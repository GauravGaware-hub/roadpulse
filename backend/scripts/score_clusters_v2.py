import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

CLUSTERED_FILE = (
    BASE_DIR
    / "backend"
    / "processed"
    / "roadpulse_events_clustered.csv"
)

DATA_DIR = (
    BASE_DIR
    / "Combined CSV with GIS and Weather Data"
    / "Road Anomalies"
)

OUTPUT_FILE = (
    BASE_DIR
    / "backend"
    / "processed"
    / "roadpulse_cluster_evidence_v2.csv"
)


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

SENSOR_COLUMNS = [
    "seconds_elapsed",

    "accelerometer_x",
    "accelerometer_y",
    "accelerometer_z",

    "gyroscope_x",
    "gyroscope_y",
    "gyroscope_z",

    "location_latitude",
    "location_longitude",
]


# ---------------------------------------------------------
# DUPLICATE FINGERPRINT
# ---------------------------------------------------------

def recording_fingerprint(df):
    data = df[SENSOR_COLUMNS].copy()

    raw = data.to_csv(
        index=False,
        float_format="%.10f"
    ).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------
# BUILD RECORDING GROUPS
# ---------------------------------------------------------

print()
print("=" * 80)
print("BUILDING RECORDING INDEPENDENCE GROUPS")
print("=" * 80)

fingerprints = {}

csv_files = sorted(DATA_DIR.glob("*.csv"))

for path in csv_files:

    if path.name == "99.csv":
        continue

    try:

        df = pd.read_csv(path)

        missing = [
            c for c in SENSOR_COLUMNS
            if c not in df.columns
        ]

        if missing:
            continue

        fingerprint = recording_fingerprint(df)

        fingerprints.setdefault(
            fingerprint,
            []
        ).append(path.name)

    except Exception:
        continue


# Map every filename to a recording group.
#
# Unique recording:
#   REC_0001
#
# Duplicate group:
#   DUP_0001

recording_group_map = {}

group_number = 0

for fingerprint, files in fingerprints.items():

    group_number += 1

    if len(files) == 1:

        group_id = f"REC_{group_number:04d}"

    else:

        group_id = f"DUP_{group_number:04d}"

    for filename in files:
        recording_group_map[filename] = group_id


print(
    f"Unique recording groups: "
    f"{len(fingerprints)}"
)

print()
print("Duplicate groups:")

for fingerprint, files in fingerprints.items():

    if len(files) > 1:

        group_id = recording_group_map[files[0]]

        print(
            f"  {group_id}: "
            + ", ".join(files)
        )


# ---------------------------------------------------------
# LOAD CLUSTERS
# ---------------------------------------------------------

df = pd.read_csv(CLUSTERED_FILE)

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

missing = [
    c for c in required_columns
    if c not in df.columns
]

if missing:
    raise ValueError(
        f"Missing columns: {missing}"
    )


df["recording_group"] = df["source_file"].map(
    recording_group_map
)


if df["recording_group"].isna().any():

    missing_files = sorted(
        df.loc[
            df["recording_group"].isna(),
            "source_file"
        ].unique()
    )

    raise ValueError(
        "Could not identify recording groups for: "
        + ", ".join(missing_files)
    )


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def spatial_distance_meters(
    lat1,
    lon1,
    lat2,
    lon2
):

    lat_scale = 111_320

    lon_scale = (
        111_320
        * np.cos(np.radians(lat1))
    )

    dx = (lon1 - lon2) * lon_scale
    dy = (lat1 - lat2) * lat_scale

    return np.sqrt(
        dx * dx
        + dy * dy
    )


def normalize(value, low, high):

    if high == low:
        return 0.5

    value = (
        (value - low)
        / (high - low)
    )

    return float(
        np.clip(value, 0, 1)
    )


# ---------------------------------------------------------
# SCORE CLUSTERS
# ---------------------------------------------------------

results = []


