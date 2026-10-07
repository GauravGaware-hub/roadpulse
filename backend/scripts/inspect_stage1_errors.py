import os

import joblib
import pandas as pd

from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import confusion_matrix


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATASET_PATH = os.path.join(
    BASE_DIR,
    "processed",
    "roadpulse_stage1_features.csv"
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "model",
    "roadpulse_stage1_rf.joblib"
)


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(DATASET_PATH)

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

y_test = y.iloc[test_indices]


# ============================================================
# LOAD MODEL
# ============================================================

model = joblib.load(
    MODEL_PATH
)


# ============================================================
# PREDICTIONS
# ============================================================

test_df["prediction"] = model.predict(
    X_test
)

probabilities = model.predict_proba(
    X_test
)

class_names = list(
    model.classes_
)

anomaly_index = class_names.index(
    "ANOMALY"
)

test_df["anomaly_probability"] = (
    probabilities[:, anomaly_index]
)


# ============================================================
# FALSE POSITIVES
# ============================================================

false_positives = test_df[
    (test_df["stage1_label"] == "NORMAL") &
    (test_df["prediction"] == "ANOMALY")
].copy()


print("=" * 70)
print("ROADPULSE STAGE 1 ERROR INSPECTION")
print("=" * 70)

print(
    f"\nTotal test windows: {len(test_df)}"
)

print(
    f"False positives: {len(false_positives)}"
)


# ============================================================
# FALSE POSITIVES BY RECORDING
# ============================================================

print("\n" + "=" * 70)
print("FALSE POSITIVES BY RECORDING")
print("=" * 70)

fp_by_file = (
    false_positives
    .groupby("source_file")
    .agg(
        false_positive_windows=("prediction", "size"),
        avg_anomaly_probability=(
            "anomaly_probability",
            "mean"
        ),
        max_anomaly_probability=(
            "anomaly_probability",
            "max"
        )
    )
    .sort_values(
        "false_positive_windows",
        ascending=False
    )
)

print(
    fp_by_file.head(30)
    .round(4)
    .to_string()
)


# ============================================================
# FALSE POSITIVES BY SOURCE TYPE
# ============================================================

def source_type(filename):

    if filename in [
        "37 - Normal Road.csv",
        "49 - Normal Road.csv",
        "75 - Normal Road.csv",
        "87 - Normal Road.csv",
        "9 - Normal Road.csv"
    ]:
        return "ORIGINAL_NORMAL"

    return "ANOMALY_RECORDING_SAFE_REGION"


false_positives["source_type"] = (
    false_positives["source_file"]
    .apply(source_type)
)


print("\n" + "=" * 70)
print("FALSE POSITIVES BY SOURCE TYPE")
print("=" * 70)

print(
    false_positives["source_type"]
    .value_counts()
    .to_string()
)


# ============================================================
# FALSE POSITIVE STATISTICS
# ============================================================

print("\n" + "=" * 70)
print("FALSE POSITIVE FEATURE SUMMARY")
print("=" * 70)

summary_features = [
    "accel_mag_std",
    "accel_mag_max",
    "accel_mag_range",
    "accel_peak_deviation",
    "accel_energy",
    "jerk_std",
    "jerk_max",
    "gyro_mag_std",
    "gyro_mag_max"
]

available_features = [
    feature
    for feature in summary_features
    if feature in false_positives.columns
]

print(
    false_positives[available_features]
    .describe()
    .round(3)
    .to_string()
)


# ============================================================
# SHOW HIGHEST-CONFIDENCE FALSE POSITIVES
# ============================================================

print("\n" + "=" * 70)
print("TOP 30 HIGHEST-CONFIDENCE FALSE POSITIVES")
print("=" * 70)

columns_to_show = [
    "source_file",
    "window_start",
    "window_end",
    "anomaly_probability"
]

print(
    false_positives
    .sort_values(
        "anomaly_probability",
        ascending=False
    )[columns_to_show]
    .head(30)
    .round(4)
    .to_string(index=False)
)


# ============================================================
# SAVE FALSE POSITIVES
# ============================================================

OUTPUT_PATH = os.path.join(
    BASE_DIR,
    "processed",
    "stage1_false_positives.csv"
)

false_positives.to_csv(
    OUTPUT_PATH,
    index=False
)

print(
    f"\nSaved false positives to:"
)

print(
    OUTPUT_PATH
)

print("\nInspection complete.")