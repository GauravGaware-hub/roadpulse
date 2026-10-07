import { PageHeader } from "../components/PageHeader";
import { StatusBadge } from "../components/Badges";
import { ToggleField } from "../components/FilterBar";
import Icon from "../lib/Icon";
import type { PageCtx } from "./ctx";

const API_BASE = ((import.meta.env.VITE_API_BASE_URL as string | undefined) ?? (import.meta.env.DEV ? "http://localhost:8000" : "")).replace(/\/+$/, "");

const Row = ({ k, children }: { k: string; children: React.ReactNode }) => (
  <div className="set-row">
    <span className="k">{k}</span>
    <span className="set-val">{children}</span>
  </div>
);

export default function Settings({ ctx }: { ctx: PageCtx }) {
  const { recordingId, apiStatus } = ctx;
  return (
    <div className="stack">
      <PageHeader eyebrow="Configuration" title="Settings" subtitle="Dataset, API connection and system information." />
      <div className="grid-2">
        <section className="card">
          <h3>Dataset</h3>
          <Row k="Current dataset">{recordingId ? "Uploaded recording" : "Static Pune dataset"}</Row>
          <Row k="Recording ID">
            <span className="mono wrap-any">{recordingId ?? "None (static dataset)"}</span>
          </Row>
          <Row k="Scope">One vehicle · one trip</Row>
          {recordingId && (
            <button className="btn ghost" onClick={() => ctx.switchDataset(null)}>
              Switch to static Pune dataset
            </button>
          )}
        </section>

        <section className="card">
          <h3>Backend / API</h3>
          <Row k="Connection">
            <StatusBadge tone={apiStatus === "online" ? "ok" : apiStatus === "offline" ? "crit" : "mute"}>
              {apiStatus === "online" ? "Connected" : apiStatus === "offline" ? "Unreachable" : "Checking"}
            </StatusBadge>
          </Row>
          <Row k="API base URL">
            <span className="mono wrap-any">{API_BASE || "Same origin"}</span>
          </Row>
          <button className="btn ghost" onClick={ctx.refreshApi}>
            <Icon name="refresh" size={14} /> Re-check connection
          </button>
        </section>

        <section className="card">
          <h3>Display</h3>
          <ToggleField label="Dark map tiles" checked={ctx.darkTiles} onChange={ctx.setDarkTiles} />
          <p className="muted small">Darkens the OpenStreetMap base layer to match the interface. Saved in this browser only. The interface itself is dark-only.</p>
        </section>

        <section className="card">
          <h3>System</h3>
          <Row k="Backend version">{ctx.apiVersion ?? "Unavailable"}</Row>
          <Row k="Detection pipeline">Heuristic (rule-based)</Row>
          <Row k="ML model">
            <StatusBadge tone="mute">Not connected</StatusBadge>
          </Row>
          <p className="muted small">Research classifiers exist in the project but are not used by the application, and do not affect any result shown here.</p>
        </section>
      </div>
    </div>
  );
}
