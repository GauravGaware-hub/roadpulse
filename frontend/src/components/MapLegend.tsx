import { TONE_COLOR } from "../lib/format";

const swatch = (color: string, extra?: React.CSSProperties) => <i className="sw" style={{ background: color, ...extra }} aria-hidden />;

export default function MapLegend() {
  return (
    <div className="legend" aria-label="Map legend">
      <div className="legend-group">
        <span className="legend-title">Event markers (impact shape)</span>
        <span>{swatch(TONE_COLOR.crit)}Strong impact</span>
        <span>{swatch(TONE_COLOR.warn)}Moderate impact</span>
        <span>{swatch(TONE_COLOR.info)}Weak impact</span>
      </div>
      <div className="legend-group">
        <span className="legend-title">Hotspots (potential road anomaly)</span>
        <span>
          <i className="sw ring-sw" aria-hidden />
          Repeated hotspot (2+ observations)
        </span>
        <span className="muted">Colour = inspection priority · size = observations</span>
      </div>
    </div>
  );
}
