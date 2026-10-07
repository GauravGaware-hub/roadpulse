import { useEffect, useMemo, useState } from "react";
import { fmtNum, fmtSec } from "../lib/format";
import type { Hotspot, RoadEvent } from "../types/roadpulse";
import { PriorityBadge, SeverityBadge } from "./Badges";

type SortKey = "id" | "impact_score" | "peak_accel" | "speed" | "peak_time";

interface Props {
  events: RoadEvent[];
  hotspotById: Map<number, Hotspot>;
  selectedId?: number | null;
  onSelect: (e: RoadEvent) => void;
  pageSize?: number;
  compact?: boolean;
  defaultSort?: { key: SortKey; dir: 1 | -1 };
}

const COLS: { key: SortKey | null; label: string }[] = [
  { key: "id", label: "Event" },
  { key: null, label: "Context" },
  { key: null, label: "Severity" },
  { key: "impact_score", label: "Impact score" },
  { key: "peak_accel", label: "Peak accel" },
  { key: "speed", label: "Speed" },
  { key: null, label: "Location" },
  { key: "peak_time", label: "Time" },
  { key: null, label: "Status" },
];

/** Paged, sortable event registry (renders at most `pageSize` rows). */
export default function EventTable({ events, hotspotById, selectedId, onSelect, pageSize = 15, compact, defaultSort = { key: "impact_score", dir: -1 } }: Props) {
  const [sort, setSort] = useState(defaultSort);
  const [page, setPage] = useState(0);

  const sorted = useMemo(() => {
    const val = (e: RoadEvent) => (sort.key === "speed" ? e.speed ?? -1 : (e[sort.key] as number));
    return [...events].sort((a, b) => (val(a) - val(b)) * sort.dir);
  }, [events, sort]);

  const pages = Math.max(1, Math.ceil(sorted.length / pageSize));
  useEffect(() => setPage(0), [events]);
  const cur = Math.min(page, pages - 1);
  const rows = sorted.slice(cur * pageSize, cur * pageSize + pageSize);

  const header = (c: (typeof COLS)[number]) => {
    if (!c.key) return <th key={c.label}>{c.label}</th>;
    const k = c.key;
    const active = sort.key === k;
    return (
      <th key={c.label} aria-sort={active ? (sort.dir === 1 ? "ascending" : "descending") : "none"}>
        <button className="th-btn" onClick={() => setSort({ key: k, dir: active ? ((sort.dir * -1) as 1 | -1) : -1 })}>
          {c.label}
          <span aria-hidden>{active ? (sort.dir === 1 ? " ▲" : " ▼") : ""}</span>
        </button>
      </th>
    );
  };

  return (
    <div>
      <div className="table-wrap">
        <table className={compact ? "compact" : ""}>
          <thead>
            <tr>{(compact ? COLS.filter((c) => !["Location", "Status"].includes(c.label)) : COLS).map(header)}</tr>
          </thead>
          <tbody>
            {rows.map((e) => {
              const h = e.hotspot_id !== null ? hotspotById.get(e.hotspot_id) : undefined;
              return (
                <tr key={e.id} className={e.id === selectedId ? "sel" : ""}>
                  <td>
                    <button className="row-link mono" onClick={() => onSelect(e)}>
                      #{e.id}
                    </button>
                  </td>
                  <td>
                    <span>Potential road anomaly</span>
                    {e.speed_band && <span className="muted small block">{e.speed_band.replace("_", " ").toLowerCase()} traffic speed band</span>}
                  </td>
                  <td>
                    <SeverityBadge classification={e.classification} />
                  </td>
                  <td>
                    <span className="mono">{e.impact_score.toFixed(0)}</span>
                    <span className="mini-meter" aria-hidden>
                      <i style={{ width: `${e.impact_score}%` }} />
                    </span>
                  </td>
                  <td className="mono">{fmtNum(e.peak_accel)} m/s²</td>
                  <td className="mono">{e.speed === null ? "–" : `${(e.speed * 3.6).toFixed(0)} km/h`}</td>
                  {!compact && (
                    <td className="mono small">
                      {e.latitude === null ? "–" : `${e.latitude.toFixed(5)}, ${(e.longitude as number).toFixed(5)}`}
                    </td>
                  )}
                  <td className="mono">{fmtSec(e.peak_time)}</td>
                  {!compact && (
                    <td>
                      {h ? (
                        <span className="status-cell">
                          <span className="small muted">Hotspot #{h.id}</span>
                          <PriorityBadge level={h.risk_level} />
                        </span>
                      ) : (
                        <span className="muted small">Isolated observation</span>
                      )}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {pages > 1 && (
        <div className="pager">
          <span className="muted small">
            {cur * pageSize + 1}–{Math.min(sorted.length, (cur + 1) * pageSize)} of {sorted.length}
          </span>
          <div className="row gap">
            <button className="btn ghost sm" disabled={cur === 0} onClick={() => setPage(cur - 1)}>
              Previous
            </button>
            <button className="btn ghost sm" disabled={cur >= pages - 1} onClick={() => setPage(cur + 1)}>
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
