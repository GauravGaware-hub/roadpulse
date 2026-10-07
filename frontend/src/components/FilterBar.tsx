import type { ReactNode } from "react";

export interface Chip<T extends string> {
  value: T;
  label: string;
  count?: number;
}

/** Pill-style single-select filter. */
export function ChipFilter<T extends string>({ label, chips, value, onChange }: { label: string; chips: Chip<T>[]; value: T; onChange: (v: T) => void }) {
  return (
    <div className="chip-filter" role="group" aria-label={label}>
      {chips.map((c) => (
        <button key={c.value} className={`chip${c.value === value ? " active" : ""}`} aria-pressed={c.value === value} onClick={() => onChange(c.value)}>
          {c.label}
          {c.count !== undefined && <span className="chip-count">{c.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function RangeField({ label, value, min, max, step, unit, onChange }: { label: string; value: number; min: number; max: number; step: number; unit?: string; onChange: (v: number) => void }) {
  return (
    <label className="field">
      <span className="field-label">
        {label}: <b className="mono">{value}</b>
        {unit}
      </span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  );
}

export function ToggleField({ label, checked, onChange, children }: { label: string; checked: boolean; onChange: (v: boolean) => void; children?: ReactNode }) {
  return (
    <label className="toggle">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>{label}</span>
      {children}
    </label>
  );
}
