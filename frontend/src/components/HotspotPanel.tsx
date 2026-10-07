import { fmtCoord, fmtNum, fmtSec } from "../lib/format";
import Icon from "../lib/Icon";
import type { HotspotDetail, RoadEvent } from "../types/roadpulse";
import { ConfidenceBadge, PriorityBadge, SeverityBadge } from "./Badges";
import { EmptyState, ErrorState, LoadingState } from "./States";

const CLUSTER_RADIUS_M = 30; // DBSCAN radius used by the backend clustering

interface Props {
  hotspot: HotspotDetail | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onOpenEvent: (e: RoadEvent) => void;
  onRetry?: () => void;
}

// Built only from values the backend provides.
function why(h: HotspotDetail): string {
  const parts = [`${h.event_count} impact observation${h.event_count === 1 ? "" : "s"} recorded within a ${CLUSTER_RADIUS_M} m clustering radius.`];
  if (h.strong_events > 0) parts.push(`${h.strong_events} ${h.strong_events === 1 ? "is" : "are"} classified as strong impact.`);
  parts.push(`Maximum heuristic impact score: ${h.max_impact_score.toFixed(0)} / 100.`);
  parts.push(
    h.event_count >= 2
      ? "The same location produced repeated impacts during this single trip. That makes a one-off disturbance less likely, but it is not independent confirmation."
      : "Only one observation so far. Keep monitoring and wait for further passes before drawing conclusions.",
  );
  return parts.join(" ");
}

export default function HotspotPanel({ hotspot: h, loading, error, onClose, onOpenEvent, onRetry }: Props) {
  if (error) return <ErrorState title="Could not load hotspot" message={error} onRetry={onRetry} />;
  if (loading) return <LoadingState label="Loading hotspot…" />;
  if (!h) {
    return (
      <EmptyState title="No hotspot selected">
        Select a hotspot marker on the map, or a hotspot from the list, to see observations, scores and linked events.
      </EmptyState>
    );
  }
  return (
    <div className="panel-body">
      <div className="panel-head">
        <div>
          <div className="eyebrow">Potential road anomaly · repeated observations</div>
          <h2>Hotspot #{h.id}</h2>
        </div>
        <button className="icon-btn" onClick={onClose} aria-label="Close hotspot details">
          <Icon name="x" />
        </button>
      </div>
      <div className="badges">
        <PriorityBadge level={h.risk_level} />
        <ConfidenceBadge level={h.confidence_level} />
        {h.event_count >= 2 && <span className="badge tone-info">Repeated hotspot</span>}
      </div>
      <div className="loc">
        <Icon name="pin" size={15} />
        <span className="mono">
          {fmtCoord(h.latitude)}, {fmtCoord(h.longitude)}
        </span>
      </div>

      <div className="kv-grid">
        <div>
          <span className="k">Observations</span>
          <span className="v">{h.event_count}</span>
        </div>
        <div>
          <span className="k">Strong / moderate</span>
          <span className="v">
            {h.strong_events} / {h.moderate_events}
          </span>
        </div>
        <div>
          <span className="k">Max impact score</span>
          <span className="v">{h.max_impact_score.toFixed(0)}</span>
        </div>
        <div>
          <span className="k">Mean impact score</span>
          <span className="v">{h.mean_impact_score.toFixed(1)}</span>
        </div>
        <div>
          <span className="k">Max peak accel</span>
          <span className="v">{fmtNum(h.max_peak_accel)} m/s²</span>
        </div>
        <div>
          <span className="k">Independent recordings</span>
          <span className="v">1</span>
        </div>
      </div>
      <p className="muted small">Single trip: multi-vehicle confirmation is not yet available.</p>

      <div className="callout">
        <div className="eyebrow">Why this location matters</div>
        <p>{why(h)}</p>
      </div>

      <div className="kv-list">
        <div>
          <span className="k">First observation</span>
          <span className="mono">t = {fmtSec(h.first_event)} into recording</span>
        </div>
        <div>
          <span className="k">Last observation</span>
          <span className="mono">t = {fmtSec(h.last_event)} into recording</span>
        </div>
      </div>

      <h3>Associated events ({h.events.length})</h3>
      {h.events.length === 0 ? (
        <p className="muted small">No linked events.</p>
      ) : (
        <ul className="linked">
          {h.events.map((e) => (
            <li key={e.id}>
              <button onClick={() => onOpenEvent(e)}>
                <span className="mono">Event #{e.id}</span>
                <SeverityBadge classification={e.classification} />
                <span className="mono">score {e.impact_score.toFixed(0)}</span>
                <span className="mono">{fmtNum(e.peak_accel)} m/s²</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="muted small">
        Priority combines the maximum impact score with repeated observations; confidence reflects the observation count. Both are prototype heuristics. They are not scientifically validated.
      </p>
    </div>
  );
}
