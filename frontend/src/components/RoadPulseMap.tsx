import { Fragment, useEffect, useMemo } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import L from "leaflet";
import { PRIORITY, SEVERITY, TONE_COLOR, fmtCoord, hasGps } from "../lib/format";
import Icon from "../lib/Icon";
import type { Classification, Hotspot, RoadEvent } from "../types/roadpulse";

export interface FocusPoint {
  lat: number;
  lon: number;
  key: number; // changes on every request so repeat clicks re-centre
}

export interface MapLayers {
  hotspots: boolean;
  events: boolean;
  rings: boolean;
}

interface Props {
  hotspots: Hotspot[];
  events: RoadEvent[];
  selectedHotspotId: number | null;
  selectedEventId?: number | null;
  focus: FocusPoint | null;
  layers: MapLayers;
  severity: Classification | "ALL";
  darkTiles: boolean;
  onSelectHotspot: (id: number) => void;
  onSelectEvent: (e: RoadEvent) => void;
  className?: string;
}

// Exact backend coordinates are used as-is; nothing is rounded, jittered or anonymised.
function Controller({ hotspots, events, focus }: { hotspots: Hotspot[]; events: RoadEvent[]; focus: FocusPoint | null }) {
  const map = useMap();

  const bounds = useMemo(() => {
    const pts: [number, number][] = hotspots.map((h) => [h.latitude, h.longitude]);
    if (pts.length === 0) events.filter(hasGps).forEach((e) => pts.push([e.latitude as number, e.longitude as number]));
    return pts;
  }, [hotspots, events]);

  const fit = () => {
    if (bounds.length) map.fitBounds(bounds, { padding: [40, 40], maxZoom: 17 });
  };

  // Fit to the data whenever the dataset changes
  useEffect(fit, [bounds, map]);

  useEffect(() => {
    if (focus) map.flyTo([focus.lat, focus.lon], Math.max(map.getZoom(), 17), { duration: 0.6 });
  }, [focus, map]);

  return (
    <div
      className="map-ctl"
      ref={(el) => {
        if (el) L.DomEvent.disableClickPropagation(el);
      }}
    >
      <button className="icon-btn" onClick={() => map.zoomIn()} aria-label="Zoom in">
        +
      </button>
      <button className="icon-btn" onClick={() => map.zoomOut()} aria-label="Zoom out">
        −
      </button>
      <button className="icon-btn" onClick={fit} aria-label="Fit map to all data" title="Fit to all data">
        <Icon name="fit" size={16} />
      </button>
    </div>
  );
}

export default function RoadPulseMap({
  hotspots,
  events,
  selectedHotspotId,
  selectedEventId,
  focus,
  layers,
  severity,
  darkTiles,
  onSelectHotspot,
  onSelectEvent,
  className = "",
}: Props) {
  const shownEvents = useMemo(
    () => events.filter(hasGps).filter((e) => severity === "ALL" || e.classification === severity),
    [events, severity],
  );

  return (
    <div className={`map-wrap ${darkTiles ? "map-dark" : ""} ${className}`}>
      <MapContainer center={[18.52, 73.85]} zoom={12} className="map" scrollWheelZoom zoomControl={false}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Controller hotspots={hotspots} events={events} focus={focus} />

        {layers.events &&
          shownEvents.map((e) => {
            const color = TONE_COLOR[SEVERITY[e.classification].tone];
            const selected = e.id === selectedEventId;
            return (
              <CircleMarker
                key={`e${e.id}`}
                center={[e.latitude as number, e.longitude as number]}
                radius={selected ? 7 : 4}
                pathOptions={{ color: selected ? "#fff" : "#0B0F17", weight: selected ? 2 : 1, fillColor: color, fillOpacity: 0.85 }}
                eventHandlers={{ click: () => onSelectEvent(e) }}
              >
                <Tooltip direction="top" offset={[0, -4]}>
                  Event #{e.id} · {SEVERITY[e.classification].short} · score {e.impact_score.toFixed(0)}
                </Tooltip>
              </CircleMarker>
            );
          })}

        {layers.hotspots &&
          hotspots.map((h) => {
            const color = TONE_COLOR[PRIORITY[h.risk_level].tone];
            const selected = h.id === selectedHotspotId;
            const r = 8 + Math.min(h.event_count, 5) * 1.5 + (selected ? 3 : 0);
            return (
              <Fragment key={`h${h.id}`}>
                {layers.rings && h.event_count >= 2 && (
                  <CircleMarker
                    center={[h.latitude, h.longitude]}
                    radius={r + 7}
                    interactive={false}
                    pathOptions={{ color, weight: 1.5, dashArray: "4 4", fillOpacity: 0, opacity: 0.9 }}
                  />
                )}
                <CircleMarker
                  center={[h.latitude, h.longitude]}
                  radius={r}
                  pathOptions={{ color: selected ? "#ffffff" : color, weight: selected ? 3 : 2, fillColor: color, fillOpacity: selected ? 0.55 : 0.28 }}
                  eventHandlers={{ click: () => onSelectHotspot(h.id) }}
                >
                  <Tooltip direction="top" offset={[0, -r]}>
                    <b>Hotspot #{h.id}</b> · {h.event_count} observation{h.event_count === 1 ? "" : "s"} · {PRIORITY[h.risk_level].action}
                    <br />
                    {fmtCoord(h.latitude)}, {fmtCoord(h.longitude)}
                  </Tooltip>
                </CircleMarker>
              </Fragment>
            );
          })}
      </MapContainer>
    </div>
  );
}
