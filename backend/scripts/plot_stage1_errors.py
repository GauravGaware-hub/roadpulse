import os

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import GroupShuffleSplit


# ============================================================
# SETTINGS
# ============================================================

TARGET_FILE = "95.csv"


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
# RECREATE EXACT SAME TEST SPLIT
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

probabilities = model.predict_proba(
    X_test
)

anomaly_index = list(
    model.classes_
).index("ANOMALY")

test_df["anomaly_probability"] = (
    probabilities[:, anomaly_index]
)


# ============================================================
# GET FALSE POSITIVES FOR TARGET FILE
# ============================================================

false_positives = test_df[
    (test_df["source_file"] == TARGET_FILE) &
    (test_df["stage1_label"] == "NORMAL") &
    (test_df["prediction"] == "ANOMALY")
].copy()


print("=" * 70)
print("ROADPULSE STAGE 1 SIGNAL INSPECTION")
print("=" * 70)

print(
    f"\nTarget recording: {TARGET_FILE}"
)

print(
    f"False-positive windows: "
    f"{len(false_positives)}"
)


# ============================================================
# LOAD RAW RECORDING
# ============================================================

raw_path = os.path.join(
    RAW_DATA_DIR,
    TARGET_FILE
)

raw = pd.read_csv(
    raw_path
)

raw["seconds_elapsed"] = pd.to_numeric(
    raw["seconds_elapsed"],
    errors="coerce"
)


# ============================================================
# CALCULATE SIGNALS
# ============================================================

raw["accel_mag"] = np.sqrt(
    raw["accelerometer_x"] ** 2 +
    raw["accelerometer_y"] ** 2 +
    raw["accelerometer_z"] ** 2
)

raw["gyro_mag"] = np.sqrt(
    raw["gyroscope_x"] ** 2 +
    raw["gyroscope_y"] ** 2 +
    raw["gyroscope_z"] ** 2
)

raw["jerk"] = (
    raw["accel_mag"]
    .diff()
    .abs()
)


# ============================================================
# GET ANNOTATION SEGMENTS
# ============================================================

raw["annotation_text"] = (
    raw["annotation_text"]
    .fillna("")
    .astype(str)
    .str.strip()
)

annotation_mask = raw[
    "annotation_text"
].isin(
    ["Bump", "Pothole"]
)

annotation_segments = []

for label in ["Bump", "Pothole"]:

    label_rows = raw[
        raw["annotation_text"] == label
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

        if current - previous > 0.05:

            annotation_segments.append(
                (
                    float(start),
                    float(previous),
                    label
                )
            )

            start = current

        previous = current

    annotation_segments.append(
        (
            float(start),
            float(previous),
            label
        )
    )


# ============================================================
# PRINT ANNOTATION SEGMENTS
# ============================================================

print("\nAnnotated events:")

for start, end, label in annotation_segments:

    print(
        f"{label:8s} "
        f"{start:8.2f}s - "
        f"{end:8.2f}s"
    )


# ============================================================
# PRINT FALSE POSITIVE WINDOWS
# ============================================================

print("\nFalse-positive windows:")

print(
    false_positives[
        [
            "window_start",
            "window_end",
            "anomaly_probability"
        ]
    ]
    .sort_values("window_start")
    .round(3)
    .to_string(index=False)
)


# ============================================================
# PLOT 1 — ACCELERATION MAGNITUDE
# ============================================================

plt.figure(
    figsize=(16, 6)
)

plt.plot(
    raw["seconds_elapsed"],
    raw["accel_mag"],
    linewidth=0.8
)

for start, end, label in annotation_segments:

    plt.axvspan(
        start,
        end,
        alpha=0.25
    )

for _, row in false_positives.iterrows():

    plt.axvspan(
        row["window_start"],
        row["window_end"],
        alpha=0.12
    )

plt.xlabel(
    "Time (seconds)"
)

plt.ylabel(
    "Acceleration Magnitude"
)

plt.title(
    "95.csv — Acceleration Magnitude\n"
    "Shaded regions: annotated events + Stage 1 false positives"
)

plt.grid(
    alpha=0.2
)

plt.tight_layout()


output1 = os.path.join(
    BASE_DIR,
    "processed",
    "95_acceleration_errors.png"
)

plt.savefig(
    output1,
    dpi=150
)

plt.show()

plt.close()


# ============================================================
# PLOT 2 — JERK
# ============================================================

plt.figure(
    figsize=(16, 6)
)

plt.plot(
    raw["seconds_elapsed"],
    raw["jerk"],
    linewidth=0.8
)

for start, end, label in annotation_segments:

    plt.axvspan(
        start,
        end,
        alpha=0.25
    )

for _, row in false_positives.iterrows():

    plt.axvspan(
        row["window_start"],
        row["window_end"],
        alpha=0.12
    )

plt.xlabel(
    "Time (seconds)"
)

plt.ylabel(
    "Absolute Jerk"
)

plt.title(
    "95.csv — Jerk\n"
    "Shaded regions: annotated events + Stage 1 false positives"
)

plt.grid(
    alpha=0.2
)

plt.tight_layout()


output2 = os.path.join(
    BASE_DIR,
    "processed",
    "95_jerk_errors.png"
)

plt.savefig(
    output2,
    dpi=150
)

plt.show()

plt.close()


print("\nPlots saved:")

print(output1)

print(output2)

print("\nInspection complete.")