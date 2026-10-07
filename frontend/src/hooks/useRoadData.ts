import { useCallback, useEffect, useState } from "react";
import { api } from "../services/api";
import type { Hotspot, RoadEvent, Stats } from "../types/roadpulse";

export const errMsg = (e: unknown) => (e instanceof Error ? e.message : "Unknown error");

export interface RoadData {
  stats?: Stats;
  hotspots: Hotspot[];
  events: RoadEvent[];
  eventTotal: number;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/** Loads stats, hotspots and events for the active dataset (static Pune or an uploaded recording). */
export function useRoadData(recordingId: string | null): RoadData {
  const [stats, setStats] = useState<Stats>();
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [events, setEvents] = useState<RoadEvent[]>([]);
  const [eventTotal, setEventTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let stale = false;
    setLoading(true);
    setError(null);
    Promise.all([api.stats(recordingId), api.hotspots(recordingId), api.events({ limit: 500, recordingId })])
      .then(([s, h, e]) => {
        if (stale) return;
        setStats(s);
        setHotspots(h.items);
        setEvents(e.items);
        setEventTotal(e.total);
      })
      .catch((e) => {
        if (stale) return;
        setStats(undefined);
        setHotspots([]);
        setEvents([]);
        setEventTotal(0);
        setError(errMsg(e));
      })
      .finally(() => !stale && setLoading(false));
    return () => {
      stale = true;
    };
  }, [recordingId, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { stats, hotspots, events, eventTotal, loading, error, reload };
}
