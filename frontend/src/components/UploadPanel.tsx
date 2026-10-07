import { useMemo, useRef, useState } from "react";
import { uploadRecording } from "../services/api";
import Icon from "../lib/Icon";
import type { IngestResult } from "../types/roadpulse";
import { shortId } from "../lib/format";
import { Disclaimer, ErrorState } from "./States";
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
  { field: "total_acceleration", file: "TotalAcceleration.csv", required: false, hint: "Validated, not used yet", match: /^totalacceleration\.csv$/i },
  { field: "metadata", file: "Metadata.csv", required: false, hint: "Only the start time is read", match: /^metadata\.csv$/i },
];

const kb = (n: number) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);

interface Props {
  onViewResults: (recordingId: string) => void;
  onBack: () => void;
  notify: (msg: string, tone?: "ok" | "error" | "info") => void;
}

export default function UploadPanel({ onViewResults, onBack, notify }: Props) {
  const [files, setFiles] = useState<Record<string, File>>({});
  const [phase, setPhase] = useState<UploadPhase>("idle");
  const [result, setResult] = useState<IngestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [drag, setDrag] = useState(false);
  const inputs = useRef<Record<string, HTMLInputElement | null>>({});
  const dropInput = useRef<HTMLInputElement>(null);

  const busy = phase === "uploading" || phase === "processing";
  const ready = SLOTS.filter((s) => s.required).every((s) => files[s.field]);

  const assign = (list: FileList | File[]) => {
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

  const submit = async () => {
    setPhase("uploading");
    setResult(null);
    setError(null);
    try {
      const r = await uploadRecording(files, () => setPhase("processing"));
      setResult(r);
      setPhase("done");
      notify("Recording processed", "ok");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setPhase("error");
    }
  };

  const summary = useMemo(() => {
    if (!result) return null;
    return {
      strong: result.events.filter((e) => e.classification === "STRONG_IMPACT").length,
      repeated: result.hotspots.filter((h) => h.event_count >= 2).length,
    };
  }, [result]);

  return (
    <div className="stack">
      <section className="card">
        <div
          className={`dropzone${drag ? " over" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            if (!busy) setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            if (!busy) assign(e.dataTransfer.files);
          }}
        >
          <Icon name="upload" size={28} />
          <strong>Drop Sensor Logger CSV files here</strong>
          <span className="muted">or choose several files at once. Files are matched by name.</span>
          <button className="btn ghost" disabled={busy} onClick={() => dropInput.current?.click()}>
            Choose files
          </button>
          <input ref={dropInput} type="file" accept=".csv,text/csv" multiple hidden onChange={(e) => e.target.files && assign(e.target.files)} />
        </div>

        <div className="slots">
          {SLOTS.map((s) => {
            const f = files[s.field];
            return (
              <div key={s.field} className={`slot${f ? " filled" : ""}`}>
                <div className="slot-top">
                  <span className="mono">{s.file}</span>
                  <span className={`pipe-tag ${s.required ? "live" : "planned"}`}>{s.required ? "Required" : "Optional"}</span>
                </div>
                <span className="muted small">{f ? `${f.name} · ${kb(f.size)}` : s.hint}</span>
                <div className="row gap">
                  <button className="btn ghost sm" disabled={busy} onClick={() => inputs.current[s.field]?.click()}>
                    {f ? "Replace" : "Select"}
                  </button>
                  {f && (
                    <button
                      className="btn ghost sm"
                      disabled={busy}
                      onClick={() =>
                        setFiles((p) => {
                          const n = { ...p };
                          delete n[s.field];
                          return n;
                        })
                      }
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
                    if (file) setFiles((p) => ({ ...p, [s.field]: file }));
                    e.target.value = "";
                  }}
                />
              </div>
            );
          })}
        </div>

        <div className="row gap wrap">
          <button className="btn primary" disabled={!ready || busy} onClick={submit}>
            {busy ? "Processing…" : "Process recording"}
          </button>
          {!ready && <span className="muted small">Accelerometer.csv, Gyroscope.csv and Location.csv are required.</span>}
        </div>
      </section>

      <ProcessingProgress phase={phase} />

      {phase === "error" && <ErrorState title="Processing failed" message={error ?? "Upload failed"} />}

      {phase === "done" && result && summary && (
        <section className="card result" aria-live="polite">
          <div className="row between wrap">
            <div>
              <div className="eyebrow ok">Completed · one vehicle / one trip</div>
              <h2>Recording processed</h2>
              <div className="mono small muted">
                Recording ID <span title={result.recording_id}>{result.recording_id}</span> ({shortId(result.recording_id)})
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
            <StatCard label="Rows processed" value={result.rows_processed.toLocaleString()} note={`${result.duration_seconds.toFixed(0)} s of sensor data`} icon="database" />
            <StatCard label="Events detected" value={result.events_detected} note="Impact observations" icon="bolt" />
            <StatCard label="Hotspots detected" value={result.hotspots_detected} note="30 m clusters" icon="hotspot" />
            <StatCard label="Strong events" value={summary.strong} tone="crit" icon="alert" />
            <StatCard label="Repeated hotspots" value={summary.repeated} tone="info" icon="layers" note="2+ observations" />
          </div>
          {result.events_detected === 0 && <p className="muted">No impact events were detected in this recording (for example a stationary or very short trip).</p>}
        </section>
      )}

      <Disclaimer>Current results are heuristic motion observations from the uploaded sensor recording. They should not be interpreted as confirmed road damage without further validation.</Disclaimer>
    </div>
  );
}
