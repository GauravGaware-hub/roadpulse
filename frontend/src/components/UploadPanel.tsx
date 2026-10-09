import { useMemo, useRef, useState } from "react";
import { ApiError, UploadError, api, uploadRecording, wakeServer } from "../services/api";
import Icon from "../lib/Icon";
import type { IngestResult } from "../types/roadpulse";
import { shortId } from "../lib/format";
import { validateSelection, type Issue } from "../lib/validateFiles";
import { addRecent, loadRecent, removeRecent, type RecentRecording } from "../lib/recent";
import { Disclaimer } from "./States";
import ProcessingProgress, { type UploadPhase } from "./ProcessingProgress";
import StatCard from "./StatCard";

interface Slot {
  field: string;
  file: string;
  required: boolean;
  hint: string;
  match: RegExp;
}

const SLOTS: Slot[] = [
  { field: "accelerometer", file: "Accelerometer.csv", required: true, hint: "Linear acceleration (x, y, z)", match: /^accelerometer\.csv$/i },
  { field: "gyroscope", file: "Gyroscope.csv", required: true, hint: "Rotation rate (x, y, z)", match: /^gyroscope\.csv$/i },
  { field: "location", file: "Location.csv", required: true, hint: "GPS fixes with speed", match: /^location\.csv$/i },
  { field: "total_acceleration", file: "TotalAcceleration.csv", required: false, hint: "Checked, not used yet", match: /^totalacceleration\.csv$/i },
  { field: "metadata", file: "Metadata.csv", required: false, hint: "Only the start time is read", match: /^metadata\.csv$/i },
];

const kb = (n: number) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);

/** What went wrong and what the user can safely do next. */
interface Failure {
  title: string;
  message: string;
  advice: string;
  /** The server may already have stored a result: retrying could create a second recording. */
  ambiguous: boolean;
}

function describe(e: unknown): Failure {
  if (e instanceof UploadError) {
    if (e.kind === "aborted") return { title: "Upload cancelled", message: "You cancelled the upload.", advice: "Nothing needs to be cleaned up. Press Process recording to start again.", ambiguous: e.serverMayHaveProcessed };
    if (e.serverMayHaveProcessed) {
      return {
        title: "Result not received",
        message: e.message,
        advice: "The files reached the server, so the recording may have been processed even though no result came back. Uploading again with the same files is safe: if the server already processed them it returns that same recording instead of creating a duplicate (unless the server restarted in between). If it was restarting, wait a minute first.",
        ambiguous: true,
      };
    }
    if (e.kind === "http") return { title: "The server rejected the files", message: e.message, advice: "Fix the problem described above (check the file in each slot) and try again. Nothing was saved.", ambiguous: false };
    return { title: "Upload did not complete", message: e.message, advice: "The files did not finish uploading, so nothing was saved. Check your connection and retry. Hotspot Wi-Fi works better than a weak mobile signal.", ambiguous: false };
  }
  if (e instanceof ApiError) return { title: "Server not reachable", message: e.message, advice: "Nothing was uploaded. The free server may still be starting. Retry in a moment.", ambiguous: false };
  return { title: "Something went wrong", message: e instanceof Error ? e.message : "Unknown error", advice: "Nothing was confirmed saved. Retry; if it keeps failing, use the baseline dataset or Demo Mode.", ambiguous: false };
}

interface Props {
  recordingId: string | null;
  onViewResults: (recordingId: string) => void;
  onUseBaseline: () => void;
  onBack: () => void;
  notify: (msg: string, tone?: "ok" | "error" | "info") => void;
}

