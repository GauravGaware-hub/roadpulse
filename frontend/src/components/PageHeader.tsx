import type { ReactNode } from "react";
import { ErrorState, LoadingState } from "./States";
import type { PageCtx } from "../pages/ctx";

export function PageHeader({ eyebrow, title, subtitle, children }: { eyebrow?: string; title: string; subtitle?: string; children?: ReactNode }) {
  return (
    <div className="page-header">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {subtitle && <p className="subtitle">{subtitle}</p>}
      </div>
      {children && <div className="page-actions">{children}</div>}
    </div>
  );
}

/** Renders children only when the core dataset has loaded; otherwise a loading or error state. */
export function DataGate({ ctx, children }: { ctx: PageCtx; children: ReactNode }) {
  const { data } = ctx;
  if (data.error) {
    return (
      <ErrorState
        title={ctx.recordingId ? "Could not load this recording" : "Backend unavailable"}
        message={data.error}
        onRetry={() => {
          data.reload();
          ctx.refreshApi();
        }}
      >
        {ctx.recordingId && (
          <button className="btn ghost" onClick={() => ctx.switchDataset(null)}>
            Use static Pune dataset
          </button>
        )}
      </ErrorState>
    );
  }
  if (data.loading && !data.stats) return <LoadingState label="Loading road-health data…" />;
  return <>{children}</>;
}
