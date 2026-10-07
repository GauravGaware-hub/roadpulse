import os

import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import GroupShuffleSplit


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

FEATURES_PATH = os.path.join(
    BASE_DIR,
    "processed",
    "roadpulse_stage1_features.csv"
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "model",
    "roadpulse_stage1_rf.joblib"
)

RAW_DATA_DIR = os.path.join(
    os.path.dirname(BASE_DIR),
    "Combined CSV with GIS and Weather Data",
    "Road Anomalies"
)


# ============================================================
# LOAD FEATURE DATA
# ============================================================

df = pd.read_csv(FEATURES_PATH)

df["stage1_label"] = df["label"].replace({
    "BUMP": "ANOMALY",
    "POTHOLE": "ANOMALY",
    "NORMAL": "NORMAL"
})


NON_FEATURE_COLUMNS = [
    "label",
    "stage1_label",
    "source_file",
    "window_start",
    "window_end"
]

FEATURE_COLUMNS = [
    column
    for column in df.columns
    if column not in NON_FEATURE_COLUMNS
]

X = df[FEATURE_COLUMNS]

y = df["stage1_label"]

groups = df["source_file"]


# ============================================================
# RECREATE EXACT TEST SPLIT
# ============================================================

splitter = GroupShuffleSplit(
    n_splits=1,
    test_size=0.20,
    random_state=42
)

train_indices, test_indices = next(
    splitter.split(
        X,
        y,
        groups=groups
    )
)

test_df = df.iloc[test_indices].copy()

X_test = X.iloc[test_indices]


# ============================================================
# LOAD MODEL
# ============================================================

model = joblib.load(
    MODEL_PATH
)

test_df["prediction"] = model.predict(
    X_test
)


# ============================================================
# GET FALSE POSITIVES
# ============================================================

false_positives = test_df[
    (test_df["stage1_label"] == "NORMAL") &
    (test_df["prediction"] == "ANOMALY")
].copy()


print("=" * 70)
print("FALSE POSITIVE DISTANCE TO NEAREST ANNOTATED EVENT")
print("=" * 70)

print(
    f"\nFalse positives: {len(false_positives)}"
)


# ============================================================
# FIND ANNOTATED EVENT RANGES
# ============================================================

event_cache = {}


