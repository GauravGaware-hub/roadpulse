import { useEffect } from "react";
import { fmtCoord, fmtNum, fmtSec, fmtSpeed, hasGps } from "../lib/format";
import Icon from "../lib/Icon";
import type { RoadEvent } from "../types/roadpulse";
import { HeuristicBadge, SeverityBadge } from "./Badges";

const FUTURE_CLASSES = ["Normal", "Traffic event", "Braking", "Turning", "Speed breaker / bump", "Pothole", "Road anomaly", "Unknown"];

interface Props {
  event: RoadEvent | null;
  onClose: () => void;
  onOpenHotspot: (id: number) => void;
  onShowOnMap: (e: RoadEvent) => void;
}

/** Real before / peak / after acceleration values (median ±150 ms around the peak). Not a waveform. */
function PeakProfile({ e }: { e: RoadEvent }) {
  const vals = [
    { label: "Before", v: e.before_accel },
    { label: "Peak", v: e.peak_accel },
    { label: "After", v: e.after_accel },
  ];
  const max = Math.max(...vals.map((x) => x.v ?? 0), 0.001);
  return (
    <div className="profile" role="img" aria-label="Acceleration before, at and after the peak">
      {vals.map((x) => (
        <div key={x.label} className="profile-col">
          <div className="profile-bar-wrap">
            <div className={`profile-bar${x.label === "Peak" ? " peak" : ""}`} style={{ height: `${x.v === null ? 0 : (x.v / max) * 100}%` }} />
          </div>
          <span className="mono small">{x.v === null ? "–" : x.v.toFixed(1)}</span>
          <span className="muted small">{x.label}</span>
        </div>
      ))}
    </div>
  );
}

export default function EventDetail({ event: e, onClose, onOpenHotspot, onShowOnMap }: Props) {
  useEffect(() => {
    if (!e) return;
    const onKey = (ev: KeyboardEvent) => ev.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [e, onClose]);

  if (!e) return null;
  return (
    <>
      <div className="scrim" onClick={onClose} aria-hidden />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={`Event ${e.id} details`}>
        <div className="panel-head">
          <div>
            <div className="eyebrow">Impact observation</div>
            <h2>Event #{e.id}</h2>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close event details" autoFocus>
            <Icon name="x" />
          </button>
        </div>

        <div className="badges">
          <SeverityBadge classification={e.classification} />
          <HeuristicBadge />
        </div>
        <p className="muted small">
          Classification: <b>Potential road anomaly</b> (heuristic impact scoring). Not a validated pothole detection.
        </p>

        <div className="score">
          <div className="row between">
            <span className="k">Impact score</span>
            <span className="mono score-num">{e.impact_score.toFixed(0)} / 100</span>
          </div>
          <div className="meter" aria-hidden>
            <div style={{ width: `${Math.max(0, Math.min(100, e.impact_score))}%` }} />
          </div>
        </div>

        <div className="kv-grid">
          <div>
            <span className="k">Peak acceleration</span>
            <span className="v">{fmtNum(e.peak_accel)} m/s²</span>
          </div>
          <div>
            <span className="k">Peak gyroscope</span>
            <span className="v">{fmtNum(e.peak_gyro_near, 2)} rad/s</span>
          </div>
          <div>
            <span className="k">Peak prominence</span>
            <span className="v">{fmtNum(e.peak_prominence, 2)}×</span>
          </div>
          <div>
            <span className="k">Peak width</span>
            <span className="v">{e.peak_width === null ? "–" : `${(e.peak_width * 1000).toFixed(0)} ms`}</span>
          </div>
          <div className="wide">
            <span className="k">Speed</span>
            <span className="v">
              {fmtSpeed(e.speed)}
              {e.speed_band ? ` · ${e.speed_band.replace("_", " ").toLowerCase()}` : ""}
            </span>
          </div>
        </div>

        <h3>Peak profile</h3>
        <PeakProfile e={e} />
        <p className="muted small">
          Median acceleration (m/s²) in the 150 ms before and after the peak. A raw sensor waveform is not available from the API.
        </p>

        <div className="kv-list">
          <div>
            <span className="k">Coordinates</span>
            <span className="mono">
              {fmtCoord(e.latitude)}, {fmtCoord(e.longitude)}
            </span>
          </div>
          <div>
            <span className="k">Time</span>
            <span className="mono">
              t = {fmtSec(e.peak_time)} (window {fmtSec(e.start)}–{fmtSec(e.end)} into recording)
            </span>
          </div>
          <div>
            <span className="k">Associated hotspot</span>
            {e.hotspot_id !== null ? (
              <button className="link-btn" onClick={() => onOpenHotspot(e.hotspot_id as number)}>
                Hotspot #{e.hotspot_id}
              </button>
            ) : (
              <span className="muted">None (below clustering threshold)</span>
            )}
          </div>
        </div>

        <div className="callout future">
          <div className="eyebrow">Future classification layer · not active</div>
          <p className="small">
            Current engine: heuristic motion detection and impact scoring. A validated classifier is not connected, so no class or probability is shown. Planned classes:
          </p>
          <div className="chips">
            {FUTURE_CLASSES.map((c) => (
              <span key={c} className="chip disabled">
                {c}
              </span>
            ))}
          </div>
        </div>

        <div className="row gap wrap">
          {hasGps(e) && (
            <button className="btn primary" onClick={() => onShowOnMap(e)}>
              <Icon name="map" size={15} /> Show on map
            </button>
          )}
          <button className="btn ghost" onClick={onClose}>
            Close
          </button>
        </div>
      </aside>
    </>
  );
}
