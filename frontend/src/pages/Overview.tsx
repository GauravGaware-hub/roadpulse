import { useMemo } from "react";
import { ConfidenceBadge, PriorityBadge } from "../components/Badges";
import EventTable from "../components/EventTable";
import MapLegend from "../components/MapLegend";
import { DataGate, PageHeader } from "../components/PageHeader";
import PipelineDiagram from "../components/PipelineDiagram";
import RoadPulseMap from "../components/RoadPulseMap";
import StatCard from "../components/StatCard";
import { Disclaimer, EmptyState } from "../components/States";
import DatasetIndicator from "../components/DatasetIndicator";
import { PRIORITY, fmtCoord, fmtNum } from "../lib/format";
import Icon from "../lib/Icon";
import type { PageCtx } from "./ctx";

export default function Overview({ ctx }: { ctx: PageCtx }) {
  const { data, recordingId, go } = ctx;
  const { stats, hotspots, events } = data;

  const highPriority = hotspots.filter((h) => h.risk_level === "HIGH").length;
  const top = useMemo(
    () =>
      [...hotspots]
        .sort((a, b) => PRIORITY[b.risk_level].rank - PRIORITY[a.risk_level].rank || b.max_impact_score - a.max_impact_score || b.event_count - a.event_count)
        .slice(0, 4),
    [hotspots],
  );
  const recent = useMemo(() => [...events].sort((a, b) => b.peak_time - a.peak_time).slice(0, 5), [events]);

  return (
    <div className="stack">
      <PageHeader eyebrow="Road health intelligence" title="Road Health Overview" subtitle="Turning smartphone motion data into actionable road intelligence.">
        <span className={`dataset-chip status ${ctx.apiStatus}`}>
          <i className={`status-dot ${ctx.apiStatus}`} aria-hidden />
          System {ctx.apiStatus === "online" ? "online" : ctx.apiStatus === "offline" ? "offline" : "checking"}
        </span>
        <DatasetIndicator recordingId={recordingId} onUseStatic={() => ctx.switchDataset(null)} />
      </PageHeader>

      <section className="hero card">
        <div className="hero-copy">
          <div className="eyebrow">Smartphone sensing · single-trip prototype</div>
          <h2>Road Health Intelligence</h2>
          <p>
            RoadPulse converts smartphone motion observations into road-health insight. It detects road-anomaly-like motion events from accelerometer, gyroscope and GPS data, then aggregates repeated observations to identify locations that may deserve
            inspection.
          </p>
          <div className="row gap wrap">
            <button className="btn primary" onClick={() => go("map")}>
              <Icon name="map" size={16} /> View Live Map
            </button>
            <button className="btn ghost" onClick={() => go("upload")}>
              <Icon name="upload" size={16} /> Upload Sensor Data
            </button>
          </div>
        </div>
        <div className="hero-pipe" aria-label="Pipeline summary">
          <PipelineDiagram compact />
        </div>
      </section>

      <DataGate ctx={ctx}>
        <section className="stats">
          <StatCard label="Road events" value={stats?.total_events} note="Impact observations" icon="bolt" />
          <StatCard label="Detected locations" value={stats?.total_hotspots} note="Spatial hotspots (30 m)" icon="hotspot" />
          <StatCard label="Strong events" value={stats?.strong_events} note={`${stats?.moderate_events ?? 0} moderate · ${stats?.weak_events ?? 0} weak`} tone="crit" icon="alert" />
          <StatCard label="Repeated hotspots" value={stats?.repeated_hotspots} note="2+ observations" tone="info" icon="layers" />
          <StatCard label="Inspection priority" value={highPriority} note="High-priority hotspots" tone="warn" icon="pin" />
        </section>

        <section className="grid-main">
          <div className="card map-card">
            <div className="card-head">
              <h3>Spatial anomaly map</h3>
              <button className="btn ghost sm" onClick={() => go("map")}>
                Open Live Map <Icon name="arrow" size={13} />
              </button>
            </div>
            <RoadPulseMap
              className="compact"
              hotspots={hotspots}
              events={events}
              selectedHotspotId={ctx.hotspotId}
              focus={null}
              layers={{ hotspots: true, events: true, rings: true }}
              severity="ALL"
              darkTiles={ctx.darkTiles}
              onSelectHotspot={(id) => {
                ctx.selectHotspot(id);
                go("map");
              }}
              onSelectEvent={ctx.openEvent}
            />
            <MapLegend />
          </div>

          <div className="card">
            <div className="card-head">
              <h3>Priority hotspots</h3>
              <button className="btn ghost sm" onClick={() => go("hotspots")}>
                View all ({hotspots.length}) <Icon name="arrow" size={13} />
              </button>
            </div>
            {top.length === 0 ? (
              <EmptyState title="No hotspots yet">Hotspots appear when impact events cluster in space.</EmptyState>
            ) : (
              <ul className="hs-list">
                {top.map((h) => (
                  <li key={h.id} className="hs-item">
                    <div className="row between">
                      <PriorityBadge level={h.risk_level} />
                      <span className="mono muted small">#{h.id}</span>
                    </div>
                    <div className="hs-metrics">
                      <div>
                        <span className="k">Observations</span>
                        <span className="mono">{h.event_count}</span>
                      </div>
                      <div>
                        <span className="k">Max score</span>
                        <span className="mono">{h.max_impact_score.toFixed(0)}</span>
                      </div>
                      <div>
                        <span className="k">Peak accel</span>
                        <span className="mono">{fmtNum(h.max_peak_accel)}</span>
                      </div>
                    </div>
                    <div className="row between wrap">
                      <ConfidenceBadge level={h.confidence_level} />
                      <button
                        className="link-btn"
                        onClick={() => {
                          ctx.selectHotspot(h.id);
                          ctx.showOnMap(h.latitude, h.longitude);
                        }}
                      >
                        Locate <Icon name="pin" size={12} />
                      </button>
                    </div>
                    <div className="mono small muted">
                      {fmtCoord(h.latitude)}, {fmtCoord(h.longitude)}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        <section className="card">
          <div className="card-head">
            <div>
              <h3>Recent road events</h3>
              <span className="muted small">Latest in recording order (time = seconds into the recording)</span>
            </div>
            <button className="btn ghost sm" onClick={() => go("events")}>
              Full event log <Icon name="arrow" size={13} />
            </button>
          </div>
          {recent.length === 0 ? (
            <EmptyState title="No events">No impact events were detected in this dataset.</EmptyState>
          ) : (
            <EventTable events={recent} hotspotById={ctx.hotspotsById} onSelect={ctx.openEvent} compact pageSize={5} defaultSort={{ key: "peak_time", dir: -1 }} />
          )}
        </section>
      </DataGate>

      <Disclaimer />
    </div>
  );
}
