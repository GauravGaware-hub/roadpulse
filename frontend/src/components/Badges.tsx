import type { ReactNode } from "react";
import { PRIORITY, severityOf } from "../lib/format";
import type { Level } from "../types/roadpulse";

type BadgeTone = "crit" | "warn" | "info" | "ok" | "mute";

export function StatusBadge({ tone, children, title, dot = true }: { tone: BadgeTone; children: ReactNode; title?: string; dot?: boolean }) {
  return (
    <span className={`badge tone-${tone}`} title={title}>
      {dot && <i className="dot" aria-hidden />}
      {children}
    </span>
  );
}

/** Impact-shape class from the heuristic scorer. Text + dot, never colour alone. */
export function SeverityBadge({ classification }: { classification: string }) {
  const s = severityOf(classification);
  return <StatusBadge tone={s.tone}>{s.short}</StatusBadge>;
}

/** Inspection priority, derived by the backend from the hotspot's max impact score and observation count. */
export function PriorityBadge({ level }: { level: Level }) {
  const p = PRIORITY[level];
  return (
    <StatusBadge tone={p.tone} title="Heuristic priority: maximum impact score combined with repeated observations">
      {p.label} · {p.action}
    </StatusBadge>
  );
}

/** Hotspot confidence is derived from the number of observations at the location (single trip). */
export function ConfidenceBadge({ level }: { level: Level }) {
  const tone: BadgeTone = level === "HIGH" ? "ok" : level === "MEDIUM" ? "info" : "mute";
  return (
    <StatusBadge tone={tone} title="Heuristic: based on the number of impact observations at this location">
      Confidence {level.toLowerCase()}
    </StatusBadge>
  );
}

/** Per-event confidence is not provided by the backend. */
export function HeuristicBadge() {
  return (
    <StatusBadge tone="mute" title="No per-event confidence is computed; events are scored heuristically">
      Confidence: Heuristic
    </StatusBadge>
  );
}
