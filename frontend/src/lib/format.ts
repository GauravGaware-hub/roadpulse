import type { Classification, Level, RoadEvent } from "../types/roadpulse";

export type Tone = "crit" | "warn" | "info";

// Severity = impact-shape class from the heuristic scorer (NOT a validated damage class)
export const SEVERITY: Record<Classification, { label: string; short: string; tone: Tone }> = {
  STRONG_IMPACT: { label: "Strong impact", short: "Strong", tone: "crit" },
  MODERATE_IMPACT: { label: "Moderate impact", short: "Moderate", tone: "warn" },
  WEAK_IMPACT: { label: "Weak impact", short: "Weak", tone: "info" },
};

// Priority comes from the backend's heuristic hotspot risk_level (max impact score + repeated observations)
export const PRIORITY: Record<Level, { label: string; action: string; tone: Tone; rank: number }> = {
  HIGH: { label: "High", action: "Priority inspection", tone: "crit", rank: 3 },
  MEDIUM: { label: "Medium", action: "Inspect", tone: "warn", rank: 2 },
  LOW: { label: "Low", action: "Monitor", tone: "info", rank: 1 },
};

export const TONE_COLOR: Record<Tone, string> = { crit: "#EF4444", warn: "#F59E0B", info: "#38BDF8" };

export const severityOf = (c: string) => SEVERITY[c as Classification] ?? { label: c, short: c, tone: "info" as Tone };

export const fmtCoord = (n: number | null | undefined) => (n === null || n === undefined ? "Not available" : n.toFixed(6));
export const fmtSec = (s: number) => `${s.toFixed(1)} s`;
export const fmtNum = (n: number | null | undefined, d = 1) => (n === null || n === undefined ? "–" : n.toFixed(d));
export const fmtSpeed = (mps: number | null | undefined) =>
  mps === null || mps === undefined ? "–" : `${mps.toFixed(1)} m/s (${(mps * 3.6).toFixed(0)} km/h)`;
export const shortId = (id: string) => id.slice(0, 8);

export const hasGps = (e: RoadEvent) => e.latitude !== null && e.longitude !== null;
