import hashlib
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = (
    BASE_DIR
    / "Combined CSV with GIS and Weather Data"
    / "Road Anomalies"
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
# FINGERPRINT
# ---------------------------------------------------------

def recording_fingerprint(df):
    """
    Create an exact fingerprint from the selected sensor/GPS
    columns.

    Files with identical values in these columns receive the
    same fingerprint.
    """

    data = df[SENSOR_COLUMNS].copy()

    # Convert to a stable CSV representation.
    raw = data.to_csv(
        index=False,
        float_format="%.10f"
    ).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------
# PROCESS RECORDINGS
# ---------------------------------------------------------

print()
print("=" * 80)
print("ROADPULSE DUPLICATE RECORDING CHECK")
print("=" * 80)

fingerprints = {}

csv_files = sorted(DATA_DIR.glob("*.csv"))

processed = 0
skipped = 0


for path in csv_files:

    if path.name == "99.csv":
        skipped += 1
        continue

    try:
        df = pd.read_csv(path)

        missing = [
            c for c in SENSOR_COLUMNS
            if c not in df.columns
        ]

        if missing:
            print(
                f"Skipping {path.name}: "
                f"missing {missing}"
            )
            skipped += 1
            continue

        fingerprint = recording_fingerprint(df)

        fingerprints.setdefault(
            fingerprint,
            []
        ).append(path.name)

        processed += 1

    except Exception as e:

        print(
            f"Error reading {path.name}: {e}"
        )

        skipped += 1


# ---------------------------------------------------------
# FIND DUPLICATES
# ---------------------------------------------------------

duplicate_groups = [
    files
    for files in fingerprints.values()
    if len(files) > 1
]


print()
print(f"Recordings processed: {processed}")
print(f"Recordings skipped: {skipped}")
print(f"Unique fingerprints: {len(fingerprints)}")
print(f"Duplicate groups: {len(duplicate_groups)}")

print()
print("=" * 80)
print("DUPLICATE GROUPS")
print("=" * 80)


if not duplicate_groups:

    print("No exact duplicate groups found.")

else:

    for i, group in enumerate(
        duplicate_groups,
        start=1
    ):

        print(
            f"Group {i}: "
            f"{len(group)} recordings"
        )

        print(
            "  "
            + ", ".join(group)
        )


print()
print("=" * 80)
print("IMPORTANT")
print("=" * 80)

print(
    """
Duplicate recordings must not be counted as independent
vehicle observations.

RoadPulse should count unique recording groups when estimating
multi-recording confirmation.

This prevents repeated copies of the same trip from artificially
increasing confidence.
"""
)