export default function UploadPanel({ recordingId, onViewResults, onUseBaseline, onBack, notify }: Props) {
  const [files, setFiles] = useState<Record<string, File>>({});
  const [issues, setIssues] = useState<Issue[]>([]);
  const [phase, setPhase] = useState<UploadPhase>("idle");
  const [pct, setPct] = useState(0);
  const [note, setNote] = useState<string>();
  const [result, setResult] = useState<IngestResult | null>(null);
  const [failure, setFailure] = useState<Failure | null>(null);
  const [drag, setDrag] = useState(false);
  const [recent, setRecent] = useState<RecentRecording[]>(loadRecent);
  const [opening, setOpening] = useState<string | null>(null);
  const inputs = useRef<Record<string, HTMLInputElement | null>>({});
  const dropInput = useRef<HTMLInputElement>(null);
  const busyRef = useRef(false); // synchronous guard: a double click can never start two uploads
  const abortRef = useRef<AbortController | null>(null);
  // One idempotency key per file selection: retrying the SAME selection can never create a second recording
  const keyRef = useRef<string | null>(null);
  const newKey = () => (typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`);

  const busy = phase === "checking" || phase === "uploading" || phase === "processing";
  const done = phase === "done";
  const ready = SLOTS.filter((s) => s.required).every((s) => files[s.field]);

  const touch = () => {
    // any change to the selection clears stale messages and starts a new upload identity
    keyRef.current = null;
    setIssues([]);
    setFailure(null);
  };

  const assign = (list: FileList | File[]) => {
    touch();
    const next = { ...files };
    const ignored: string[] = [];
    Array.from(list).forEach((f) => {
      const slot = SLOTS.find((s) => s.match.test(f.name));
      if (slot) next[slot.field] = f;
      else ignored.push(f.name);
    });
    setFiles(next);
    if (ignored.length) notify(`Ignored (not a recognised Sensor Logger file): ${ignored.join(", ")}`, "info");
  };

  const reset = () => {
    keyRef.current = null;
    setFiles({});
    setIssues([]);
    setFailure(null);
    setResult(null);
    setPhase("idle");
    setPct(0);
    setNote(undefined);
  };

  const submit = async () => {
    if (busyRef.current || done) return;
    busyRef.current = true;
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setFailure(null);
    setResult(null);
    setPct(0);
    try {
      // 1. Validate locally (reads only the first KB of each file)
      setPhase("checking");
      setNote("Checking files…");
      const found = await validateSelection(files);
      setIssues(found);
      if (found.some((i) => i.level === "error")) {
        setPhase("idle");
        return;
      }
      // 2. Make sure the (possibly sleeping) server is awake. Only the harmless health GET is repeated.
      const awake = await wakeServer((n, s) => setNote(n === 1 ? "Checking that the server is awake…" : `Waking up the server (free hosting sleeps when idle)… ${s}s`), ctrl.signal);
      if (ctrl.signal.aborted) {
        setFailure({ title: "Upload cancelled", message: "You cancelled before anything was uploaded.", advice: "Nothing was sent to the server. Press Retry upload when you are ready.", ambiguous: false });
        setPhase("idle");
        return;
      }
      if (!awake) {
        setFailure({ title: "Server not responding", message: "The RoadPulse server did not answer after two minutes.", advice: "Nothing was uploaded. Retry in a minute, or use the baseline dataset or Demo Mode.", ambiguous: false });
        setPhase("error");
        return;
      }
      // 3. Upload once. Never retried automatically: a retry could create a duplicate recording.
      setNote(undefined);
      setPhase("uploading");
      keyRef.current ??= newKey();
      const r = await uploadRecording(files, {
        uploadKey: keyRef.current,
        onProgress: (f) => setPct(Math.round(f * 100)),
        onUploaded: () => {
          setPct(100);
          setPhase("processing");
        },
        signal: ctrl.signal,
      });
      setResult(r);
      setPhase("done");
      setRecent(addRecent({ id: r.recording_id, savedAt: Date.now(), rows: r.rows_processed, events: r.events_detected, hotspots: r.hotspots_detected }));
      notify("Recording processed", "ok");
    } catch (e) {
      const f = describe(e);
      setFailure(f);
      setPhase(e instanceof UploadError && e.kind === "aborted" ? "idle" : "error");
    } finally {
      busyRef.current = false;
      abortRef.current = null;
    }
  };

  const openRecent = async (r: RecentRecording) => {
    setOpening(r.id);
    try {
      if (await api.recordingExists(r.id)) onViewResults(r.id);
      else {
        setRecent(removeRecent(r.id));
        notify("That recording is no longer on the server. The free server clears uploads when it restarts. Upload the files again to recreate it.", "error");
      }
    } catch {
      notify("Could not reach the server to open that recording. Try again in a moment.", "error");
    } finally {
      setOpening(null);
    }
  };

  const summary = useMemo(() => {
    if (!result) return null;
    return {
      strong: result.events.filter((e) => e.classification === "STRONG_IMPACT").length,
      repeated: result.hotspots.filter((h) => h.event_count >= 2).length,
    };
  }, [result]);

  const issueFor = (field: string) => issues.filter((i) => i.field === field);

  return (
    <div className="stack">
      <section className="card">
        <div className="row between wrap">
          <span className="dataset-chip">
            <Icon name="database" size={14} />
            <span>
              Currently viewing: <b>{recordingId ? `Uploaded recording ${shortId(recordingId)}` : "Baseline (static Pune dataset)"}</b>
            </span>
          </span>
          {recordingId && (
            <button className="btn ghost sm" onClick={onUseBaseline}>
              Back to baseline dataset
            </button>
          )}
        </div>
        <p className="muted small">
          Uploading creates a new recording. It never changes the baseline Pune dataset, and nothing switches until you press <b>View Results</b>.
        </p>

        <div
          className={`dropzone${drag ? " over" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            if (!busy && !done) setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            if (!busy && !done) assign(e.dataTransfer.files);
          }}
        >
          <Icon name="upload" size={28} />
          <strong>Drop Sensor Logger CSV files here</strong>
          <span className="muted">or choose several files at once. Files are matched by name.</span>
          <button className="btn ghost" disabled={busy || done} onClick={() => dropInput.current?.click()}>
            Choose files
          </button>
          <input ref={dropInput} type="file" accept=".csv,text/csv" multiple hidden onChange={(e) => e.target.files && assign(e.target.files)} />
        </div>

        <div className="slots">
          {SLOTS.map((s) => {
            const f = files[s.field];
            const probs = issueFor(s.field);
            return (
              <div key={s.field} className={`slot${f ? " filled" : ""}${probs.some((p) => p.level === "error") ? " bad" : ""}`}>
                <div className="slot-top">
                  <span className="mono">{s.file}</span>
                  <span className={`pipe-tag ${s.required ? "live" : "planned"}`}>{s.required ? "Required" : "Optional"}</span>
                </div>
                <span className="muted small">{f ? `${f.name} · ${kb(f.size)}` : s.hint}</span>
                {probs.map((p, i) => (
                  <span key={i} className={`slot-msg ${p.level}`} role="alert">
                    {p.message}
                  </span>
                ))}
                <div className="row gap">
                  <button className="btn ghost sm" disabled={busy || done} onClick={() => inputs.current[s.field]?.click()}>
                    {f ? "Replace" : "Select"}
                  </button>
                  {f && (
                    <button
                      className="btn ghost sm"
                      disabled={busy || done}
                      onClick={() => {
                        touch();
                        setFiles((p) => {
                          const n = { ...p };
                          delete n[s.field];
                          return n;
                        });
                      }}
                    >
                      Remove
                    </button>
                  )}
                </div>
                <input
                  ref={(el) => {
                    inputs.current[s.field] = el;
                  }}
                  type="file"
                  accept=".csv,text/csv"
                  hidden
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      touch();
                      setFiles((p) => ({ ...p, [s.field]: file }));
                    }
                    e.target.value = "";
                  }}
                />
              </div>
            );
          })}
        </div>

        {issues.length > 0 && !issues.some((i) => i.level === "error") && (
          <div className="notice-warn" role="status">
            {issues.map((i, k) => (
              <div key={k}>{i.message}</div>
            ))}
          </div>
        )}

        <div className="row gap wrap">
          {done ? (
            <button className="btn primary" onClick={reset}>
              Upload another recording
            </button>
          ) : (
            <button className="btn primary" disabled={!ready || busy} onClick={submit}>
              {busy ? "Working…" : failure ? "Retry upload" : "Process recording"}
            </button>
          )}
          {(phase === "checking" || phase === "uploading") && (
            <button className="btn ghost" onClick={() => abortRef.current?.abort()}>
              Cancel
            </button>
          )}
          {phase === "processing" && <span className="muted small">The files are on the server and being processed. This cannot be cancelled; please wait.</span>}
          {!ready && !busy && !done && <span className="muted small">Accelerometer.csv, Gyroscope.csv and Location.csv are required.</span>}
        </div>
      </section>

      <ProcessingProgress phase={phase} uploadPct={pct} note={note} />

      {failure && (
        <section className={`card failure${failure.ambiguous ? " ambiguous" : ""}`} role="alert">
          <div className="eyebrow">{failure.ambiguous ? "Outcome unknown" : "Not saved"}</div>
          <h3>{failure.title}</h3>
          <p>{failure.message}</p>
          <p className="muted small">{failure.advice}</p>
          <div className="row gap wrap">
            <button className="btn ghost" disabled={busy || !ready} onClick={submit}>
              <Icon name="refresh" size={14} /> {failure.ambiguous ? "Upload again (same files)" : "Retry upload"}
            </button>
            <button className="btn ghost" onClick={onUseBaseline}>
              Use baseline dataset
            </button>
          </div>
        </section>
      )}

      {done && result && summary && (
        <section className="card result" aria-live="polite">
          <div className="row between wrap">
            <div>
              <div className="eyebrow ok">Completed · one vehicle / one trip</div>
              <h2>Recording processed</h2>
              <div className="row gap wrap small">
                <span className="muted">Recording ID</span>
                <span className="mono wrap-any" title={result.recording_id}>
                  {result.recording_id}
                </span>
                <button
                  className="link-btn"
                  onClick={() =>
                    navigator.clipboard
                      ?.writeText(result.recording_id)
                      .then(() => notify("Recording ID copied", "ok"))
                      .catch(() => notify("Could not copy; select the ID manually", "error"))
                  }
                >
                  Copy
                </button>
              </div>
            </div>
            <div className="row gap wrap">
              <button className="btn primary" onClick={() => onViewResults(result.recording_id)}>
                View Results <Icon name="arrow" size={15} />
              </button>
              <button className="btn ghost" onClick={onBack}>
                Return to Dashboard
              </button>
            </div>
          </div>
          <div className="stats">
            <StatCard label="Rows processed" value={result.rows_processed.toLocaleString()} note={`${result.duration_seconds.toFixed(0)} s · ${result.gps_rows.toLocaleString()} GPS fixes`} icon="database" />
            <StatCard label="Events detected" value={result.events_detected} note="Impact observations" icon="bolt" />
            <StatCard label="Hotspots detected" value={result.hotspots_detected} note="30 m clusters" icon="hotspot" />
            <StatCard label="Strong events" value={summary.strong} tone="crit" icon="alert" />
            <StatCard label="Repeated hotspots" value={summary.repeated} tone="info" icon="layers" note="2+ observations" />
          </div>
          <p className="muted small">
            {result.recording_started ? `Recording started ${result.recording_started}. ` : ""}Files used: {result.files_used.join(", ")}.
            {result.files_ignored.length > 0 ? ` Not used: ${result.files_ignored.join("; ")}.` : ""}
          </p>
          {result.events_detected === 0 && <p className="muted">No impact events were detected in this recording (for example a stationary, very smooth or very short trip). That is a valid result.</p>}
        </section>
      )}

      {recent.length > 0 && (
        <section className="card">
          <h3>Recent recordings (this browser)</h3>
          <p className="muted small">The free server clears uploads when it restarts, so an older recording may no longer be available.</p>
          <ul className="recent">
            {recent.map((r) => (
              <li key={r.id}>
                <span className="mono">{shortId(r.id)}</span>
                <span className="muted small">
                  {new Date(r.savedAt).toLocaleString()} · {r.events} events · {r.hotspots} hotspots
                </span>
                <span className="row gap">
                  {recordingId === r.id && <span className="badge tone-info">Viewing</span>}
                  <button className="btn ghost sm" disabled={opening !== null} onClick={() => openRecent(r)}>
                    {opening === r.id ? "Checking…" : "View"}
                  </button>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <Disclaimer>Current results are heuristic motion observations from the uploaded sensor recording. They should not be interpreted as confirmed road damage without further validation.</Disclaimer>
    </div>
  );
}
