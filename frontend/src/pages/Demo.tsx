import { useEffect, useMemo, useRef, useState } from "react";
import { PageHeader } from "../components/PageHeader";
import { StatusBadge } from "../components/Badges";
import Icon from "../lib/Icon";

// ---- Deterministic SIMULATED signal (seeded PRNG; identical on every run) ----
function mulberry32(a: number) {
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const N = 240;
const DURATION = 6; // seconds shown
const SPIKE_T = 3.2;
const STOP_FROM = 4.7; // simulated "vehicle stopped" window (< 1 m/s)
const THRESHOLD = 12.6;

function makeTrace(seed: number, amp: number): number[] {
  const rnd = mulberry32(seed);
  return Array.from({ length: N }, (_, i) => {
    const t = (i / (N - 1)) * DURATION;
    const noise = (rnd() - 0.5) * 0.7;
    const texture = 0.25 * Math.sin(2 * Math.PI * 2.1 * t);
    const d = t - SPIKE_T;
    const spike = amp * Math.exp(-((d / 0.07) ** 2)) * Math.cos(2 * Math.PI * 6 * d);
    // simulated stopped-vehicle jolt that must be rejected by context filtering
    const stopped = t > STOP_FROM && t < STOP_FROM + 0.5 ? 2.6 * Math.sin(2 * Math.PI * 4 * t) : 0;
    return 9.81 + noise + texture + spike + stopped;
  });
}

const STEPS = [
  { title: "Sensor signal", text: "Smartphone acceleration magnitude while driving: about 9.8 m/s² of gravity plus road texture." },
  { title: "Motion event", text: "A short, sharp spike exceeds the speed-adaptive threshold and becomes a candidate impact event." },
  { title: "Context filtering", text: "Windows where the vehicle is stopped (< 1 m/s) are rejected. Braking, turning and traffic filters are planned, not active." },
  { title: "Repeated observation", text: "Further passes over the same spot produce similar impacts at the same GPS location." },
  { title: "Hotspot", text: "Observations within 30 m are clustered into one repeated hotspot." },
  { title: "Inspection priority", text: "Severity plus repeats gives a heuristic priority. This is a potential road anomaly, not a confirmed pothole." },
];
const STEP_MS = 2600;

function Trace({ data, draw, marks, label, height = 180 }: { data: number[]; draw: string; marks?: "event" | "event+reject"; label?: string; height?: number }) {
  const W = 640, H = height, L = 36, R = 10, T = 12, B = 22;
  const lo = 7, hi = 22;
  const x = (i: number) => L + (i / (N - 1)) * (W - L - R);
  const y = (v: number) => T + (1 - (Math.min(hi, Math.max(lo, v)) - lo) / (hi - lo)) * (H - T - B);
  const path = data.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const tx = (t: number) => L + (t / DURATION) * (W - L - R);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart demo-chart" role="img" aria-label={label ?? "Simulated acceleration signal"}>
      {[8, 12, 16, 20].map((v) => (
        <g key={v}>
          <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} className="chart-grid" />
          <text x={L - 6} y={y(v) + 3} textAnchor="end" className="chart-axis">
            {v}
          </text>
        </g>
      ))}
      <text x={W - R} y={H - 6} textAnchor="end" className="chart-axis">
        time (s, simulated)
      </text>
      {marks && (
        <>
          <line x1={L} x2={W - R} y1={y(THRESHOLD)} y2={y(THRESHOLD)} className="thresh" />
          <text x={L + 4} y={y(THRESHOLD) - 4} className="chart-axis">
            detection threshold (illustrative)
          </text>
          <rect x={tx(SPIKE_T - 0.25)} y={T} width={tx(0.5) - L} height={H - T - B} className="evt-window" />
          <text x={tx(SPIKE_T)} y={T + 11} textAnchor="middle" className="chart-num">
            candidate event
          </text>
        </>
      )}
      {marks === "event+reject" && (
        <>
          <rect x={tx(STOP_FROM)} y={T} width={tx(0.5) - L} height={H - T - B} className="rej-window" />
          <text x={tx(STOP_FROM + 0.25)} y={T + 11} textAnchor="middle" className="chart-axis">
            stopped: rejected
          </text>
        </>
      )}
      <path d={path} className={`trace ${draw}`} pathLength={1} />
    </svg>
  );
}

