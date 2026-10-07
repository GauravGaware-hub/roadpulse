import os
import numpy as np
import pandas as pd


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

EVENT_CONTEXT_FILE = os.path.join(
    BASE_DIR,
    "backend",
    "processed",
    "roadpulse_events_context.csv",
)

CLUSTERED_EVENTS_FILE = os.path.join(
    BASE_DIR,
    "backend",
    "processed",
    "roadpulse_events_clustered.csv",
)

CLUSTER_SUMMARY_FILE = os.path.join(
    BASE_DIR,
    "backend",
    "processed",
    "roadpulse_event_clusters.csv",
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "backend",
    "processed",
    "roadpulse_anomaly_scores.csv",
)


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

events = pd.read_csv(EVENT_CONTEXT_FILE)
clustered_events = pd.read_csv(CLUSTERED_EVENTS_FILE)
clusters = pd.read_csv(CLUSTER_SUMMARY_FILE)

print("=" * 90)
print("ROADPULSE ROAD-ANOMALY EVIDENCE SCORING")
print("=" * 90)

print(f"Events loaded: {len(events)}")
print(f"Clusters loaded: {len(clusters)}")


# ---------------------------------------------------------
# CHECK REQUIRED COLUMNS
# ---------------------------------------------------------

required_event_columns = [
    "event_id",
    "source_file",
    "annotation_label",
    "context",
    "motion_state",
]

required_cluster_columns = [
    "cluster_id",
    "latitude",
    "longitude",
]

missing_events = [
    c for c in required_event_columns
    if c not in events.columns
]

missing_clusters = [
    c for c in required_cluster_columns
    if c not in clusters.columns
]

if missing_events:
    print("\nERROR: Missing event columns:")
    print(missing_events)
    print("\nAvailable event columns:")
    print(events.columns.tolist())
    raise SystemExit(1)

