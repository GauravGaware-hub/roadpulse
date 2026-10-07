import Icon from "../lib/Icon";
import type { Route } from "../lib/router";
import DatasetIndicator from "./DatasetIndicator";

const TITLES: Record<Route, string> = {
  overview: "Overview",
  map: "Live Map",
  events: "Road Events",
  hotspots: "Hotspots",
  upload: "Sensor Upload",
  analytics: "Analytics",
  demo: "Demo Mode",
  about: "About RoadPulse",
  settings: "Settings",
};

interface Props {
  route: Route;
  go: (r: Route) => void;
  recordingId: string | null;
  onUseStatic: () => void;
  onMenu: () => void;
}

export default function TopBar({ route, go, recordingId, onUseStatic, onMenu }: Props) {
  return (
    <header className="topbar">
      <button className="icon-btn menu-btn" onClick={onMenu} aria-label="Open navigation">
        <Icon name="menu" />
      </button>
      <div className="crumb">
        <span className="crumb-root">RoadPulse</span>
        <span className="muted">/</span>
        <span>{TITLES[route]}</span>
      </div>
      <div className="topbar-dataset">
        <DatasetIndicator recordingId={recordingId} onUseStatic={onUseStatic} compact />
      </div>
      <button className="btn ghost" onClick={() => go("upload")}>
        <Icon name="upload" size={15} />
        <span className="hide-sm">Upload Sensor Data</span>
      </button>
    </header>
  );
}
