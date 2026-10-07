import Icon, { type IconName } from "../lib/Icon";
import type { Route } from "../lib/router";

const MAIN: { route: Route; label: string; icon: IconName }[] = [
  { route: "overview", label: "Overview", icon: "overview" },
  { route: "map", label: "Live Map", icon: "map" },
  { route: "events", label: "Road Events", icon: "bolt" },
  { route: "hotspots", label: "Hotspots", icon: "hotspot" },
  { route: "upload", label: "Sensor Upload", icon: "upload" },
  { route: "analytics", label: "Analytics", icon: "chart" },
];
const SYSTEM: { route: Route; label: string; icon: IconName }[] = [
  { route: "demo", label: "Demo Mode", icon: "play" },
  { route: "about", label: "About RoadPulse", icon: "info" },
  { route: "settings", label: "Settings", icon: "settings" },
];

interface Props {
  route: Route;
  go: (r: Route) => void;
  open: boolean;
  onClose: () => void;
  api: "checking" | "online" | "offline";
  version?: string;
}

export default function Sidebar({ route, go, open, onClose, api, version }: Props) {
  const item = (n: { route: Route; label: string; icon: IconName }) => (
    <a
      key={n.route}
      href={`#/${n.route}`}
      className={`nav-item${route === n.route ? " active" : ""}`}
      aria-current={route === n.route ? "page" : undefined}
      onClick={(e) => {
        e.preventDefault();
        go(n.route);
        onClose();
      }}
    >
      <Icon name={n.icon} />
      <span>{n.label}</span>
    </a>
  );

  return (
    <>
      {open && <div className="scrim" onClick={onClose} aria-hidden />}
      <aside className={`sidebar${open ? " open" : ""}`} aria-label="Primary">
        <div className="brand">
          <span className="brand-mark" aria-hidden>
            <Icon name="pulse" size={20} />
          </span>
          <div>
            <div className="brand-name">ROADPULSE</div>
            <div className="brand-sub">Road health intelligence</div>
          </div>
        </div>
        <nav>
          <div className="nav-label">Telemetry &amp; spatial</div>
          {MAIN.map(item)}
          <div className="nav-label">System operations</div>
          {SYSTEM.map(item)}
        </nav>
        <div className="sys-card">
          <div className="sys-row">
            <span className={`status-dot ${api}`} aria-hidden />
            <span className="mono">{api === "online" ? "API ONLINE" : api === "offline" ? "API OFFLINE" : "CHECKING API"}</span>
          </div>
          <div className="mono muted small">Heuristic pipeline{version ? ` · v${version}` : ""}</div>
          <div className="mono muted small">Research prototype</div>
        </div>
      </aside>
    </>
  );
}