if missing_clusters:
    print("\nERROR: Missing cluster columns:")
    print(missing_clusters)
    print("\nAvailable cluster columns:")
    print(clusters.columns.tolist())
    raise SystemExit(1)


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def clip_score(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def first_existing_column(df, candidates):
    for col in candidates:
        if col in df.columns:
            return col
    return None


# ---------------------------------------------------------
# TEMPORAL MOTION SCORE
# ---------------------------------------------------------

# These are prototype normalizations.
# They are intentionally not treated as calibrated probabilities.

if "peak_motion" in events.columns:
    motion_strength = pd.to_numeric(
        events["peak_motion"], errors="coerce"
    ).fillna(0)

elif "accel_mag_max" in events.columns:
    motion_strength = pd.to_numeric(
        events["accel_mag_max"], errors="coerce"
    ).fillna(0)

else:
    motion_strength = pd.Series(
        np.zeros(len(events)),
        index=events.index,
    )


# Normalize using robust percentile rather than an arbitrary
# physical threshold.

p95 = motion_strength.quantile(0.95)

if pd.isna(p95) or p95 <= 0:
    events["temporal_strength"] = 0.0
else:
    events["temporal_strength"] = (
        motion_strength / p95
    ).clip(0, 1)


# ---------------------------------------------------------
# DURATION SCORE
# ---------------------------------------------------------

duration_col = first_existing_column(
    events,
    ["duration", "duration_seconds"]
)

if duration_col:
    duration = pd.to_numeric(
        events[duration_col],
        errors="coerce"
    ).fillna(0)

    # Very long events should not automatically receive
    # maximum anomaly evidence.
    events["duration_score"] = (
        duration / 10.0
    ).clip(0, 1)

else:
    events["duration_score"] = 0.0


# ---------------------------------------------------------
# CONTEXT MODIFIER
# ---------------------------------------------------------

# Context is NOT a hard filter.
#
# Braking/acceleration can create abnormal sensor motion,
# so these contexts reduce confidence.
#
# MOVING_MOTION_EVENT is neutral.
# NORMAL_MOTION / STOPPED provide little evidence.

context_modifier = {
    "MOVING_MOTION_EVENT": 1.00,
    "DECELERATION": 0.70,
    "ACCELERATION": 0.75,
    "NORMAL_MOTION": 0.40,
    "STOPPED": 0.30,
}

events["context_modifier"] = (
    events["context"]
    .map(context_modifier)
    .fillna(0.70)
)


# ---------------------------------------------------------
# ANNOTATION INFORMATION
# ---------------------------------------------------------

# Annotation is useful for evaluating the prototype,
# but it must NOT be used as an input to the final score.
#
# UNKNOWN remains UNKNOWN.

def annotation_consistency(label):
    if label == "Bump":
        return 1.0

    if label == "Pothole":
        return 1.0

    if label == "Bump,Pothole":
        return 0.70

    return 0.0


events["annotation_reference"] = (
    events["annotation_label"]
    .apply(annotation_consistency)
)


# ---------------------------------------------------------
# MATCH EVENTS TO SPATIAL CLUSTERS
# ---------------------------------------------------------

# roadpulse_events_clustered.csv contains the individual
# events together with the cluster_id assigned to each event.

print(
    f"Clustered events loaded: {len(clustered_events)}"
)

required_clustered_columns = [
    "cluster_id",
    "source_file",
]

missing = [
    c for c in required_clustered_columns
    if c not in clustered_events.columns
]

if missing:
    print("\nERROR: Missing columns in clustered event file:")
    print(missing)
    print("\nAvailable columns:")
    print(clustered_events.columns.tolist())
    raise SystemExit(1)


# ---------------------------------------------------------
# MATCH EVENTS TO SPATIAL CLUSTERS
# ---------------------------------------------------------

# The two files use the same event coordinates:
# source_file + start + end

match_columns = [
    "source_file",
    "start",
    "end",
]

for col in match_columns:
    events[col] = pd.to_numeric(
        events[col],
        errors="coerce"
    ) if col != "source_file" else events[col].astype(str).str.strip()

    clustered_events[col] = pd.to_numeric(
        clustered_events[col],
        errors="coerce"
    ) if col != "source_file" else clustered_events[col].astype(str).str.strip()


# Round floating-point time values to avoid tiny
# representation differences.

events["_match_start"] = events["start"].round(3)
events["_match_end"] = events["end"].round(3)

clustered_events["_match_start"] = clustered_events["start"].round(3)
clustered_events["_match_end"] = clustered_events["end"].round(3)


cluster_mapping = clustered_events[
    [
        "source_file",
        "_match_start",
        "_match_end",
        "cluster_id",
    ]
].drop_duplicates(
    subset=[
        "source_file",
        "_match_start",
        "_match_end",
    ]
)


events = events.merge(
    cluster_mapping,
    on=[
        "source_file",
        "_match_start",
        "_match_end",
    ],
    how="left",
)


# ---------------------------------------------------------
# VERIFY EVENT → CLUSTER MAPPING
# ---------------------------------------------------------

matched_count = events["cluster_id"].notna().sum()
unmatched_count = events["cluster_id"].isna().sum()

print("\nEvent → cluster mapping:")
print(f"Matched:   {matched_count}")
print(f"Unmatched: {unmatched_count}")

if unmatched_count > 0:
    print("\nWARNING: Some events could not be matched.")
    print(
        events.loc[
            events["cluster_id"].isna(),
            ["event_id", "source_file", "start", "end"]
        ].head(10).to_string(index=False)
    )


# ---------------------------------------------------------
# CLUSTER SUMMARY
# ---------------------------------------------------------

cluster_summary = clusters.copy()

cluster_summary = cluster_summary.drop_duplicates(
    subset=["cluster_id"]
)

cluster_summary_columns = [
    "cluster_id",
    "event_count",
    "unique_recordings",
    "recording_groups",
    "bump_evidence",
    "pothole_evidence",
    "dominant_label",
    "label_consistency",
    "median_distance_m",
    "evidence_score",
]

cluster_summary_columns = [
    c
    for c in cluster_summary_columns
    if c in cluster_summary.columns
]

cluster_summary = cluster_summary[
    cluster_summary_columns
]

events = events.merge(
    cluster_summary,
    on="cluster_id",
    how="left",
    suffixes=("", "_cluster"),
)


# ---------------------------------------------------------
# CLUSTER EVIDENCE
# ---------------------------------------------------------

if "unique_recordings" in events.columns:

    unique_recordings = pd.to_numeric(
        events["unique_recordings"],
        errors="coerce"
    ).fillna(1)

    events["multi_recording_score"] = (
        (unique_recordings - 1) / 2
    ).clip(0, 1)

else:

    events["multi_recording_score"] = 0.0


# ---------------------------------------------------------
# SPATIAL AGREEMENT
# ---------------------------------------------------------

if "median_distance_m" in events.columns:

    distance = pd.to_numeric(
        events["median_distance_m"],
        errors="coerce"
    )

    events["spatial_score"] = (
        1.0 - (distance / 30.0)
    ).clip(0, 1)

    events["spatial_score"] = (
        events["spatial_score"]
        .fillna(0.0)
    )

else:

    events["spatial_score"] = 0.0


# ---------------------------------------------------------
# LABEL CONSISTENCY
# ---------------------------------------------------------

if "label_consistency" in events.columns:

    events["label_consistency_score"] = pd.to_numeric(
        events["label_consistency"],
        errors="coerce"
    ).fillna(0.0).clip(0, 1)

else:

    events["label_consistency_score"] = 0.0


# ---------------------------------------------------------
# CLUSTER EVIDENCE SCORE
# ---------------------------------------------------------

if "evidence_score" in events.columns:

    cluster_score = pd.to_numeric(
        events["evidence_score"],
        errors="coerce"
    ).fillna(0.0)

    events["cluster_evidence_score"] = (
        cluster_score / 100.0
    ).clip(0, 1)

else:

    events["cluster_evidence_score"] = 0.0


# ---------------------------------------------------------
# FINAL PROTOTYPE SCORE
# ---------------------------------------------------------

# IMPORTANT:
#
# This is NOT a machine-learning probability.
# It is an interpretable research prototype score.
#
# Temporal evidence:
#     25%
#
# Multi-recording:
#     30%
#
# Spatial agreement:
#     20%
#
# Label consistency:
#     15%
#
# Duration:
#     10%
#
# Context then modifies the result.

base_score = (
    0.25 * events["temporal_strength"]
    + 0.30 * events["multi_recording_score"]
    + 0.20 * events["spatial_score"]
    + 0.15 * events["label_consistency_score"]
    + 0.10 * events["duration_score"]
)

events["base_evidence_score"] = (
    base_score * 100
)

events["road_anomaly_score"] = (
    events["base_evidence_score"]
    * events["context_modifier"]
).clip(0, 100)


# ---------------------------------------------------------
# EVIDENCE LEVEL
# ---------------------------------------------------------

def evidence_level(score, recordings):

    if recordings >= 2 and score >= 60:
        return "HIGH"

    if recordings >= 2 and score >= 40:
        return "MODERATE"

    if score >= 40:
        return "WEAK"

    return "LOW"


recording_count = (
    pd.to_numeric(
        events.get(
            "unique_recordings",
            pd.Series(1, index=events.index)
        ),
        errors="coerce"
    )
    .fillna(1)
)

events["road_anomaly_level"] = [
    evidence_level(score, recs)
    for score, recs in zip(
        events["road_anomaly_score"],
        recording_count
    )
]


# ---------------------------------------------------------
# SORT
# ---------------------------------------------------------

events = events.sort_values(
    "road_anomaly_score",
    ascending=False
)


# ---------------------------------------------------------
# SAVE
# ---------------------------------------------------------

events.to_csv(
    OUTPUT_FILE,
    index=False
)


# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------

print("\n" + "=" * 90)
print("ROAD ANOMALY SCORE SUMMARY")
print("=" * 90)

print(
    "\nScore statistics:"
)

print(
    events["road_anomaly_score"]
    .describe()
    .round(2)
)


print(
    "\nEvidence levels:"
)

print(
    events["road_anomaly_level"]
    .value_counts()
)


print(
    "\nTop 20 events:"
)

display_columns = [
    "event_id",
    "source_file",
    "annotation_label",
    "context",
    "motion_state",
    "road_anomaly_score",
    "road_anomaly_level",
]

display_columns = [
    c for c in display_columns
    if c in events.columns
]

print(
    events[display_columns]
    .head(20)
    .to_string(index=False)
)


print(
    "\nSaved:"
)

print(OUTPUT_FILE)

print("=" * 90)