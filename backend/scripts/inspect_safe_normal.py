import os
import pandas as pd


ANOMALY_DIR = (
    r"Combined CSV with GIS and Weather Data"
    r"\Road Anomalies"
)

BUFFER_SECONDS = 3.0

total_rows = 0
safe_rows = 0
annotated_rows = 0
files_with_safe_data = 0


for filename in sorted(os.listdir(ANOMALY_DIR)):

    if not filename.endswith(".csv"):
        continue

    if filename == "99.csv":
        continue

    path = os.path.join(ANOMALY_DIR, filename)

    df = pd.read_csv(path)

    if "annotation_text" not in df.columns:
        continue

    df["annotation_text"] = (
        df["annotation_text"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df = df.sort_values("seconds_elapsed").reset_index(drop=True)

    event_mask = df["annotation_text"].isin(
        ["Bump", "Pothole"]
    )

    annotated_rows += event_mask.sum()
    total_rows += len(df)

    if not event_mask.any():
        continue

    # --------------------------------------------------------
    # Find time range occupied by annotated events
    # --------------------------------------------------------

    event_times = df.loc[
        event_mask,
        "seconds_elapsed"
    ]

    event_start = event_times.min()
    event_end = event_times.max()

    # --------------------------------------------------------
    # Safe region:
    # at least BUFFER_SECONDS away from the annotated region
    # --------------------------------------------------------

    safe_mask = (
        (df["seconds_elapsed"] < event_start - BUFFER_SECONDS)
        |
        (df["seconds_elapsed"] > event_end + BUFFER_SECONDS)
    )

    safe_count = safe_mask.sum()

    if safe_count > 0:
        files_with_safe_data += 1
        safe_rows += safe_count


print("=" * 60)
print("ROADPULSE SAFE NORMAL DATA INSPECTION")
print("=" * 60)

print(f"\nFiles inspected: {len(os.listdir(ANOMALY_DIR))}")

print(f"Total rows: {total_rows:,}")

print(f"Annotated rows: {annotated_rows:,}")

print(
    f"Originally unlabeled rows: "
    f"{total_rows - annotated_rows:,}"
)

print(
    f"Safe rows after {BUFFER_SECONDS}s buffer: "
    f"{safe_rows:,}"
)

print(
    f"Files containing safe regions: "
    f"{files_with_safe_data}"
)

if total_rows:
    print(
        f"\nSafe-row percentage: "
        f"{safe_rows / total_rows * 100:.2f}%"
    )
