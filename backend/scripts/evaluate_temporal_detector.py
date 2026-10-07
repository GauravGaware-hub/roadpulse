import pandas as pd


GROUND_TRUTH_FILE = (
    "backend/processed/roadpulse_ground_truth_events.csv"
)

DETECTED_FILE = (
    "backend/processed/roadpulse_events_clustered.csv"
)


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

gt = pd.read_csv(GROUND_TRUTH_FILE)
det = pd.read_csv(DETECTED_FILE)


# ---------------------------------------------------------
# NORMALIZE LABELS
# ---------------------------------------------------------

def normalize_label(label):
    if label == "Bump":
        return "Bump"

    if label == "Pothole":
        return "Pothole"

    return "UNKNOWN"


gt["label"] = gt["label"].apply(normalize_label)
det["label"] = det["label"].apply(normalize_label)


# ---------------------------------------------------------
# TEMPORAL OVERLAP
# ---------------------------------------------------------

def overlaps(a_start, a_end, b_start, b_end):

    return (
        max(a_start, b_start)
        <= min(a_end, b_end)
    )


# ---------------------------------------------------------
# MATCH EVENTS
# ---------------------------------------------------------

matched_gt = set()
matched_det = set()

matches = []


for det_idx, det_row in det.iterrows():

    source = det_row["source_file"]

    candidates = gt[
        (gt["source_file"] == source)
        & (~gt.index.isin(matched_gt))
    ]

    best_match = None
    best_overlap = 0.0

    for gt_idx, gt_row in candidates.iterrows():

        if not overlaps(
            det_row["start"],
            det_row["end"],
            gt_row["start"],
            gt_row["end"]
        ):
            continue

        overlap_start = max(
            det_row["start"],
            gt_row["start"]
        )

        overlap_end = min(
            det_row["end"],
            gt_row["end"]
        )

        overlap_duration = max(
            0,
            overlap_end - overlap_start
        )

        if overlap_duration > best_overlap:

            best_overlap = overlap_duration
            best_match = gt_idx

    if best_match is not None:

        matched_gt.add(best_match)
        matched_det.add(det_idx)

        matches.append({
            "detected_index": det_idx,
            "ground_truth_index": best_match,
            "source_file": source,
            "detected_label": det_row["label"],
            "ground_truth_label": gt.loc[
                best_match,
                "label"
            ],
            "overlap_seconds": best_overlap
        })


# ---------------------------------------------------------
# BASIC COUNTS
# ---------------------------------------------------------

tp = len(matched_gt)

fp = len(det) - len(matched_det)

fn = len(gt) - len(matched_gt)


def safe_div(a, b):

    if b == 0:
        return 0.0

    return a / b


precision = safe_div(
    tp,
    tp + fp
)

recall = safe_div(
    tp,
    tp + fn
)

f1 = safe_div(
    2 * precision * recall,
    precision + recall
)


print("=" * 60)
print("ROADPULSE TEMPORAL EVENT DETECTOR")
print("=" * 60)

print()
print("GROUND-TRUTH EVENTS :", len(gt))
print("DETECTED EVENTS     :", len(det))

print()
print("TRUE POSITIVES      :", tp)
print("FALSE POSITIVES     :", fp)
print("FALSE NEGATIVES     :", fn)

print()
print("PRECISION           :", round(precision, 4))
print("RECALL              :", round(recall, 4))
print("F1 SCORE            :", round(f1, 4))


# ---------------------------------------------------------
# LABEL-SPECIFIC EVALUATION
# ---------------------------------------------------------

print()
print("=" * 60)
print("LABEL-SPECIFIC RESULTS")
print("=" * 60)


for label in ["Bump", "Pothole"]:

    label_gt = gt[
        gt["label"] == label
    ]

    label_det = det[
        det["label"] == label
    ]

    label_gt_indices = set(label_gt.index)

    label_det_indices = set(label_det.index)

    label_matches = [
        m for m in matches
        if m["ground_truth_label"] == label
        and m["detected_label"] == label
    ]

    label_tp = len(label_matches)

    label_fn = len(
        label_gt_indices
        - {
            m["ground_truth_index"]
            for m in label_matches
        }
    )

    label_fp = len(
        label_det_indices
        - {
            m["detected_index"]
            for m in label_matches
        }
    )

    label_precision = safe_div(
        label_tp,
        label_tp + label_fp
    )

    label_recall = safe_div(
        label_tp,
        label_tp + label_fn
    )

    label_f1 = safe_div(
        2 * label_precision * label_recall,
        label_precision + label_recall
    )

    print()
    print(label)

    print("  Ground truth :", len(label_gt))
    print("  Detected     :", len(label_det))
    print("  TP           :", label_tp)
    print("  FP           :", label_fp)
    print("  FN           :", label_fn)

    print(
        "  Precision    :",
        round(label_precision, 4)
    )

    print(
        "  Recall       :",
        round(label_recall, 4)
    )

    print(
        "  F1           :",
        round(label_f1, 4)
    )


# ---------------------------------------------------------
# SAVE MATCHES
# ---------------------------------------------------------

matches_df = pd.DataFrame(matches)

output = (
    "backend/processed/"
    "roadpulse_temporal_matches.csv"
)

matches_df.to_csv(
    output,
    index=False
)

print()
print("MATCHES SAVED:")
print(output)