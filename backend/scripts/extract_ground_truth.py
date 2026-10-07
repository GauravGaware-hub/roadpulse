import pandas as pd
import os
import glob

BASE = "Combined CSV with GIS and Weather Data/Road Anomalies"

rows = []
files = 0
skipped = 0

for file_path in glob.glob(BASE + "/*.csv"):

    df = pd.read_csv(file_path)

    if "annotation_text" not in df.columns:
        skipped += 1
        continue

    files += 1

    # Keep only actual annotated road events
    annotated = df[
        df["annotation_text"].isin(["Bump", "Pothole"])
    ].copy()

    if annotated.empty:
        continue

    # Start a new group whenever the annotation changes
    annotated["group"] = (
        annotated["annotation_text"]
        != annotated["annotation_text"].shift()
    ).cumsum()

    for _, group in annotated.groupby("group"):

        rows.append([
            os.path.basename(file_path),
            group["annotation_text"].iloc[0],
            group["seconds_elapsed"].min(),
            group["seconds_elapsed"].max()
        ])


ground_truth = pd.DataFrame(
    rows,
    columns=[
        "source_file",
        "label",
        "start",
        "end"
    ]
)

print("ANNOTATED EVENTS:", len(ground_truth))
print(
    "RECORDINGS WITH ANNOTATIONS:",
    ground_truth["source_file"].nunique()
)

print("\nLABELS:")
print(
    ground_truth["label"]
    .value_counts()
    .to_string()
)

print("\nFIRST 20:")
print(
    ground_truth
    .head(20)
    .to_string(index=False)
)

# Save for the next evaluation step
output = "backend/processed/roadpulse_ground_truth_events.csv"

ground_truth.to_csv(output, index=False)

print("\nSAVED:")
print(output)