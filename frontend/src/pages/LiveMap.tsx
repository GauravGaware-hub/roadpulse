import { useMemo, useState } from "react";
import { ChipFilter, ToggleField } from "../components/FilterBar";
import HotspotPanel from "../components/HotspotPanel";
import MapLegend from "../components/MapLegend";
import { DataGate, PageHeader } from "../components/PageHeader";
import RoadPulseMap, { type MapLayers } from "../components/RoadPulseMap";
import { Disclaimer } from "../components/States";
import type { Classification } from "../types/roadpulse";
import type { PageCtx } from "./ctx";

type Sev = Classification | "ALL";

export default function LiveMap({ ctx }: { ctx: PageCtx }) {
  const { data } = ctx;
  const [layers, setLayers] = useState<MapLayers>({ hotspots: true, events: true, rings: true });
  const [sev, setSev] = useState<Sev>("ALL");
  const counts = useMemo(() => {
    const c = { STRONG_IMPACT: 0, MODERATE_IMPACT: 0, WEAK_IMPACT: 0 };
    data.events.forEach((e) => (c[e.classification] += 1));
    return c;
  }, [data.events]);

  return (
    <div className="stack">
      <PageHeader
        eyebrow="Geospatial stream"
        title="Live Road Health Map"
        subtitle="Explore detected impact observations and repeated hotspots on the road network. Coordinates are shown exactly as recorded."
      />
      <DataGate ctx={ctx}>
        <section className="grid-map">
          <div className="card map-card tall">
            <div className="map-toolbar">
              <div className="layer-panel">
                <span className="legend-title">Layers</span>
                <ToggleField label="Hotspots" checked={layers.hotspots} onChange={(v) => setLayers({ ...layers, hotspots: v })} />
                <ToggleField label="Event markers" checked={layers.events} onChange={(v) => setLayers({ ...layers, events: v })} />
                <ToggleField label="Repeated rings" checked={layers.rings} onChange={(v) => setLayers({ ...layers, rings: v })} />
              </div>
              <ChipFilter<Sev>
                label="Event severity"
                value={sev}
                onChange={setSev}
                chips={[
                  { value: "ALL", label: "All", count: data.events.length },
                  { value: "STRONG_IMPACT", label: "Strong", count: counts.STRONG_IMPACT },
                  { value: "MODERATE_IMPACT", label: "Moderate", count: counts.MODERATE_IMPACT },
                  { value: "WEAK_IMPACT", label: "Weak", count: counts.WEAK_IMPACT },
                ]}
              />
            </div>
            {data.hotspots.length === 0 && data.events.length === 0 && <div className="map-empty">No hotspots or events in this dataset.</div>}
            <RoadPulseMap
              hotspots={data.hotspots}
              events={data.events}
              selectedHotspotId={ctx.hotspotId}
              selectedEventId={ctx.selectedEvent?.id}
              focus={ctx.focus}
              layers={layers}
              severity={sev}
              darkTiles={ctx.darkTiles}
              onSelectHotspot={ctx.selectHotspot}
              onSelectEvent={ctx.openEvent}
            />
            <MapLegend />
          </div>
          <aside className="card side-panel">
            <HotspotPanel
              hotspot={ctx.detail.data}
              loading={ctx.detail.loading}
              error={ctx.detail.error}
              onClose={() => ctx.selectHotspot(null)}
              onOpenEvent={ctx.openEvent}
              onRetry={ctx.detail.retry}
            />
          </aside>
        </section>
      </DataGate>
      <Disclaimer />
    </div>
  );
}
