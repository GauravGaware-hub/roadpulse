import { useMemo, useState } from "react";
import { ConfidenceBadge, PriorityBadge } from "../components/Badges";
import { ChipFilter, ToggleField } from "../components/FilterBar";
import HotspotPanel from "../components/HotspotPanel";
import { DataGate, PageHeader } from "../components/PageHeader";
import RoadPulseMap from "../components/RoadPulseMap";
import StatCard from "../components/StatCard";
import { Disclaimer, EmptyState } from "../components/States";
import { PRIORITY, fmtCoord, fmtNum, fmtSec } from "../lib/format";
import Icon from "../lib/Icon";
import type { Level } from "../types/roadpulse";
import type { PageCtx } from "./ctx";

type Pri = Level | "ALL";
const PAGE = 12;

export default function Hotspots({ ctx }: { ctx: PageCtx }) {
  const { data } = ctx;
  const [pri, setPri] = useState<Pri>("ALL");
  const [repeatedOnly, setRepeatedOnly] = useState(false);
  const [shown, setShown] = useState(PAGE);

  const counts = useMemo(() => {
    const c = { HIGH: 0, MEDIUM: 0, LOW: 0 };
    data.hotspots.forEach((h) => (c[h.risk_level] += 1));
    return c;
  }, [data.hotspots]);

  const list = useMemo(
    () =>
      data.hotspots
        .filter((h) => (pri === "ALL" || h.risk_level === pri) && (!repeatedOnly || h.event_count >= 2))
        .sort((a, b) => PRIORITY[b.risk_level].rank - PRIORITY[a.risk_level].rank || b.event_count - a.event_count || b.max_impact_score - a.max_impact_score),
    [data.hotspots, pri, repeatedOnly],
  );

  return (
    <div className="stack">
      <PageHeader eyebrow="Spatial clustering" title="Road Health Hotspots" subtitle="Locations where impact observations were repeatedly logged within 30 m, ranked for inspection." />
      <DataGate ctx={ctx}>
        <section className="stats">
          <StatCard label="Repeated hotspots" value={data.stats?.repeated_hotspots} note="2+ observations" tone="info" icon="layers" />
          <StatCard label="Priority inspection" value={counts.HIGH} note="High priority" tone="crit" icon="alert" />
          <StatCard label="Inspect" value={counts.MEDIUM} note="Medium priority" tone="warn" icon="pin" />
          <StatCard label="Monitor" value={counts.LOW} note="Low priority" icon="hotspot" />
          <StatCard label="Total hotspots" value={data.stats?.total_hotspots} note={`${data.stats?.total_events ?? 0} impact events`} icon="database" />
        </section>

        <section className="card explain">
          <div>
            <div className="eyebrow">How priority is determined</div>
            <p>
              RoadPulse ranks locations using the factors below. The thresholds are simple prototype heuristics, <b>not scientifically validated</b>.
            </p>
            <ul className="factors">
              <li>
                <span className="pipe-tag live">Current</span> Impact severity: the hotspot's maximum impact score (80+ is high, 60+ is moderate)
              </li>
              <li>
                <span className="pipe-tag live">Current</span> Repeated observations: 2+ observations are needed for the top priority; confidence rises with observation count (3+ high, 2 medium, 1 low)
              </li>
              <li>
                <span className="pipe-tag live">Current</span> Spatial consistency: events within 30 m are clustered together
              </li>
              <li>
                <span className="pipe-tag partial">Partial</span> Context: stopped windows are excluded; braking, turning and traffic filters are planned
              </li>
              <li>
                <span className="pipe-tag planned">Planned</span> Independent evidence: multiple vehicles confirming a location (this dataset is one trip)
              </li>
            </ul>
          </div>
          <div className="matrix" aria-label="Priority tiers">
            <div className="matrix-row">
              <PriorityBadge level="HIGH" />
              <span className="small muted">Score 80+ and repeated (2+ observations)</span>
            </div>
            <div className="matrix-row">
              <PriorityBadge level="MEDIUM" />
              <span className="small muted">Score 80+ with a single observation, or score 60+ and repeated</span>
            </div>
            <div className="matrix-row">
              <PriorityBadge level="LOW" />
              <span className="small muted">Single moderate/weak observations, or weak repeats</span>
            </div>
          </div>
        </section>

        <section className="card filters-card">
          <div className="filter-row">
            <ChipFilter<Pri>
              label="Priority"
              value={pri}
              onChange={(v) => {
                setPri(v);
                setShown(PAGE);
              }}
              chips={[
                { value: "ALL", label: "All", count: data.hotspots.length },
                { value: "HIGH", label: "Priority inspection", count: counts.HIGH },
                { value: "MEDIUM", label: "Inspect", count: counts.MEDIUM },
                { value: "LOW", label: "Monitor", count: counts.LOW },
              ]}
            />
            <ToggleField
              label="Repeated hotspots only"
              checked={repeatedOnly}
              onChange={(v) => {
                setRepeatedOnly(v);
                setShown(PAGE);
              }}
            />
          </div>
        </section>

        <section className="grid-hotspots">
          <div className="stack">
            {list.length === 0 ? (
              <div className="card">
                <EmptyState title="No hotspots match the filters">Clear the filters to see all hotspots.</EmptyState>
              </div>
            ) : (
              list.slice(0, shown).map((h) => (
                <article key={h.id} className={`card hs-card${h.id === ctx.hotspotId ? " selected" : ""}`}>
                  <div className="row between wrap">
                    <div className="row gap wrap">
                      <span className="mono id-tag">#{h.id}</span>
                      <PriorityBadge level={h.risk_level} />
                      <ConfidenceBadge level={h.confidence_level} />
                      {h.event_count >= 2 && <span className="badge tone-info">Repeated hotspot</span>}
                    </div>
                    <span className="mono small muted">
                      last observed t = {fmtSec(h.last_event)}
                    </span>
                  </div>
                  <div className="hs-metrics wide">
                    <div>
                      <span className="k">Observations</span>
                      <span className="mono">{h.event_count}</span>
                    </div>
                    <div>
                      <span className="k">Strong / moderate</span>
                      <span className="mono">
                        {h.strong_events} / {h.moderate_events}
                      </span>
                    </div>
                    <div>
                      <span className="k">Max score</span>
                      <span className="mono">{h.max_impact_score.toFixed(0)}</span>
                    </div>
                    <div>
                      <span className="k">Peak accel</span>
                      <span className="mono">{fmtNum(h.max_peak_accel)} m/s²</span>
                    </div>
                    <div>
                      <span className="k">Independent recordings</span>
                      <span className="mono">1</span>
                    </div>
                  </div>
                  <div className="row between wrap">
                    <span className="mono small muted">
                      <Icon name="pin" size={12} /> {fmtCoord(h.latitude)}, {fmtCoord(h.longitude)}
                    </span>
                    <div className="row gap">
                      <button className="btn ghost sm" onClick={() => ctx.selectHotspot(h.id)}>
                        Details &amp; linked events
                      </button>
                      <button
                        className="btn ghost sm"
                        onClick={() => {
                          ctx.selectHotspot(h.id);
                          ctx.showOnMap(h.latitude, h.longitude);
                        }}
                      >
                        Locate
                      </button>
                    </div>
                  </div>
                </article>
              ))
            )}
            {list.length > shown && (
              <button className="btn ghost" onClick={() => setShown(shown + PAGE)}>
                Show more ({list.length - shown} remaining)
              </button>
            )}
          </div>

          <aside className="sticky-col">
            <div className="card map-card">
              <RoadPulseMap
                className="compact"
                hotspots={data.hotspots}
                events={[]}
                selectedHotspotId={ctx.hotspotId}
                focus={ctx.focus}
                layers={{ hotspots: true, events: false, rings: true }}
                severity="ALL"
                darkTiles={ctx.darkTiles}
                onSelectHotspot={ctx.selectHotspot}
                onSelectEvent={ctx.openEvent}
              />
            </div>
            <div className="card side-panel">
              <HotspotPanel
                hotspot={ctx.detail.data}
                loading={ctx.detail.loading}
                error={ctx.detail.error}
                onClose={() => ctx.selectHotspot(null)}
                onOpenEvent={ctx.openEvent}
                onRetry={ctx.detail.retry}
              />
            </div>
          </aside>
        </section>
      </DataGate>
      <Disclaimer />
    </div>
  );
}
