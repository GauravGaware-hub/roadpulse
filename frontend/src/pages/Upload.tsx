import { PageHeader } from "../components/PageHeader";
import UploadPanel from "../components/UploadPanel";
import type { PageCtx } from "./ctx";

export default function Upload({ ctx }: { ctx: PageCtx }) {
  return (
    <div className="stack">
      <PageHeader
        eyebrow="Sensor ingestion"
        title="Sensor Upload"
        subtitle="Upload one Sensor Logger recording. RoadPulse synchronises the sensors, detects motion events, scores them and clusters repeated locations."
      />
      <UploadPanel recordingId={ctx.recordingId} onViewResults={ctx.switchDataset} onUseBaseline={() => ctx.switchDataset(null)} onBack={() => ctx.go("overview")} notify={ctx.notify} />
    </div>
  );
}
