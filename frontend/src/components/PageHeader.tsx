import { useEffect, useState, type ReactNode } from "react";
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
  const [slow, setSlow] = useState(false);
  const waiting = data.loading && !data.stats;
  useEffect(() => {
    setSlow(false);
    if (!waiting) return;
    const t = setTimeout(() => setSlow(true), 4000);
    return () => clearTimeout(t);
  }, [waiting]);

  if (data.error) {
    const gone = ctx.recordingId !== null && /404|not found/i.test(data.error);
    return (
      <ErrorState
        title={gone ? "This recording is no longer on the server" : ctx.recordingId ? "Could not load this recording" : "Backend unavailable"}
        message={gone ? "Uploaded recordings are stored on the server's local disk, and the free server clears them when it restarts. Upload the files again to recreate it, or return to the baseline dataset." : data.error}
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
  if (waiting) {
    return <LoadingState label={slow ? "Still loading. The free server may be waking up after being idle; this can take up to a minute." : "Loading road-health data…"} />;
  }
  return <>{children}</>;
}
