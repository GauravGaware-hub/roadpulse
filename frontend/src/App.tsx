import { useCallback, useEffect, useMemo, useState } from "react";
import EventDetail from "./components/EventDetail";
import type { FocusPoint } from "./components/RoadPulseMap";
import Sidebar from "./components/Sidebar";
import ToastHost, { type ToastItem } from "./components/Toast";
import TopBar from "./components/TopBar";
import { errMsg, useRoadData } from "./hooks/useRoadData";
import { useRoute } from "./lib/router";
import About from "./pages/About";
import Analytics from "./pages/Analytics";
import type { PageCtx } from "./pages/ctx";
import Demo from "./pages/Demo";
import Events from "./pages/Events";
import Hotspots from "./pages/Hotspots";
import LiveMap from "./pages/LiveMap";
import Overview from "./pages/Overview";
import Settings from "./pages/Settings";
import Upload from "./pages/Upload";
import { api } from "./services/api";
import type { HotspotDetail, RoadEvent } from "./types/roadpulse";

type ApiStatus = "checking" | "online" | "offline";

const readDark = () => {
  try {
    return localStorage.getItem("roadpulse.darkTiles") !== "0";
  } catch {
    return true;
  }
};

export default function App() {
  const [route, go] = useRoute();
  const [navOpen, setNavOpen] = useState(false);
  // The sidebar is permanently visible above 1100px: drop any open state when the window grows past it
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1101px)");
    const onChange = () => mq.matches && setNavOpen(false);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  // null = static Pune research dataset; otherwise an uploaded recording's UUID
  const [recordingId, setRecordingId] = useState<string | null>(null);
  const data = useRoadData(recordingId);
  const hotspotsById = useMemo(() => new Map(data.hotspots.map((h) => [h.id, h])), [data.hotspots]);

  const [hotspotId, setHotspotId] = useState<number | null>(null);
  const [detail, setDetail] = useState<HotspotDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailTick, setDetailTick] = useState(0);

  const [selectedEvent, setSelectedEvent] = useState<RoadEvent | null>(null);
  const [focus, setFocus] = useState<FocusPoint | null>(null);

  const [darkTiles, setDarkTilesState] = useState(readDark);
  const setDarkTiles = (v: boolean) => {
    setDarkTilesState(v);
    try {
      localStorage.setItem("roadpulse.darkTiles", v ? "1" : "0");
    } catch {
      /* storage unavailable: setting just won't persist */
    }
  };

  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const notify = useCallback((message: string, tone: ToastItem["tone"] = "info") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, message, tone }]);
    window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4500);
  }, []);

  // API health + backend version
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");
  const [apiVersion, setApiVersion] = useState<string>();
  const [healthTick, setHealthTick] = useState(0);
  useEffect(() => {
    let stale = false;
    const check = () =>
      Promise.all([api.health(), api.root()])
        .then(([, root]) => {
          if (stale) return;
          setApiStatus("online");
          setApiVersion(root.version);
        })
        .catch(() => !stale && setApiStatus("offline"));
    check();
    const t = window.setInterval(check, 30000);
    return () => {
      stale = true;
      window.clearInterval(t);
    };
  }, [healthTick]);

  // Hotspot detail for the selected hotspot (kept here so the map and list pages share it)
  useEffect(() => {
    if (hotspotId === null) {
      setDetail(null);
      setDetailError(null);
      return;
    }
    let stale = false;
    setDetailLoading(true);
    setDetailError(null);
    api
      .hotspot(hotspotId, recordingId)
      .then((d) => !stale && setDetail(d))
      .catch((e) => !stale && setDetailError(errMsg(e)))
      .finally(() => !stale && setDetailLoading(false));
    return () => {
      stale = true;
    };
  }, [hotspotId, recordingId, detailTick]);

  const selectHotspot = useCallback(
    (id: number | null) => {
      setHotspotId(id);
      const h = id === null ? undefined : hotspotsById.get(id);
      if (h) setFocus({ lat: h.latitude, lon: h.longitude, key: Date.now() });
    },
    [hotspotsById],
  );

  const showOnMap = useCallback(
    (lat: number, lon: number) => {
      setFocus({ lat, lon, key: Date.now() });
      go("map");
    },
    [go],
  );

  const switchDataset = useCallback(
    (id: string | null) => {
      setRecordingId(id);
      setHotspotId(null);
      setDetail(null);
      setSelectedEvent(null);
      setFocus(null);
      go("overview");
      notify(id ? `Now viewing uploaded recording ${id.slice(0, 8)}` : "Now viewing the static Pune dataset", "info");
    },
    [go, notify],
  );

  const ctx: PageCtx = {
    data,
    recordingId,
    hotspotsById,
    go,
    hotspotId,
    selectHotspot,
    detail: { data: detail, loading: detailLoading, error: detailError, retry: () => setDetailTick((t) => t + 1) },
    selectedEvent,
    openEvent: setSelectedEvent,
    focus,
    showOnMap,
    darkTiles,
    setDarkTiles,
    switchDataset,
    notify,
    apiStatus,
    apiVersion,
    refreshApi: () => setHealthTick((t) => t + 1),
  };

  const page = {
    overview: <Overview ctx={ctx} />,
    map: <LiveMap ctx={ctx} />,
    events: <Events ctx={ctx} />,
    hotspots: <Hotspots ctx={ctx} />,
    upload: <Upload ctx={ctx} />,
    analytics: <Analytics ctx={ctx} />,
    demo: <Demo />,
    about: <About />,
    settings: <Settings ctx={ctx} />,
  }[route];

  return (
    <div className="shell">
      <Sidebar route={route} go={go} open={navOpen} onClose={() => setNavOpen(false)} api={apiStatus} version={apiVersion} />
      <div className="content">
        <TopBar route={route} go={go} recordingId={recordingId} onUseStatic={() => switchDataset(null)} onMenu={() => setNavOpen(true)} />
        <main className="page" id="main">
          {page}
        </main>
      </div>
      <EventDetail
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
        onOpenHotspot={(id) => {
          setSelectedEvent(null);
          selectHotspot(id);
          go("map");
        }}
        onShowOnMap={(e) => {
          setSelectedEvent(null);
          showOnMap(e.latitude as number, e.longitude as number);
        }}
      />
      <ToastHost toasts={toasts} dismiss={(id) => setToasts((t) => t.filter((x) => x.id !== id))} />
    </div>
  );
}