for cluster_id, group in df.groupby("cluster_id"):

    if pd.isna(cluster_id):
        continue


    # -----------------------------------------------------
    # UNIQUE RECORDING GROUPS
    # -----------------------------------------------------

    recording_groups = sorted(
        group["recording_group"]
        .dropna()
        .unique()
    )

    unique_recordings = len(
        recording_groups
    )

    original_recordings = (
        group["source_file"]
        .nunique()
    )


    # -----------------------------------------------------
    # BASIC COUNTS
    # -----------------------------------------------------

    event_count = len(group)

    center_lat = group["latitude"].median()
    center_lon = group["longitude"].median()


    # -----------------------------------------------------
    # LABEL EVIDENCE
    # -----------------------------------------------------

    labels = (
        group["label"]
        .fillna("UNKNOWN")
        .astype(str)
    )

    bump_count = labels.str.contains(
        "Bump",
        case=False
    ).sum()

    pothole_count = labels.str.contains(
        "Pothole",
        case=False
    ).sum()

    known_count = (
        bump_count
        + pothole_count
    )


    if known_count > 0:

        dominant_count = max(
            bump_count,
            pothole_count
        )

        consistency = (
            dominant_count
            / known_count
        )

    else:

        consistency = 0.0


    # -----------------------------------------------------
    # LABEL BY RECORDING GROUP
    # -----------------------------------------------------
    #
    # This prevents one duplicated recording from
    # contributing several times to label evidence.

    group_labels = []

    for recording_group, recording_data in group.groupby(
        "recording_group"
    ):

        recording_labels = (
            recording_data["label"]
            .fillna("UNKNOWN")
            .astype(str)
        )

        has_bump = recording_labels.str.contains(
            "Bump",
            case=False
        ).any()

        has_pothole = recording_labels.str.contains(
            "Pothole",
            case=False
        ).any()

        if has_bump and has_pothole:
            group_label = "MIXED"

        elif has_bump:
            group_label = "BUMP"

        elif has_pothole:
            group_label = "POTHOLE"

        else:
            group_label = "UNKNOWN"

        group_labels.append(group_label)


    group_labels = pd.Series(
        group_labels
    )

    recording_bump_evidence = (
        (group_labels == "BUMP")
        | (group_labels == "MIXED")
    ).sum()

    recording_pothole_evidence = (
        (group_labels == "POTHOLE")
        | (group_labels == "MIXED")
    ).sum()


    # -----------------------------------------------------
    # SPATIAL COMPACTNESS
    # -----------------------------------------------------

    distances = []

    for _, row in group.iterrows():

        distance = spatial_distance_meters(
            center_lat,
            center_lon,
            row["latitude"],
            row["longitude"]
        )

        distances.append(distance)


    median_distance = float(
        np.median(distances)
    )

    max_distance = float(
        np.max(distances)
    )

    spatial_score = (
        1.0
        - min(
            median_distance / 30.0,
            1.0
        )
    )


    # -----------------------------------------------------
    # MOTION INTENSITY
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


    median_peak_motion = float(
        peak_motion.median()
    )

    median_max_accel = float(
        max_accel.median()
    )

    median_max_gyro = float(
        max_gyro.median()
    )


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
    # RECORDING EVIDENCE
    # -----------------------------------------------------

    recording_score = min(
        unique_recordings / 5,
        1.0
    )


    # -----------------------------------------------------
    # FINAL EVIDENCE SCORE
    # -----------------------------------------------------

    evidence_score = (
        recording_score * 40
        + consistency * 25
        + spatial_score * 20
        + intensity_score * 15
    )


    # -----------------------------------------------------
    # EVIDENCE LEVEL
    # -----------------------------------------------------

    if (
        unique_recordings >= 3
        and evidence_score >= 70
    ):

        evidence_level = "STRONG"

    elif (
        unique_recordings >= 2
        and evidence_score >= 50
    ):

        evidence_level = "MODERATE"

    elif unique_recordings >= 2:

        evidence_level = (
            "WEAK_MULTI_RECORDING"
        )

    else:

        evidence_level = "SINGLE_RECORDING"


    # -----------------------------------------------------
    # DOMINANT LABEL
    # -----------------------------------------------------

    if (
        recording_pothole_evidence
        > recording_bump_evidence
    ):

        dominant_label = "POTHOLE"

    elif (
        recording_bump_evidence
        > recording_pothole_evidence
    ):

        dominant_label = "BUMP"

    elif (
        recording_bump_evidence > 0
        and recording_pothole_evidence > 0
    ):

        dominant_label = "MIXED"

    else:

        dominant_label = "UNKNOWN"


    results.append({

        "cluster_id": int(cluster_id),

        "latitude": center_lat,
        "longitude": center_lon,

        "event_count": event_count,

        # Original file count
        "original_recordings": original_recordings,

        # Duplicate-aware count
        "unique_recordings": unique_recordings,

        "recording_groups": (
            "|".join(recording_groups)
        ),

        "bump_evidence": int(
            recording_bump_evidence
        ),

        "pothole_evidence": int(
            recording_pothole_evidence
        ),

        "dominant_label": dominant_label,

        "label_consistency": round(
            consistency,
            3
        ),

        "median_distance_m": round(
            median_distance,
            2
        ),

        "max_distance_m": round(
            max_distance,
            2
        ),

        "median_peak_motion": round(
            median_peak_motion,
            3
        ),

        "median_max_accel": round(
            median_max_accel,
            3
        ),

        "median_max_gyro": round(
            median_max_gyro,
            3
        ),

        "recording_score": round(
            recording_score,
            3
        ),

        "spatial_score": round(
            spatial_score,
            3
        ),

        "intensity_score": round(
            intensity_score,
            3
        ),

        "evidence_score": round(
            evidence_score,
            2
        ),

        "evidence_level": evidence_level,
    })


# ---------------------------------------------------------
# SAVE
# ---------------------------------------------------------

result_df = pd.DataFrame(
    results
)

result_df = result_df.sort_values(
    [
        "evidence_score",
        "unique_recordings"
    ],
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
print("=" * 80)
print("DUPLICATE-AWARE ROADPULSE EVIDENCE SCORE")
print("=" * 80)

print(
    f"Total spatial clusters: "
    f"{len(result_df)}"
)

print()
print("Evidence levels:")

print(
    result_df[
        "evidence_level"
    ].value_counts()
)


print()
print("Top clusters:")

print(
    result_df[
        [
            "cluster_id",
            "latitude",
            "longitude",
            "event_count",
            "original_recordings",
            "unique_recordings",
            "recording_groups",
            "bump_evidence",
            "pothole_evidence",
            "dominant_label",
            "label_consistency",
            "median_distance_m",
            "evidence_score",
            "evidence_level",
        ]
    ]
    .head(20)
    .to_string(index=False)
)


print()
print(
    f"Saved: {OUTPUT_FILE}"
)