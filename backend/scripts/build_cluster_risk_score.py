import os
import pandas as pd


BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

CLUSTER_FILE = os.path.join(
    BASE_DIR,
    "backend",
    "processed",
    "roadpulse_event_clusters.csv",
)

EVENT_FILE = os.path.join(
    BASE_DIR,
    "backend",
    "processed",
    "roadpulse_events_clustered.csv",
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "backend",
    "processed",
    "roadpulse_cluster_risk_scores.csv",
)


print("=" * 90)
print("ROADPULSE CLUSTER-LEVEL ROAD RISK SCORING")
print("=" * 90)


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

clusters = pd.read_csv(CLUSTER_FILE)
events = pd.read_csv(EVENT_FILE)

print(f"Clusters loaded: {len(clusters)}")
print(f"Events loaded:   {len(events)}")


# ---------------------------------------------------------
# DUPLICATE RECORDING GROUPS
# ---------------------------------------------------------

duplicate_groups = {
    "30.csv": "DUP_0027",
    "31.csv": "DUP_0027",

    "45.csv": "DUP_0041",
    "78.csv": "DUP_0041",

    "46.csv": "DUP_0042",
    "47.csv": "DUP_0042",
    "68.csv": "DUP_0042",
    "79.csv": "DUP_0042",
}


def recording_group(filename):

    filename = str(filename).strip()

    if filename in duplicate_groups:
        return duplicate_groups[filename]

    return f"REC_{filename}"


events["recording_group"] = (
    events["source_file"]
    .apply(recording_group)
)


# ---------------------------------------------------------
# BUILD DUPLICATE-AWARE CLUSTER EVIDENCE
# ---------------------------------------------------------

cluster_evidence = []

for cluster_id, group in events.groupby("cluster_id"):

    recording_groups = sorted(
        group["recording_group"]
        .dropna()
        .unique()
        .tolist()
    )

    original_recordings = sorted(
        group["source_file"]
        .dropna()
        .unique()
        .tolist()
    )

    labels = (
        group["label"]
        .fillna("UNKNOWN")
        .astype(str)
        .tolist()
    )

    # Treat combined labels as containing both types.
    expanded_labels = []

    for label in labels:

        if label == "Bump,Pothole":
            expanded_labels.extend(
                ["Bump", "Pothole"]
            )
        else:
            expanded_labels.append(label)

    labels = expanded_labels

    bump_count = sum(
        1 for label in labels
        if label == "Bump"
    )

    pothole_count = sum(
        1 for label in labels
        if label == "Pothole"
    )

    unknown_count = sum(
        1 for label in labels
        if label == "UNKNOWN"
    )

    mixed_count = sum(
        1 for label in labels
        if label == "Bump,Pothole"
    )

    cluster_evidence.append({
        "cluster_id": cluster_id,
        "original_recordings": len(original_recordings),
        "independent_recording_groups": len(recording_groups),
        "recording_groups": "|".join(recording_groups),
        "bump_events": bump_count,
        "pothole_events": pothole_count,
        "unknown_event_count": unknown_count,
        "mixed_events": mixed_count,
    })


evidence_df = pd.DataFrame(cluster_evidence)


# ---------------------------------------------------------
# MERGE ONLY OUR DUPLICATE-AWARE EVIDENCE
# ---------------------------------------------------------

clusters = clusters.drop(
    columns=[
        "unknown_events",
        "bump_evidence",
        "pothole_evidence",
    ],
    errors="ignore",
)

clusters = clusters.merge(
    evidence_df,
    on="cluster_id",
    how="left",
)


# ---------------------------------------------------------
# FILL MISSING VALUES
# ---------------------------------------------------------

count_columns = [
    "event_count",
    "original_recordings",
    "independent_recording_groups",
    "bump_events",
    "pothole_events",
    "unknown_event_count",
    "mixed_events",
]

for col in count_columns:

    if col in clusters.columns:
        clusters[col] = (
            pd.to_numeric(
                clusters[col],
                errors="coerce",
            )
            .fillna(0)
        )


# ---------------------------------------------------------
# CONTEXT-AWARE INDEPENDENT RECORDING SCORE
# ---------------------------------------------------------

# STOPPED events are not treated as independent road-condition
# confirmation. VERY_SLOW and faster states remain valid evidence.

valid_motion_states = {
    "VERY_SLOW",
    "SLOW",
    "MOVING",
    "FAST",
}

event_context = (
    events.groupby("cluster_id")["motion_state"]
    .apply(
        lambda states: any(
            state in valid_motion_states
            for state in states
        )
    )
)

clusters["has_moving_evidence"] = (
    clusters["cluster_id"]
    .map(event_context)
    .fillna(False)
)

independent_count = (
    clusters["independent_recording_groups"]
)

clusters["independent_recording_score"] = (
    independent_count / 3.0
).clip(0, 1)

# A cluster containing only STOPPED events cannot receive
# independent road-condition confirmation.
clusters.loc[
    ~clusters["has_moving_evidence"],
    "independent_recording_score"
] = 0


# ---------------------------------------------------------
# OBSERVATION SCORE
# ---------------------------------------------------------

event_count = clusters["event_count"]

clusters["observation_score"] = (
    event_count / 5.0
).clip(0, 1)


