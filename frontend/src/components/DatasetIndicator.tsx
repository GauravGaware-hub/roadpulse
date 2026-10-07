import { shortId } from "../lib/format";
import Icon from "../lib/Icon";

interface Props {
  recordingId: string | null;
  onUseStatic: () => void;
  compact?: boolean;
}

/** Shows which dataset is active: the static Pune research dataset or an uploaded recording. */
export default function DatasetIndicator({ recordingId, onUseStatic, compact }: Props) {
  if (!recordingId) {
    return (
      <span className="dataset-chip" title="Static Pune research dataset (one vehicle, one trip)">
        <Icon name="database" size={14} />
        <span>
          Dataset: <b>Static Pune dataset</b>
        </span>
      </span>
    );
  }
  return (
    <span className="dataset-chip live" title={`Uploaded recording ${recordingId}`}>
      <Icon name="upload" size={14} />
      <span>
        Dataset: <b>Uploaded recording</b>
      </span>
      <span className="mono">{shortId(recordingId)}</span>
      {!compact && <span className="muted">One vehicle / one trip · heuristic impact observations</span>}
      <button className="link-btn" onClick={onUseStatic}>
        Static Pune dataset
      </button>
    </span>
  );
}
