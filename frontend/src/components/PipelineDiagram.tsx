import Icon from "../lib/Icon";

type State = "live" | "partial" | "planned";

interface Step {
  title: string;
  desc: string;
  state: State;
}

// Honest status of each stage in the current prototype
export const PIPELINE: Step[] = [
  { title: "Smartphone sensors", desc: "Accelerometer and gyroscope (~100 Hz) with GPS (~1 Hz)", state: "live" },
  { title: "Signal processing", desc: "Time-sync, acceleration and gyro magnitude, jerk", state: "live" },
  { title: "Motion event detection", desc: "1 s windows, speed-adaptive robust z-scores", state: "live" },
  { title: "Context filtering", desc: "Speed gating today; braking, turning and traffic filters planned", state: "partial" },
  { title: "Potential road anomaly", desc: "Impact-shape scoring: strong / moderate / weak", state: "live" },
  { title: "Repeated observations", desc: "30 m spatial clustering into hotspots", state: "live" },
  { title: "Confidence & priority", desc: "Heuristic severity and observation-count rules", state: "live" },
  { title: "Multi-vehicle confirmation", desc: "Independent recordings agreeing on a location", state: "planned" },
];

const TAG: Record<State, string> = { live: "Current", partial: "Partial", planned: "Planned" };

export default function PipelineDiagram({ compact = false }: { compact?: boolean }) {
  const steps = compact ? PIPELINE.filter((_, i) => [0, 2, 3, 5, 6].includes(i)) : PIPELINE;
  return (
    <ol className={`pipeline${compact ? " compact" : ""}`}>
      {steps.map((s, i) => (
        <li key={s.title} className={`pipe-step ${s.state}`}>
          <span className="pipe-num mono">{String(i + 1).padStart(2, "0")}</span>
          <div className="pipe-body">
            <strong>{s.title}</strong>
            {!compact && <span className="muted small">{s.desc}</span>}
            <span className={`pipe-tag ${s.state}`}>{TAG[s.state]}</span>
          </div>
          {i < steps.length - 1 && (
            <span className="pipe-arrow" aria-hidden>
              <Icon name="arrow" size={14} />
            </span>
          )}
        </li>
      ))}
    </ol>
  );
}
