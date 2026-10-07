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

INPUT = r"backend\processed\roadpulse_features.csv"

MODEL_DIR = r"backend\model"
MODEL_PATH = os.path.join(MODEL_DIR, "roadpulse_rf.joblib")
METADATA_PATH = os.path.join(MODEL_DIR, "metadata.json")
FEATURE_PATH = os.path.join(MODEL_DIR, "feature_schema.json")

RANDOM_STATE = 42

os.makedirs(MODEL_DIR, exist_ok=True)

print("=" * 60)
print("ROADPULSE RANDOM FOREST TRAINING")
print("=" * 60)

# ---------------------------------------------------------
# 1. Load dataset
# ---------------------------------------------------------

df = pd.read_csv(INPUT)

print("\nDataset:")
print("Total windows:", len(df))
print("Features:", len(df.columns))

# Columns that are NOT ML features
NON_FEATURE_COLUMNS = [
    "label",
    "source_file",
    "window_start",
    "window_end"
]

feature_columns = [
    col for col in df.columns
    if col not in NON_FEATURE_COLUMNS
]

X = df[feature_columns]
y = df["label"]
groups = df["source_file"]

print("\nFeature count:", len(feature_columns))

# ---------------------------------------------------------
# 2. Group-based train/test split
# ---------------------------------------------------------

splitter = GroupShuffleSplit(
    n_splits=1,
    test_size=0.20,
    random_state=RANDOM_STATE
)

train_idx, test_idx = next(
    splitter.split(X, y, groups=groups)
)

X_train = X.iloc[train_idx]
X_test = X.iloc[test_idx]

y_train = y.iloc[train_idx]
y_test = y.iloc[test_idx]

train_groups = groups.iloc[train_idx]
test_groups = groups.iloc[test_idx]

print("\nTRAINING SET")
print("Windows:", len(X_train))
print(y_train.value_counts().to_string())

print("\nTEST SET")
print("Windows:", len(X_test))
print(y_test.value_counts().to_string())

print("\nTraining recordings:", train_groups.nunique())
print("Testing recordings:", test_groups.nunique())

# ---------------------------------------------------------
# 3. Check leakage
# ---------------------------------------------------------

overlap = set(train_groups).intersection(set(test_groups))

if overlap:
    raise RuntimeError(
        f"DATA LEAKAGE DETECTED: {overlap}"
    )

print("\nData leakage check: PASS")

# ---------------------------------------------------------
# 4. Train Random Forest
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("TRAINING RANDOM FOREST")
print("=" * 60)

model = RandomForestClassifier(
    n_estimators=250,
    max_depth=20,
    class_weight="balanced",
    random_state=RANDOM_STATE,
    n_jobs=-1
)

model.fit(X_train, y_train)

print("Training complete.")

# ---------------------------------------------------------
# 5. Predictions
# ---------------------------------------------------------

y_pred = model.predict(X_test)

# ---------------------------------------------------------
# 6. Evaluation
# ---------------------------------------------------------

accuracy = accuracy_score(y_test, y_pred)

macro_f1 = f1_score(
    y_test,
    y_pred,
    average="macro"
)

print("\n" + "=" * 60)
print("MODEL EVALUATION")
print("=" * 60)

print(f"\nAccuracy: {accuracy:.4f}")
print(f"Macro F1: {macro_f1:.4f}")

print("\nClassification Report:")
print(
    classification_report(
        y_test,
        y_pred,
        digits=4
    )
)

print("\nConfusion Matrix:")

labels = ["NORMAL", "BUMP", "POTHOLE"]

cm = confusion_matrix(
    y_test,
    y_pred,
    labels=labels
)

print("              " + "  ".join(f"{x:>8}" for x in labels))

for label, row in zip(labels, cm):
    print(
        f"{label:<12}"
        + "  ".join(f"{value:>8}" for value in row)
    )

# ---------------------------------------------------------
# 7. Save model
# ---------------------------------------------------------

joblib.dump(
    model,
    MODEL_PATH
)

print("\nModel saved:")
print(MODEL_PATH)

# ---------------------------------------------------------
# 8. Save feature schema
# ---------------------------------------------------------

with open(FEATURE_PATH, "w") as f:
    json.dump(
        {
            "feature_count": len(feature_columns),
            "features": feature_columns
        },
        f,
        indent=2
    )

print("Feature schema saved:")
print(FEATURE_PATH)

# ---------------------------------------------------------
# 9. Save metadata
# ---------------------------------------------------------

metadata = {
    "model": "RandomForestClassifier",
    "n_estimators": 250,
    "max_depth": 20,
    "class_weight": "balanced",
    "random_state": RANDOM_STATE,
    "dataset_windows": len(df),
    "train_windows": len(X_train),
    "test_windows": len(X_test),
    "train_recordings": int(train_groups.nunique()),
    "test_recordings": int(test_groups.nunique()),
    "feature_count": len(feature_columns),
    "accuracy": float(accuracy),
    "macro_f1": float(macro_f1),
    "classes": labels
}

with open(METADATA_PATH, "w") as f:
    json.dump(
        metadata,
        f,
        indent=2
    )

print("Metadata saved:")
print(METADATA_PATH)

print("\n" + "=" * 60)
print("TRAINING FINISHED")
print("=" * 60)