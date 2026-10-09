import { useEffect, useState } from "react";
import Icon from "../lib/Icon";

export type UploadPhase = "idle" | "checking" | "uploading" | "processing" | "done" | "error";

const STAGES = [
  "Uploading",
  "Synchronizing Sensors",
  "Detecting Motion Events",
  "Filtering Context",
  "Scoring Events",
  "Clustering Hotspots",
  "Generating Report",
];

interface Props {
  phase: UploadPhase;
  uploadPct?: number; // 0-100, real bytes sent
  note?: string; // e.g. "Waking up the server…"
}

/**
 * The backend processes a recording synchronously, so it reports no per-stage progress.
 * Only "checking server", "uploading" (real byte progress), "processing" and "done" are real;
 * the stage steps advance on a timer while the single processing request is in flight.
 */
export default function ProcessingProgress({ phase, uploadPct = 0, note }: Props) {
  const [stage, setStage] = useState(0);

  useEffect(() => {
    if (phase === "checking" || phase === "uploading") setStage(0);
    if (phase === "processing") {
      setStage(1);
      const t = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), 1100);
      return () => clearInterval(t);
    }
    if (phase === "done") setStage(STAGES.length);
  }, [phase]);

  // On failure the failure card explains what happened; stage ticks would imply progress that did not occur
  if (phase === "idle" || phase === "error") return null;

  return (
    <div className="progress-card" role="status" aria-live="polite">
      <div className="row between wrap">
        <strong>
          {phase === "checking" && "Contacting server…"}
          {phase === "uploading" && `Uploading… ${uploadPct}%`}
          {phase === "processing" && "Processing on the server…"}
          {phase === "done" && "Completed"}
        </strong>
        {note && <span className="muted small">{note}</span>}
      </div>
      {phase === "uploading" && (
        <div className="meter" aria-hidden>
          <div style={{ width: `${uploadPct}%` }} />
        </div>
      )}
      <ol className="stages">
        {STAGES.map((name, i) => {
          const active = phase === "checking" ? false : i === stage;
          const state = i < stage ? "done" : active ? "active" : "todo";
          return (
            <li key={name} className={`stage ${state}`}>
              <span className="stage-dot" aria-hidden>
                {state === "done" ? <Icon name="check" size={12} /> : i + 1}
              </span>
              <span>{name}</span>
              <span className="visually-hidden">{state}</span>
            </li>
          );
        })}
      </ol>
      {phase === "processing" && <p className="muted small">The server runs the whole pipeline in one request, so the stage steps are indicative.</p>}
    </div>
  );
}
