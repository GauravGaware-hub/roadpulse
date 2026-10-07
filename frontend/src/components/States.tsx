import type { ReactNode } from "react";
import Icon from "../lib/Icon";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="state" role="status" aria-live="polite">
      <span className="spinner" aria-hidden />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="state">
      <strong>{title}</strong>
      {children && <span className="muted">{children}</span>}
    </div>
  );
}

export function ErrorState({ title = "Something went wrong", message, onRetry, children }: { title?: string; message: string; onRetry?: () => void; children?: ReactNode }) {
  return (
    <div className="state state-error" role="alert">
      <span className="state-icon">
        <Icon name="alert" size={20} />
      </span>
      <strong>{title}</strong>
      <span>{message}</span>
      <div className="row gap">
        {onRetry && (
          <button className="btn ghost" onClick={onRetry}>
            <Icon name="refresh" size={14} /> Retry
          </button>
        )}
        {children}
      </div>
    </div>
  );
}

export function Disclaimer({ children }: { children?: ReactNode }) {
  return (
    <p className="disclaimer-line">
      <Icon name="info" size={14} />
      <span>
        {children ??
          "Prototype evidence from a single Pune sensor recording. Independent multi-vehicle confirmation is part of the planned RoadPulse system. Results are heuristic motion observations, not validated road-damage classifications."}
      </span>
    </p>
  );
}
