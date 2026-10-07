import type { EventList, HotspotDetail, HotspotList, IngestResult, Stats } from "../types/roadpulse";

// Set VITE_API_BASE_URL at build time. The localhost fallback applies to `npm run dev` only;
// a production build without it calls the same origin the page is served from.
const BASE = (
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? (import.meta.env.DEV ? "http://localhost:8000" : "")
).replace(/\/+$/, "");

async function get<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`);
  } catch {
    throw new Error(`Cannot reach the RoadPulse API at ${BASE || "this origin"}. Is the backend running?`);
  }
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(`API error ${res.status}${detail ? `: ${detail}` : ""}`);
  }
  return res.json() as Promise<T>;
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
  hotspot: (id: number, recordingId?: string | null) =>
    get<HotspotDetail>(withRec(`/api/hotspots/${id}`, recordingId)),
  events: ({ classification, minScore, limit = 100, recordingId }: EventFilters = {}) => {
    const q = new URLSearchParams({ limit: String(limit) });
    if (classification) q.set("classification", classification);
    if (minScore) q.set("min_score", String(minScore));
    if (recordingId) q.set("recording_id", recordingId);
    return get<EventList>(`/api/events?${q}`);
  },
};

// XHR (not fetch) so we can tell "uploading" apart from "processing" on the server.
export function uploadRecording(
  files: Record<string, File>,
  onUploaded: () => void,
): Promise<IngestResult> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    Object.entries(files).forEach(([field, file]) => form.append(field, file));
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE}/api/ingest`);
    xhr.upload.onload = onUploaded;
    xhr.onerror = () => reject(new Error(`Cannot reach the RoadPulse API at ${BASE || "this origin"}. Is the backend running?`));
    xhr.onload = () => {
      let body: { detail?: unknown } = {};
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        /* non-JSON body */
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as unknown as IngestResult);
      else reject(new Error(typeof body.detail === "string" ? body.detail : `Upload failed (HTTP ${xhr.status})`));
    };
    xhr.send(form);
  });
}