# ---------------------------------------------------------
# LABEL CONSISTENCY
# ---------------------------------------------------------

bump = clusters["bump_events"]
pothole = clusters["pothole_events"]
mixed = clusters["mixed_events"]

total_labelled = bump + pothole

clusters["classification_consistency"] = 0.0

pure_mask = total_labelled > 0

clusters.loc[
    pure_mask,
    "classification_consistency"
] = (
    bump[pure_mask]
    .where(
        bump[pure_mask] >= pothole[pure_mask],
        pothole[pure_mask],
    )
    /
    total_labelled[pure_mask]
).clip(0, 1)


# Mixed Bump/Pothole observations reduce
# exact classification confidence.

mixed_mask = mixed > 0

clusters.loc[
    mixed_mask,
    "classification_consistency"
] *= 0.70


# ---------------------------------------------------------
# ANOMALY PRESENCE SCORE
# ---------------------------------------------------------

clusters["anomaly_presence_score"] = (
    (
        clusters["bump_events"]
        + clusters["pothole_events"]
        + (
            clusters["mixed_events"]
            * 0.5
        )
    )
    /
    clusters["event_count"].replace(0, 1)
).clip(0, 1)


# ---------------------------------------------------------
# CONFIRMATION BONUS
# ---------------------------------------------------------

clusters["confirmation_bonus"] = 0.0

clusters.loc[
    independent_count >= 2,
    "confirmation_bonus"
] = 1.0


# ---------------------------------------------------------
# ROAD RISK SCORE
# ---------------------------------------------------------
#
# Prototype research score:
#
# Independent recordings       55%
# Observation evidence          5%
# Classification consistency   15%
# Anomaly presence             15%
# Confirmation bonus           10%
#
# NOT a probability.
# ---------------------------------------------------------

clusters["road_risk_score"] = (
    55
    * clusters["independent_recording_score"]

    + 5
    * clusters["observation_score"]

    + 15
    * clusters["classification_consistency"]

    + 15
    * clusters["anomaly_presence_score"]

    + 10
    * clusters["confirmation_bonus"]
).clip(0, 100)


# ---------------------------------------------------------
# ROAD ANOMALY TYPE
# ---------------------------------------------------------

def determine_type(row):

    bump = row["bump_events"]
    pothole = row["pothole_events"]

    if bump == 0 and pothole == 0:
        return "UNKNOWN ROAD ANOMALY"

    if bump > 0 and pothole > 0:
        return "ROAD ANOMALY - TYPE UNCERTAIN"

    if pothole > bump:
        return "POTHOLE"

    return "BUMP"


clusters["road_anomaly_type"] = (
    clusters.apply(
        determine_type,
        axis=1,
    )
)


# ---------------------------------------------------------
# RISK LEVEL
# ---------------------------------------------------------

def risk_level(row):

    score = row["road_risk_score"]
    recordings = row["independent_recording_groups"]

    if recordings >= 2 and score >= 60:
        return "HIGH"

    if recordings >= 2 and score >= 40:
        return "MODERATE"

    if score >= 40:
        return "WEAK"

    return "LOW"


clusters["risk_level"] = (
    clusters.apply(
        risk_level,
        axis=1,
    )
)


# ---------------------------------------------------------
# MAINTENANCE PRIORITY
# ---------------------------------------------------------

def maintenance_priority(row):

    if row["risk_level"] == "HIGH":
        return "PRIORITY INSPECTION"

    if row["risk_level"] == "MODERATE":
        return "INSPECT"

    if row["risk_level"] == "WEAK":
        return "MONITOR"

    return "INSUFFICIENT EVIDENCE"


clusters["maintenance_priority"] = (
    clusters.apply(
        maintenance_priority,
        axis=1,
    )
)


# ---------------------------------------------------------
# SORT
# ---------------------------------------------------------

clusters = clusters.sort_values(
    [
        "road_risk_score",
        "independent_recording_groups",
    ],
    ascending=False,
)


# ---------------------------------------------------------
# SAVE
# ---------------------------------------------------------

clusters.to_csv(
    OUTPUT_FILE,
    index=False,
)


# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------

print("\n" + "=" * 90)
print("ROADPULSE CLUSTER RISK SUMMARY")
print("=" * 90)


multi_count = (
    clusters[
        clusters["independent_recording_groups"] >= 2
    ]
    .shape[0]
)

print(
    "\nClusters with independent "
    f"multi-recording evidence: {multi_count}"
)


print("\nRisk levels:")

print(
    clusters["risk_level"]
    .value_counts()
)


display_columns = [
    "cluster_id",
    "latitude",
    "longitude",
    "event_count",
    "original_recordings",
    "independent_recording_groups",
    "recording_groups",
    "bump_events",
    "pothole_events",
    "unknown_event_count",
    "road_anomaly_type",
    "road_risk_score",
    "risk_level",
    "maintenance_priority",
]


print("\nMulti-recording clusters:")

print(
    clusters[
        clusters["independent_recording_groups"] >= 2
    ][display_columns]
    .to_string(index=False)
)


print("\nTop 20 clusters:")

print(
    clusters[
        display_columns
    ]
    .head(20)
    .to_string(index=False)
)


print("\nSaved:")
print(OUTPUT_FILE)

print("=" * 90)