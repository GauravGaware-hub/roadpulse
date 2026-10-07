import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    BASE_DIR
    / "backend"
    / "processed"
    / "roadpulse_cluster_evidence_v2.csv"
)


df = pd.read_csv(INPUT_FILE)


multi = df[
    df["unique_recordings"] >= 2
].copy()


multi = multi.sort_values(
    [
        "unique_recordings",
        "evidence_score"
    ],
    ascending=False
)


print()
print("=" * 90)
print("ROADPULSE DUPLICATE-AWARE MULTI-RECORDING CLUSTERS")
print("=" * 90)

print(
    f"Multi-recording clusters: {len(multi)}"
)


if len(multi) == 0:

    print()
    print("No genuine multi-recording clusters found.")

else:

    print()

    print(
        multi[
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
                "max_distance_m",
                "median_peak_motion",
                "median_max_accel",
                "median_max_gyro",
                "evidence_score",
                "evidence_level",
            ]
        ].to_string(index=False)
    )


print()
print("=" * 90)
print("INTERPRETATION")
print("=" * 90)

print(
    """
Only clusters with at least two UNIQUE recording groups are
considered genuine multi-recording evidence.

Duplicate recordings are already collapsed.

A multi-recording cluster is still NOT automatically proof of
an actual road defect. It is evidence that similar motion
episodes were observed at approximately the same location
in different recording groups.

The next step is to inspect whether those observations are
consistent enough to support road-health evidence.
"""
)