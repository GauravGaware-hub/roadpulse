import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_FILE = BASE_DIR / "backend" / "processed" / "roadpulse_events_clustered.csv"
OUTPUT_FILE = BASE_DIR / "backend" / "processed" / "roadpulse_cluster_evidence.csv"


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

# Prototype weights only.
# These are NOT experimentally calibrated final weights.
WEIGHT_RECORDINGS = 40
WEIGHT_CONSISTENCY = 25
WEIGHT_SPATIAL = 20
WEIGHT_INTENSITY = 15


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

required_columns = [
    "cluster_id",
    "source_file",
    "latitude",
    "longitude",
    "peak_motion",
    "max_accel",
    "max_gyro",
    "label",
]

missing = [c for c in required_columns if c not in df.columns]

if missing:
    raise ValueError(f"Missing columns: {missing}")


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def spatial_distance_meters(lat1, lon1, lat2, lon2):
    """
    Approximate distance between two GPS coordinates.
    Good enough for small clusters.
    """

    lat_scale = 111_320
    lon_scale = 111_320 * np.cos(np.radians(lat1))

    dx = (lon1 - lon2) * lon_scale
    dy = (lat1 - lat2) * lat_scale

    return np.sqrt(dx * dx + dy * dy)


def normalize(value, low, high):
    if high == low:
        return 0.5

    value = (value - low) / (high - low)

    return float(np.clip(value, 0, 1))


# ---------------------------------------------------------
# BUILD CLUSTER SCORES
# ---------------------------------------------------------

results = []

for cluster_id, group in df.groupby("cluster_id"):

    # Ignore invalid cluster IDs
    if pd.isna(cluster_id):
        continue

    unique_recordings = group["source_file"].nunique()
    event_count = len(group)

    center_lat = group["latitude"].median()
    center_lon = group["longitude"].median()

    # -----------------------------------------------------
    # 1. RECORDING EVIDENCE
    # -----------------------------------------------------

    # 1 recording = weak
    # 2 = moderate
    # 3+ = increasingly strong
    #
    # Cap at 5 so a cluster with many repeated files
    # does not completely dominate the score.

    recording_score = min(unique_recordings / 5, 1.0)


    # -----------------------------------------------------
    # 2. LABEL CONSISTENCY
    # -----------------------------------------------------

    labels = group["label"].fillna("UNKNOWN").astype(str)

    bump_count = labels.str.contains("Bump", case=False).sum()
    pothole_count = labels.str.contains("Pothole", case=False).sum()

    known_count = bump_count + pothole_count

    if known_count > 0:
        dominant_count = max(bump_count, pothole_count)
        consistency = dominant_count / known_count
    else:
        consistency = 0.0


    # -----------------------------------------------------
    # 3. SPATIAL COMPACTNESS
    # -----------------------------------------------------

    distances = []

    for _, row in group.iterrows():

        distance = spatial_distance_meters(
            center_lat,
            center_lon,
            row["latitude"],
            row["longitude"],
        )

        distances.append(distance)

    median_distance = float(np.median(distances))
    max_distance = float(np.max(distances))

    # Within ~30 m = strong spatial agreement.
    spatial_score = 1.0 - min(median_distance / 30.0, 1.0)


    # -----------------------------------------------------
    # 4. MOTION INTENSITY
    # -----------------------------------------------------

    peak_motion = pd.to_numeric(
        group["peak_motion"],
        errors="coerce"
    ).fillna(0)

    max_accel = pd.to_numeric(
        group["max_accel"],
        errors="coerce"
    ).fillna(0)

    max_gyro = pd.to_numeric(
        group["max_gyro"],
        errors="coerce"
    ).fillna(0)

    # Use median so one extreme event doesn't dominate.
    median_peak_motion = float(peak_motion.median())
    median_max_accel = float(max_accel.median())
    median_max_gyro = float(max_gyro.median())

    # Prototype normalization ranges.
    motion_component = normalize(
        median_peak_motion,
        1.0,
        5.0
    )

    accel_component = normalize(
        median_max_accel,
        2.0,
        10.0
    )

    gyro_component = normalize(
        median_max_gyro,
        0.2,
        2.0
    )

    intensity_score = (
        motion_component * 0.5
        + accel_component * 0.3
        + gyro_component * 0.2
    )


    # -----------------------------------------------------
    # FINAL EVIDENCE SCORE
    # -----------------------------------------------------

    evidence_score = (
        recording_score * WEIGHT_RECORDINGS
        + consistency * WEIGHT_CONSISTENCY
        + spatial_score * WEIGHT_SPATIAL
        + intensity_score * WEIGHT_INTENSITY
    )


    # -----------------------------------------------------
    # EVIDENCE CATEGORY
    # -----------------------------------------------------

    if unique_recordings >= 3 and evidence_score >= 70:
        evidence_level = "STRONG"

    elif unique_recordings >= 2 and evidence_score >= 50:
        evidence_level = "MODERATE"

    elif unique_recordings >= 2:
        evidence_level = "WEAK_MULTI_RECORDING"

    else:
        evidence_level = "SINGLE_RECORDING"


    # -----------------------------------------------------
    # LABEL INTERPRETATION
    # -----------------------------------------------------

    if bump_count > pothole_count and bump_count > 0:
        dominant_label = "BUMP"

    elif pothole_count > bump_count and pothole_count > 0:
        dominant_label = "POTHOLE"

    elif bump_count > 0 and pothole_count > 0:
        dominant_label = "MIXED"

    else:
        dominant_label = "UNKNOWN"


    results.append({
        "cluster_id": int(cluster_id),
        "latitude": center_lat,
        "longitude": center_lon,

        "event_count": event_count,
        "unique_recordings": unique_recordings,

        "bump_evidence": int(bump_count),
        "pothole_evidence": int(pothole_count),
        "known_events": int(known_count),

        "dominant_label": dominant_label,
        "label_consistency": round(consistency, 3),

        "median_distance_m": round(median_distance, 2),
        "max_distance_m": round(max_distance, 2),

        "median_peak_motion": round(median_peak_motion, 3),
        "median_max_accel": round(median_max_accel, 3),
        "median_max_gyro": round(median_max_gyro, 3),

        "recording_score": round(recording_score, 3),
        "spatial_score": round(spatial_score, 3),
        "intensity_score": round(intensity_score, 3),

        "evidence_score": round(evidence_score, 2),
        "evidence_level": evidence_level,
    })


# ---------------------------------------------------------
# SAVE
# ---------------------------------------------------------

result_df = pd.DataFrame(results)

result_df = result_df.sort_values(
    ["evidence_score", "unique_recordings"],
    ascending=False
)

result_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ---------------------------------------------------------
# DISPLAY
# ---------------------------------------------------------

print()
print("=" * 70)
print("ROADPULSE MULTI-RECORDING EVIDENCE SCORE")
print("=" * 70)

print(f"Total clusters: {len(result_df)}")

print()
print("Evidence levels:")
print(result_df["evidence_level"].value_counts())

print()
print("Top evidence clusters:")
print(
    result_df[
        [
            "cluster_id",
            "latitude",
            "longitude",
            "event_count",
            "unique_recordings",
            "bump_evidence",
            "pothole_evidence",
            "dominant_label",
            "label_consistency",
            "median_distance_m",
            "evidence_score",
            "evidence_level",
        ]
    ].head(15).to_string(index=False)
)

print()
print(f"Saved: {OUTPUT_FILE}")