def get_event_ranges(source_file):

    if source_file in event_cache:
        return event_cache[source_file]

    path = os.path.join(
        RAW_DATA_DIR,
        source_file
    )

    if not os.path.exists(path):
        event_cache[source_file] = []

        return []

    raw = pd.read_csv(path)

    if "annotation_text" not in raw.columns:
        event_cache[source_file] = []

        return []

    raw["annotation_text"] = (
        raw["annotation_text"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    event_rows = raw[
        raw["annotation_text"].isin(
            ["Bump", "Pothole"]
        )
    ].copy()

    if event_rows.empty:
        event_cache[source_file] = []

        return []

    event_ranges = []

    for label in ["Bump", "Pothole"]:

        label_rows = event_rows[
            event_rows["annotation_text"] == label
        ]

        if label_rows.empty:
            continue

        times = (
            label_rows["seconds_elapsed"]
            .sort_values()
            .to_numpy()
        )

        start = times[0]
        previous = times[0]

        for current in times[1:]:

            # A gap greater than 0.05 seconds
            # starts a new annotated event group.
            if current - previous > 0.05:

                event_ranges.append(
                    {
                        "label": label,
                        "start": float(start),
                        "end": float(previous)
                    }
                )

                start = current

            previous = current

        event_ranges.append(
            {
                "label": label,
                "start": float(start),
                "end": float(previous)
            }
        )

    event_cache[source_file] = event_ranges

    return event_ranges


# ============================================================
# CALCULATE DISTANCE
# ============================================================

results = []

for _, row in false_positives.iterrows():

    source_file = row["source_file"]

    window_start = float(
        row["window_start"]
    )

    window_end = float(
        row["window_end"]
    )

    window_center = (
        window_start +
        window_end
    ) / 2

    events = get_event_ranges(
        source_file
    )

    if not events:

        results.append(
            {
                "source_file": source_file,
                "window_start": window_start,
                "window_end": window_end,
                "nearest_event_distance": np.nan,
                "nearest_event_label": "NO_EVENT_DATA",
                "event_start": np.nan,
                "event_end": np.nan
            }
        )

        continue

    distances = []

    for event in events:

        event_start = event["start"]
        event_end = event["end"]

        if (
            window_center >= event_start
            and
            window_center <= event_end
        ):
            distance = 0.0

        elif window_center < event_start:

            distance = (
                event_start -
                window_center
            )

        else:

            distance = (
                window_center -
                event_end
            )

        distances.append(
            (
                distance,
                event
            )
        )

    nearest_distance, nearest_event = min(
        distances,
        key=lambda item: item[0]
    )

    results.append(
        {
            "source_file": source_file,
            "window_start": window_start,
            "window_end": window_end,
            "nearest_event_distance": nearest_distance,
            "nearest_event_label": nearest_event["label"],
            "event_start": nearest_event["start"],
            "event_end": nearest_event["end"]
        }
    )


result_df = pd.DataFrame(
    results
)


# ============================================================
# SUMMARY
# ============================================================

print("\nDistance summary (seconds):")

print(
    result_df[
        "nearest_event_distance"
    ]
    .describe(
        percentiles=[
            0.10,
            0.25,
            0.50,
            0.75,
            0.90,
            0.95
        ]
    )
    .round(2)
    .to_string()
)


# ============================================================
# DISTANCE BUCKETS
# ============================================================

bins = [
    -0.01,
    3,
    5,
    10,
    20,
    30,
    60,
    float("inf")
]

labels = [
    "0-3 sec",
    "3-5 sec",
    "5-10 sec",
    "10-20 sec",
    "20-30 sec",
    "30-60 sec",
    "60+ sec"
]

result_df["distance_bucket"] = pd.cut(
    result_df["nearest_event_distance"],
    bins=bins,
    labels=labels
)


print("\nFalse positives by distance:")

print(
    result_df[
        "distance_bucket"
    ]
    .value_counts(
        sort=False
    )
    .to_string()
)


# ============================================================
# BY RECORDING
# ============================================================

print("\n" + "=" * 70)
print("FALSE POSITIVE DISTANCE BY RECORDING")
print("=" * 70)

by_file = (
    result_df
    .groupby("source_file")
    .agg(
        false_positives=(
            "source_file",
            "size"
        ),
        median_distance=(
            "nearest_event_distance",
            "median"
        ),
        minimum_distance=(
            "nearest_event_distance",
            "min"
        ),
        maximum_distance=(
            "nearest_event_distance",
            "max"
        )
    )
    .sort_values(
        "false_positives",
        ascending=False
    )
)

print(
    by_file
    .round(2)
    .to_string()
)


# ============================================================
# CLOSEST FALSE POSITIVES
# ============================================================

print("\n" + "=" * 70)
print("CLOSEST FALSE POSITIVES")
print("=" * 70)

print(
    result_df
    .sort_values(
        "nearest_event_distance"
    )
    .head(30)
    .round(2)
    .to_string(index=False)
)


# ============================================================
# FARTHEST FALSE POSITIVES
# ============================================================

print("\n" + "=" * 70)
print("FARTHEST FALSE POSITIVES")
print("=" * 70)

print(
    result_df
    .sort_values(
        "nearest_event_distance",
        ascending=False
    )
    .head(30)
    .round(2)
    .to_string(index=False)
)


# ============================================================
# SAVE
# ============================================================

OUTPUT_PATH = os.path.join(
    BASE_DIR,
    "processed",
    "stage1_fp_event_distance.csv"
)

result_df.to_csv(
    OUTPUT_PATH,
    index=False
)

print(
    f"\nSaved detailed results to:"
)

print(
    OUTPUT_PATH
)

print("\nInspection complete.")