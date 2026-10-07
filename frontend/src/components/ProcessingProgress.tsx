import { useEffect, useState } from "react";
import Icon from "../lib/Icon";

export type UploadPhase = "idle" | "uploading" | "processing" | "done" | "error";

const STAGES = [
  "Uploading",
  "Synchronizing Sensors",
  "Detecting Motion Events",
  "Filtering Context",
  "Scoring Events",
  "Clustering Hotspots",
  "Generating Report",
];

/**
 * The backend processes a recording synchronously, so it reports no per-stage progress.
 * Only "uploading" vs "processing" vs "done" are real; the stage steps below advance on a timer
 * while the single processing request is in flight.
 */
export default function ProcessingProgress({ phase }: { phase: UploadPhase }) {
  const [stage, setStage] = useState(0);

  useEffect(() => {
    if (phase === "uploading") setStage(0);
    if (phase === "processing") {
      setStage(1);
      const t = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), 1100);
      return () => clearInterval(t);
    }
    if (phase === "done") setStage(STAGES.length);
  }, [phase]);

  if (phase === "idle") return null;

  return (
    <div className="progress-card">
      <ol className="stages">
        {STAGES.map((name, i) => {
          const state = phase === "error" ? (i < stage ? "done" : i === stage ? "error" : "todo") : i < stage ? "done" : i === stage ? "active" : "todo";
          return (
            <li key={name} className={`stage ${state}`}>
              <span className="stage-dot" aria-hidden>
                {state === "done" ? <Icon name="check" size={12} /> : state === "error" ? <Icon name="x" size={12} /> : i + 1}
              </span>
              <span>{name}</span>
              <span className="visually-hidden">{state}</span>
            </li>
          );
        })}
      </ol>
      <p className="muted small">
        {phase === "uploading" && "Uploading sensor files…"}
        {phase === "processing" && "Processing… The server runs the whole pipeline in one request, so stage steps are indicative."}
        {phase === "done" && "Completed."}
        {phase === "error" && "Processing stopped."}
      </p>
    </div>
  );
}
