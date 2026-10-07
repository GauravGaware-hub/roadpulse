import { useMemo } from "react";
import { BarList, EventTimeline, ScoreHistogram } from "../components/Charts";
import { DataGate, PageHeader } from "../components/PageHeader";
import PipelineDiagram from "../components/PipelineDiagram";
import StatCard from "../components/StatCard";
import { Disclaimer, EmptyState } from "../components/States";
import { fmtNum } from "../lib/format";
import type { PageCtx } from "./ctx";

export default function Analytics({ ctx }: { ctx: PageCtx }) {
  const { data } = ctx;
  const { stats, events, hotspots } = data;

  const obs = useMemo(() => {
    if (events.length === 0) return null;
    const accel = events.map((e) => e.peak_accel);
    const speeds = events.map((e) => e.speed).filter((s): s is number => s !== null);
    return {
      meanAccel: accel.reduce((a, b) => a + b, 0) / accel.length,
      maxAccel: Math.max(...accel),
      meanSpeed: speeds.length ? (speeds.reduce((a, b) => a + b, 0) / speeds.length) * 3.6 : null,
      linked: events.filter((e) => e.hotspot_id !== null).length,
    };
  }, [events]);

  const hsByCount = useMemo(() => {
    const b = { "1 observation": 0, "2 observations": 0, "3 observations": 0, "4+ observations": 0 };
    hotspots.forEach((h) => {
      if (h.event_count >= 4) b["4+ observations"]++;
      else if (h.event_count === 3) b["3 observations"]++;
      else if (h.event_count === 2) b["2 observations"]++;
      else b["1 observation"]++;
    });
    return b;
  }, [hotspots]);

  const hsByPriority = useMemo(() => {
    const c = { HIGH: 0, MEDIUM: 0, LOW: 0 };
    hotspots.forEach((h) => (c[h.risk_level] += 1));
    return c;
  }, [hotspots]);

  return (
    <div className="stack">
      <PageHeader eyebrow="Evidence" title="Analytics" subtitle="What the current observations look like. All charts use the active dataset only; nothing here is simulated." />
      <DataGate ctx={ctx}>
        {events.length === 0 ? (
          <div className="card">
            <EmptyState title="No events to analyse">This dataset has no impact events.</EmptyState>
          </div>
        ) : (
          <>
            <section className="stats">
              <StatCard label="Events" value={stats?.total_events} icon="bolt" />
              <StatCard label="Highest impact score" value={stats?.highest_impact_score.toFixed(0)} note="of 100 (heuristic)" tone="crit" icon="alert" />
              <StatCard label="Mean peak accel" value={fmtNum(obs?.meanAccel)} unit=" m/s²" note={`max ${fmtNum(obs?.maxAccel)} m/s²`} icon="pulse" />
              <StatCard label="Mean event speed" value={obs?.meanSpeed === null || obs === null ? "–" : obs.meanSpeed.toFixed(0)} unit=" km/h" note="From GPS speed" icon="map" />
              <StatCard label="Events in hotspots" value={obs?.linked} note={`of ${events.length}`} tone="info" icon="layers" />
            </section>

            <section className="grid-2">
              <div className="card">
                <h3>Severity distribution</h3>
                <p className="muted small">Impact-shape classes from the heuristic scorer.</p>
                <BarList
                  items={[
                    { label: "Strong impact", value: stats?.strong_events ?? 0, tone: "crit" },
                    { label: "Moderate impact", value: stats?.moderate_events ?? 0, tone: "warn" },
                    { label: "Weak impact", value: stats?.weak_events ?? 0, tone: "info" },
                  ]}
                />
              </div>
              <div className="card">
                <h3>Impact score distribution</h3>
                <p className="muted small">Number of events per 10-point score band (0 to 100).</p>
                <ScoreHistogram values={events.map((e) => e.impact_score)} />
              </div>
              <div className="card">
                <h3>Hotspot distribution</h3>
                <p className="muted small">Hotspots by number of observations, and by inspection priority.</p>
                <BarList items={(Object.entries(hsByCount) as [string, number][]).map(([label, value]) => ({ label, value, tone: "accent" as const }))} />
                <hr className="sep" />
                <BarList
                  items={[
                    { label: "Priority inspection", value: hsByPriority.HIGH, tone: "crit" },
                    { label: "Inspect", value: hsByPriority.MEDIUM, tone: "warn" },
                    { label: "Monitor", value: hsByPriority.LOW, tone: "info" },
                  ]}
                />
              </div>
              <div className="card">
                <h3>Road-health summary</h3>
                <ul className="summary">
                  <li>
                    <b>{stats?.strong_events}</b> of <b>{stats?.total_events}</b> impact events scored as strong.
                  </li>
                  <li>
                    Events cluster into <b>{stats?.total_hotspots}</b> locations; <b>{stats?.repeated_hotspots}</b> were hit more than once.
                  </li>
                  <li>
                    <b>{hsByPriority.HIGH}</b> hotspot{hsByPriority.HIGH === 1 ? "" : "s"} reach the priority-inspection tier.
                  </li>
                  <li>All observations come from one vehicle on one trip, so this is not independent confirmation.</li>
                </ul>
              </div>
            </section>

            <section className="card">
              <h3>Event timeline</h3>
              <p className="muted small">Impact score of each event over the recording (x = seconds into the recording). Select a point to open the event.</p>
              <EventTimeline events={events} onSelect={ctx.openEvent} />
            </section>
          </>
        )}

        <section className="card">
          <h3>How RoadPulse works</h3>
          <p className="muted small">The processing pipeline, with the status of each stage in the current prototype.</p>
          <PipelineDiagram />
        </section>
      </DataGate>
      <Disclaimer />
    </div>
  );
}
