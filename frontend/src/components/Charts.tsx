import { useMemo } from "react";
import { SEVERITY, TONE_COLOR, type Tone } from "../lib/format";
import type { RoadEvent } from "../types/roadpulse";

/** Horizontal labelled bars. */
export function BarList({ items }: { items: { label: string; value: number; tone: Tone | "accent" }[] }) {
  const max = Math.max(...items.map((i) => i.value), 1);
  return (
    <ul className="barlist">
      {items.map((i) => (
        <li key={i.label}>
          <span className="bl-label">{i.label}</span>
          <span className="bl-track" aria-hidden>
            <i className={`tone-${i.tone}`} style={{ width: `${(i.value / max) * 100}%` }} />
          </span>
          <span className="mono bl-val">{i.value}</span>
        </li>
      ))}
    </ul>
  );
}

/** Histogram of impact scores (0-100) in fixed bins. */
export function ScoreHistogram({ values, bins = 10 }: { values: number[]; bins?: number }) {
  const counts = useMemo(() => {
    const c = new Array(bins).fill(0) as number[];
    values.forEach((v) => c[Math.min(bins - 1, Math.max(0, Math.floor((v / 100) * bins)))]++);
    return c;
  }, [values, bins]);
  const max = Math.max(...counts, 1);
  const W = 420, H = 150, pad = 24, bw = (W - pad * 2) / bins;
  return (
    <svg viewBox={`0 0 ${W} ${H + 24}`} className="chart" role="img" aria-label="Distribution of impact scores">
      {counts.map((c, i) => {
        const h = (c / max) * (H - 20);
        const mid = ((i + 0.5) / bins) * 100;
        const color = mid >= 70 ? TONE_COLOR.crit : mid >= 45 ? TONE_COLOR.warn : TONE_COLOR.info;
        return (
          <g key={i}>
            <rect x={pad + i * bw + 2} y={H - h} width={bw - 4} height={h} rx={2} fill={color} opacity={0.85} />
            {c > 0 && (
              <text x={pad + i * bw + bw / 2} y={H - h - 4} textAnchor="middle" className="chart-num">
                {c}
              </text>
            )}
            <text x={pad + i * bw} y={H + 14} className="chart-axis" textAnchor="middle">
              {(i * 100) / bins}
            </text>
          </g>
        );
      })}
      <text x={W - pad} y={H + 14} className="chart-axis" textAnchor="middle">
        100
      </text>
      <line x1={pad} x2={W - pad} y1={H} y2={H} className="chart-line" />
    </svg>
  );
}

/** Impact score of each event along the recording timeline (time = seconds into the recording). */
export function EventTimeline({ events, onSelect }: { events: RoadEvent[]; onSelect: (e: RoadEvent) => void }) {
  const W = 760, H = 190, L = 34, R = 12, T = 10, B = 28;
  if (events.length === 0) return null;
  const tMin = Math.min(...events.map((e) => e.peak_time));
  const tMax = Math.max(...events.map((e) => e.peak_time), tMin + 1);
  const x = (t: number) => L + ((t - tMin) / (tMax - tMin)) * (W - L - R);
  const y = (s: number) => T + (1 - s / 100) * (H - T - B);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img" aria-label="Impact score of each event over recording time">
      {[0, 25, 50, 75, 100].map((s) => (
        <g key={s}>
          <line x1={L} x2={W - R} y1={y(s)} y2={y(s)} className="chart-grid" />
          <text x={L - 6} y={y(s) + 3} textAnchor="end" className="chart-axis">
            {s}
          </text>
        </g>
      ))}
      {[0, 0.25, 0.5, 0.75, 1].map((f) => (
        <text key={f} x={L + f * (W - L - R)} y={H - 8} textAnchor={f === 0 ? "start" : f === 1 ? "end" : "middle"} className="chart-axis">
          {Math.round(tMin + f * (tMax - tMin))} s
        </text>
      ))}
      {events.map((e) => (
        <circle
          key={e.id}
          cx={x(e.peak_time)}
          cy={y(e.impact_score)}
          r={4.5}
          fill={TONE_COLOR[SEVERITY[e.classification].tone]}
          stroke="#0B0F17"
          strokeWidth={1}
          className="pt"
          tabIndex={0}
          role="button"
          aria-label={`Event ${e.id}, score ${e.impact_score}, ${SEVERITY[e.classification].label}`}
          onClick={() => onSelect(e)}
          onKeyDown={(k) => k.key === "Enter" && onSelect(e)}
        >
          <title>
            Event #{e.id} · {SEVERITY[e.classification].short} · score {e.impact_score.toFixed(0)} · t={e.peak_time.toFixed(0)} s
          </title>
        </circle>
      ))}
    </svg>
  );
}
