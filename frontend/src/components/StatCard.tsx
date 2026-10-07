import type { ReactNode } from "react";
import type { Tone } from "../lib/format";
import Icon, { type IconName } from "../lib/Icon";

interface Props {
  label: string;
  value: number | string | undefined;
  unit?: string;
  note?: ReactNode;
  tone?: Tone | "accent";
  icon?: IconName;
}

export default function StatCard({ label, value, unit, note, tone = "accent", icon }: Props) {
  return (
    <div className={`stat tone-${tone}`}>
      <div className="stat-top">
        <span className="stat-label">{label}</span>
        {icon && <Icon name={icon} size={15} />}
      </div>
      <div className="stat-value">
        {value ?? "–"}
        {unit && <small>{unit}</small>}
      </div>
      {note && <div className="stat-note">{note}</div>}
    </div>
  );
}
