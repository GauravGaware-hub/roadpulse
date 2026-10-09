import type { EventList, HotspotDetail, HotspotList, IngestResult, Stats } from "../types/roadpulse";

// Set VITE_API_BASE_URL at build time. The localhost fallback applies to `npm run dev` only;
// a production build without it calls the same origin the page is served from.
export const API_BASE = (
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? (import.meta.env.DEV ? "http://localhost:8000" : "")
).replace(/\/+$/, "");
const BASE = API_BASE;

const where = BASE || "this origin";
const sleep = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve) => {
    const t = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => {
      clearTimeout(t);
      resolve();
    });
  });

/** Error from the API client. `kind` lets the UI choose accurate wording. */
export class ApiError extends Error {
  constructor(
    message: string,
    public kind: "network" | "timeout" | "http" | "aborted",
    public status?: number,
  ) {
    super(message);
  }
}

// Free hosting (Render) puts the server to sleep when idle. A cold start took ~40 s when measured,
// so a single attempt gets a generous timeout, and ONLY idempotent GETs are retried.
const GET_TIMEOUT_MS = 50_000;
const RETRY_STATUS = new Set([502, 503, 504]);

async function getOnce<T>(path: string, outer?: AbortSignal): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), GET_TIMEOUT_MS);
  const onOuterAbort = () => ctrl.abort();
  outer?.addEventListener("abort", onOuterAbort);
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { signal: ctrl.signal });
  } catch (e) {
    if (outer?.aborted) throw new ApiError("Cancelled.", "aborted");
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new ApiError(`The RoadPulse API at ${where} did not respond in time. The server may be waking up.`, "timeout");
    }
    throw new ApiError(`Cannot reach the RoadPulse API at ${where}. Check your connection or whether the backend is running.`, "network");
  } finally {
    clearTimeout(timer);
    outer?.removeEventListener("abort", onOuterAbort);
  }
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(`API error ${res.status}${detail ? `: ${detail}` : ""}`, "http", res.status);
  }
  return res.json() as Promise<T>;
}

async function get<T>(path: string, retries = 2): Promise<T> {
  for (let attempt = 0; ; attempt++) {
    try {
      return await getOnce<T>(path);
    } catch (e) {
      const transient = e instanceof ApiError && (e.kind === "network" || e.kind === "timeout" || (e.kind === "http" && RETRY_STATUS.has(e.status ?? 0)));
      if (!transient || attempt >= retries) throw e;
      await sleep(1500 * (attempt + 1));
    }
  }
}

export interface EventFilters {
  classification?: string;
  minScore?: number;
  limit?: number;
  recordingId?: string | null; // omitted/null -> static Pune dataset
}

const rec = (id?: string | null) => (id ? `recording_id=${encodeURIComponent(id)}` : "");
const withRec = (path: string, id?: string | null) => (id ? `${path}${path.includes("?") ? "&" : "?"}${rec(id)}` : path);

export interface HealthResponse {
  status: string;
  service: string;
}
export interface RootResponse {
  project: string;
  status: string;
  version: string;
}

export const api = {
  health: () => get<HealthResponse>("/api/health"),
  root: () => get<RootResponse>("/"),
  stats: (recordingId?: string | null) => get<Stats>(withRec("/api/stats", recordingId)),
  hotspots: (recordingId?: string | null) => get<HotspotList>(withRec("/api/hotspots", recordingId)),
  hotspot: (id: number, recordingId?: string | null) => get<HotspotDetail>(withRec(`/api/hotspots/${id}`, recordingId)),
  events: ({ classification, minScore, limit = 100, recordingId }: EventFilters = {}) => {
    const q = new URLSearchParams({ limit: String(limit) });
    if (classification) q.set("classification", classification);
    if (minScore) q.set("min_score", String(minScore));
    if (recordingId) q.set("recording_id", recordingId);
    return get<EventList>(`/api/events?${q}`);
  },
  /** Does this recording still exist on the server? (uploads live on the server's local disk) */
  recordingExists: async (id: string): Promise<boolean> => {
    try {
      await get<Stats>(withRec("/api/stats", id), 1);
      return true;
    } catch (e) {
      if (e instanceof ApiError && e.kind === "http" && e.status === 404) return false;
      throw e;
    }
  },
};