function Schematic({ done }: { done: boolean }) {
  // Illustrative layout only; these are NOT real coordinates.
  const pts = [
    { x: 150, y: 98 },
    { x: 176, y: 112 },
    { x: 162, y: 128 },
  ];
  return (
    <svg viewBox="0 0 320 200" className="chart demo-chart schematic" role="img" aria-label="Schematic of three observations clustering into a hotspot">
      <path d="M10 160 C80 130 120 120 160 110 S260 70 312 40" className="road" />
      {pts.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r={6} className="obs" />
          <text x={p.x + 10} y={p.y - 6} className="chart-axis">
            pass {i + 1}
          </text>
        </g>
      ))}
      {done && (
        <>
          <circle cx={163} cy={112} r={34} className="cluster-ring" />
          <text x={163} y={162} textAnchor="middle" className="chart-num">
            hotspot (30 m)
          </text>
        </>
      )}
      <text x={10} y={192} className="chart-axis">
        schematic, not real coordinates
      </text>
    </svg>
  );
}

export default function Demo() {
  const [step, setStep] = useState(-1);
  const [run, setRun] = useState(0);
  const timer = useRef<number | undefined>(undefined);

  const traces = useMemo(() => [makeTrace(11, 8.5), makeTrace(23, 7.9), makeTrace(37, 8.9)], []);

  const stop = () => window.clearInterval(timer.current);
  const start = () => {
    stop();
    setRun((r) => r + 1);
    setStep(0);
    timer.current = window.setInterval(() => {
      setStep((s) => {
        if (s >= STEPS.length - 1) {
          window.clearInterval(timer.current);
          return s;
        }
        return s + 1;
      });
    }, STEP_MS);
  };
  const reset = () => {
    stop();
    setStep(-1);
  };
  useEffect(() => stop, []);

  const idle = step < 0;
  const cur = Math.max(step, 0);

  return (
    <div className="stack">
      <PageHeader eyebrow="Presentation" title="Demo Mode" subtitle="How a smartphone motion signal becomes an inspection priority, step by step.">
        <div className="row gap">
          {idle ? (
            <button className="btn primary" onClick={start}>
              <Icon name="play" size={15} /> Start Demo
            </button>
          ) : (
            <>
              <button className="btn primary" onClick={start}>
                <Icon name="refresh" size={15} /> Replay
              </button>
              <button className="btn ghost" onClick={reset}>
                <Icon name="reset" size={15} /> Reset
              </button>
            </>
          )}
        </div>
      </PageHeader>

      <div className="sim-banner" role="note">
        <StatusBadge tone="warn">Simulation</StatusBadge>
        <span>
          Deterministic presentation data. These signals, passes and locations are <b>not</b> real sensor readings and are not live. The real Pune results are on the other pages.
        </span>
      </div>

      <section className="grid-demo">
        <ol className="demo-steps" aria-label="Demo steps">
          {STEPS.map((s, i) => (
            <li key={s.title} className={idle ? "" : i < step ? "done" : i === step ? "active" : ""}>
              <span className="stage-dot" aria-hidden>
                {!idle && i < step ? <Icon name="check" size={12} /> : i + 1}
              </span>
              <div>
                <strong>{s.title}</strong>
                <span className="muted small block">{s.text}</span>
              </div>
            </li>
          ))}
        </ol>

        <div className="card demo-stage">
          {idle ? (
            <div className="state">
              <Icon name="play" size={28} />
              <strong>Press Start Demo</strong>
              <span className="muted">A simulated trip passes over the same road defect three times.</span>
            </div>
          ) : (
            <>
              <div className="eyebrow">
                Step {cur + 1} of {STEPS.length} · {STEPS[cur].title}
              </div>
              {cur <= 2 && (
                <Trace
                  key={`a${run}`}
                  data={traces[0]}
                  draw="draw"
                  marks={cur === 0 ? undefined : cur === 1 ? "event" : "event+reject"}
                  label="Simulated acceleration magnitude with a candidate event"
                />
              )}
              {cur === 3 && (
                <div className="stack tight">
                  {traces.map((t, i) => (
                    <div key={`${run}-${i}`}>
                      <span className="muted small">Pass {i + 1} · simulated</span>
                      <Trace data={t} draw="draw" marks="event" height={110} label={`Simulated pass ${i + 1}`} />
                    </div>
                  ))}
                </div>
              )}
              {cur >= 4 && <Schematic done />}
              {cur === 5 && (
                <div className="callout demo-result">
                  <div className="row gap wrap">
                    <StatusBadge tone="warn">Medium · Inspect</StatusBadge>
                    <StatusBadge tone="mute">Confidence: Heuristic</StatusBadge>
                    <StatusBadge tone="info">Repeated hotspot · 3 simulated observations</StatusBadge>
                  </div>
                  <p>
                    <b>Potential road anomaly.</b> Three impact observations at one location during a single simulated trip. In RoadPulse, independent vehicles agreeing on the same spot would raise confidence further. That multi-vehicle step is planned.
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      </section>
    </div>
  );
}
