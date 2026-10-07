import { useEffect, useMemo, useState } from "react";
import EventTable from "../components/EventTable";
import { ChipFilter, RangeField, ToggleField } from "../components/FilterBar";
import { PageHeader } from "../components/PageHeader";
import { Disclaimer, EmptyState, ErrorState, LoadingState } from "../components/States";
import { errMsg } from "../hooks/useRoadData";
import { api } from "../services/api";
import type { Classification, RoadEvent } from "../types/roadpulse";
import type { PageCtx } from "./ctx";

type Cls = Classification | "ALL";

export default function Events({ ctx }: { ctx: PageCtx }) {
  const { recordingId, data } = ctx;
  const [cls, setCls] = useState<Cls>("ALL");
  const [minScore, setMinScore] = useState(0);
  const [minSpeed, setMinSpeed] = useState(0); // km/h, applied client-side
  const [linkedOnly, setLinkedOnly] = useState(false);
  const [query, setQuery] = useState("");

  const [rows, setRows] = useState<RoadEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  // Classification and minimum score are filtered by the backend query parameters.
  useEffect(() => {
    let stale = false;
    setLoading(true);
    setError(null);
    api
      .events({ classification: cls === "ALL" ? undefined : cls, minScore, limit: 500, recordingId })
      .then((r) => {
        if (stale) return;
        setRows(r.items);
        setTotal(r.total);
      })
      .catch((e) => !stale && setError(errMsg(e)))
      .finally(() => !stale && setLoading(false));
    return () => {
      stale = true;
    };
  }, [cls, minScore, recordingId, tick]);

  const filtered = useMemo(() => {
    const id = query.trim().replace("#", "");
    return rows.filter((e) => (e.speed ?? 0) * 3.6 >= minSpeed && (!linkedOnly || e.hotspot_id !== null) && (id === "" || String(e.id) === id));
  }, [rows, minSpeed, linkedOnly, query]);

  const s = data.stats;
  return (
    <div className="stack">
      <PageHeader eyebrow="Event investigation" title="Road Events" subtitle="Impact observations detected from the smartphone motion signal. Select an event for its full signature and location.">
        <div className="mini-stat">
          <span className="k">Showing</span>
          <span className="mono">
            {filtered.length} of {s?.total_events ?? "–"}
          </span>
        </div>
      </PageHeader>

      <section className="card filters-card">
        <ChipFilter<Cls>
          label="Severity"
          value={cls}
          onChange={setCls}
          chips={[
            { value: "ALL", label: "All events", count: s?.total_events },
            { value: "STRONG_IMPACT", label: "Strong", count: s?.strong_events },
            { value: "MODERATE_IMPACT", label: "Moderate", count: s?.moderate_events },
            { value: "WEAK_IMPACT", label: "Weak", count: s?.weak_events },
          ]}
        />
        <div className="filter-row">
          <RangeField label="Min impact score" value={minScore} min={0} max={100} step={5} onChange={setMinScore} />
          <RangeField label="Min speed" value={minSpeed} min={0} max={60} step={5} unit=" km/h" onChange={setMinSpeed} />
          <label className="field">
            <span className="field-label">Find event ID</span>
            <input className="input mono" inputMode="numeric" placeholder="e.g. 12" value={query} onChange={(e) => setQuery(e.target.value)} />
          </label>
          <ToggleField label="Only events in a hotspot" checked={linkedOnly} onChange={setLinkedOnly} />
        </div>
        <p className="muted small">
          Per-event confidence is not computed by the current heuristic engine, and every observation is a potential road anomaly, so there are no confidence or class filters yet. Severity and score are filtered by the backend; speed and hotspot filters are applied in the
          browser.
        </p>
      </section>

      <section className="card">
        {error ? (
          <ErrorState title="Could not load events" message={error} onRetry={() => setTick((t) => t + 1)} />
        ) : loading && rows.length === 0 ? (
          <LoadingState label="Loading events…" />
        ) : filtered.length === 0 ? (
          <EmptyState title="No events match the current filters">Try lowering the minimum score or speed.</EmptyState>
        ) : (
          <>
            {total > rows.length && <p className="muted small">Showing the first {rows.length} of {total} matching events.</p>}
            <EventTable events={filtered} hotspotById={ctx.hotspotsById} selectedId={ctx.selectedEvent?.id} onSelect={ctx.openEvent} />
          </>
        )}
      </section>
      <Disclaimer />
    </div>
  );
}