/**
 * Wait until the API answers (handles a sleeping free-tier server). Only GET /api/health is polled,
 * which is safe to repeat. Resolves true when healthy, false when it gave up or was cancelled.
 */
export async function wakeServer(onAttempt: (n: number, elapsedS: number) => void, signal?: AbortSignal, maxWaitMs = 120_000): Promise<boolean> {
  const t0 = Date.now();
  for (let n = 1; Date.now() - t0 < maxWaitMs; n++) {
    if (signal?.aborted) return false;
    onAttempt(n, Math.round((Date.now() - t0) / 1000));
    try {
      await getOnce<HealthResponse>("/api/health", signal);
      return true;
    } catch {
      if (signal?.aborted) return false;
      await sleep(2500, signal);
    }
  }
  return false;
}

export interface UploadHandlers {
  onProgress: (fraction: number) => void;
  /** All bytes were sent; the server is now processing. */
  onUploaded: () => void;
  signal?: AbortSignal;
  /** Idempotency key: the same key sent again returns the original recording instead of a duplicate. */
  uploadKey: string;
}

/** Upload failure. `serverMayHaveProcessed` is true when the request body was fully sent before the failure. */
export class UploadError extends ApiError {
  constructor(
    message: string,
    kind: ApiError["kind"],
    status: number | undefined,
    public serverMayHaveProcessed: boolean,
  ) {
    super(message, kind, status);
  }
}

// Processing a ~20 minute recording takes seconds locally; allow generously for a small free-tier CPU.
const UPLOAD_TIMEOUT_MS = 5 * 60_000;

/**
 * POST /api/ingest. Never retried automatically by this app. The X-Upload-Key header makes a repeated
 * submission (an explicit retry, or a browser-level re-send after a dropped connection) return the
 * original recording instead of creating a duplicate.
 * XHR (not fetch) so upload progress and "uploaded -> processing" can be reported.
 */
export function uploadRecording(files: Record<string, File>, h: UploadHandlers): Promise<IngestResult> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    Object.entries(files).forEach(([field, file]) => form.append(field, file));
    if (h.signal?.aborted) {
      reject(new UploadError("Upload cancelled.", "aborted", undefined, false));
      return;
    }
    const xhr = new XMLHttpRequest();
    let sent = false;
    xhr.open("POST", `${BASE}/api/ingest`);
    xhr.setRequestHeader("X-Upload-Key", h.uploadKey);
    xhr.timeout = UPLOAD_TIMEOUT_MS;
    xhr.upload.onprogress = (e) => e.lengthComputable && h.onProgress(e.loaded / e.total);
    xhr.upload.onload = () => {
      sent = true;
      h.onUploaded();
    };
    h.signal?.addEventListener("abort", () => xhr.abort());
    xhr.onabort = () => reject(new UploadError("Upload cancelled.", "aborted", undefined, sent));
    xhr.ontimeout = () =>
      reject(new UploadError(sent ? "The server did not finish within 5 minutes." : "The upload did not complete in time.", "timeout", undefined, sent));
    xhr.onerror = () =>
      reject(new UploadError(sent ? `The connection to ${where} dropped while the server was processing.` : `Cannot reach the RoadPulse API at ${where}.`, "network", undefined, sent));
    xhr.onload = () => {
      let body: { detail?: unknown } = {};
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        /* non-JSON body (e.g. a proxy error page) */
      }
      if (xhr.status >= 200 && xhr.status < 300 && (body as { recording_id?: unknown }).recording_id) resolve(body as unknown as IngestResult);
      else {
        const detail = typeof body.detail === "string" ? body.detail : "";
        // 5xx without a RoadPulse JSON body usually means the hosting proxy answered, not our code
        const proxyish = xhr.status >= 500 && !detail;
        reject(
          new UploadError(
            detail || (proxyish ? `The server returned HTTP ${xhr.status}. It may be restarting or out of memory.` : `Upload failed (HTTP ${xhr.status}).`),
            "http",
            xhr.status,
            proxyish,
          ),
        );
      }
    };
    xhr.send(form);
  });
}
