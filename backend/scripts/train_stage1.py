import os
import json
import joblib

import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score
)


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

MODEL_DIR = os.path.join(
    BASE_DIR,
    "model"
)

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "roadpulse_stage1_rf.joblib"
)

SCHEMA_PATH = os.path.join(
    MODEL_DIR,
    "stage1_feature_schema.json"
)

METADATA_PATH = os.path.join(
    MODEL_DIR,
    "stage1_metadata.json"
)


# ============================================================
# SETTINGS
# ============================================================

RANDOM_STATE = 42

TEST_SIZE = 0.20


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 60)
print("ROADPULSE STAGE 1 RANDOM FOREST TRAINING")
print("=" * 60)

df = pd.read_csv(DATASET_PATH)

print("\nDataset:")
print(f"Total windows: {len(df)}")


# ============================================================
# CONVERT LABELS
# ============================================================

df["stage1_label"] = df["label"].replace({
    "BUMP": "ANOMALY",
    "POTHOLE": "ANOMALY",
    "NORMAL": "NORMAL"
})


print("\nStage 1 class distribution:")

print(
    df["stage1_label"]
    .value_counts()
    .to_string()
)


# ============================================================
# FEATURES
# ============================================================

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


print(
    f"\nFeature count: "
    f"{len(FEATURE_COLUMNS)}"
)


# ============================================================
# GROUP SPLIT
# ============================================================

splitter = GroupShuffleSplit(
    n_splits=1,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE
)

train_indices, test_indices = next(
    splitter.split(
        X,
        y,
        groups=groups
    )
)

X_train = X.iloc[train_indices]
X_test = X.iloc[test_indices]

y_train = y.iloc[train_indices]
y_test = y.iloc[test_indices]

train_groups = groups.iloc[train_indices]
test_groups = groups.iloc[test_indices]


print("\n" + "=" * 60)
print("TRAINING SET")
print("=" * 60)

print(
    f"Windows: {len(X_train)}"
)

print(
    y_train.value_counts()
    .to_string()
)

print(
    f"Training recordings: "
    f"{train_groups.nunique()}"
)


print("\n" + "=" * 60)
print("TEST SET")
print("=" * 60)

print(
    f"Windows: {len(X_test)}"
)

print(
    y_test.value_counts()
    .to_string()
)

print(
    f"Testing recordings: "
    f"{test_groups.nunique()}"
)


# ============================================================
# DATA LEAKAGE CHECK
# ============================================================

overlap = set(
    train_groups.unique()
).intersection(
    set(test_groups.unique())
)

if overlap:

    print(
        "\nData leakage detected!"
    )

    print(
        "Overlapping recordings:",
        sorted(overlap)
    )

    raise RuntimeError(
        "Training and testing recordings overlap."
    )

else:

    print(
        "\nData leakage check: PASS"
    )


# ============================================================
# RANDOM FOREST
# ============================================================

print("\n" + "=" * 60)
print("TRAINING RANDOM FOREST")
print("=" * 60)

model = RandomForestClassifier(

    n_estimators=300,

    max_depth=20,

    min_samples_split=4,

    min_samples_leaf=2,

    class_weight="balanced",

    random_state=RANDOM_STATE,

    n_jobs=-1
)


model.fit(
    X_train,
    y_train
)


print(
    "Training complete."
)


# ============================================================
# EVALUATION
# ============================================================

predictions = model.predict(
    X_test
)


accuracy = accuracy_score(
    y_test,
    predictions
)

macro_f1 = f1_score(
    y_test,
    predictions,
    average="macro"
)


print("\n" + "=" * 60)
print("MODEL EVALUATION")
print("=" * 60)

print(
    f"\nAccuracy: "
    f"{accuracy:.4f}"
)

print(
    f"Macro F1: "
    f"{macro_f1:.4f}"
)


print("\nClassification Report:")

print(
    classification_report(
        y_test,
        predictions,
        digits=4
    )
)


print("\nConfusion Matrix:")

labels = [
    "NORMAL",
    "ANOMALY"
]

cm = confusion_matrix(
    y_test,
    predictions,
    labels=labels
)

cm_df = pd.DataFrame(
    cm,
    index=labels,
    columns=labels
)

print(
    cm_df.to_string()
)


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

importance = pd.Series(
    model.feature_importances_,
    index=FEATURE_COLUMNS
).sort_values(
    ascending=False
)

print("\nTop 15 Features:")

print(
    importance.head(15)
    .round(5)
    .to_string()
)


# ============================================================
# SAVE MODEL
# ============================================================

os.makedirs(
    MODEL_DIR,
    exist_ok=True
)

joblib.dump(
    model,
    MODEL_PATH
)


with open(
    SCHEMA_PATH,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        FEATURE_COLUMNS,
        file,
        indent=2
    )


metadata = {

    "model_type": "RandomForestClassifier",

    "stage": "stage1",

    "task": "NORMAL vs ANOMALY",

    "random_state": RANDOM_STATE,

    "test_size": TEST_SIZE,

    "total_windows": len(df),

    "training_windows": len(X_train),

    "testing_windows": len(X_test),

    "training_recordings": int(
        train_groups.nunique()
    ),

    "testing_recordings": int(
        test_groups.nunique()
    ),

    "feature_count": len(
        FEATURE_COLUMNS
    ),

    "accuracy": float(
        accuracy
    ),

    "macro_f1": float(
        macro_f1
    )
}


with open(
    METADATA_PATH,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        metadata,
        file,
        indent=2
    )


print("\nModel saved:")
print(MODEL_PATH)

print("\nFeature schema saved:")
print(SCHEMA_PATH)

print("\nMetadata saved:")
print(METADATA_PATH)

print("\n" + "=" * 60)
print("STAGE 1 TRAINING FINISHED")
print("=" * 60)