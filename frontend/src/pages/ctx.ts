import type { RoadData } from "../hooks/useRoadData";
import type { Route } from "../lib/router";
import type { FocusPoint } from "../components/RoadPulseMap";
import type { Hotspot, HotspotDetail, RoadEvent } from "../types/roadpulse";

export interface HotspotDetailState {
  data: HotspotDetail | null;
  loading: boolean;
  error: string | null;
  retry: () => void;
}

/** Everything the pages share. App owns the state; pages stay presentational. */
export interface PageCtx {
  data: RoadData;
  recordingId: string | null;
  hotspotsById: Map<number, Hotspot>;
  go: (r: Route) => void;
  hotspotId: number | null;
  selectHotspot: (id: number | null) => void;
  detail: HotspotDetailState;
  selectedEvent: RoadEvent | null;
  openEvent: (e: RoadEvent) => void;
  focus: FocusPoint | null;
  showOnMap: (lat: number, lon: number) => void;
  darkTiles: boolean;
  setDarkTiles: (v: boolean) => void;
  switchDataset: (id: string | null) => void;
  notify: (msg: string, tone?: "ok" | "error" | "info") => void;
  apiStatus: "checking" | "online" | "offline";
  apiVersion?: string;
  refreshApi: () => void;
}
