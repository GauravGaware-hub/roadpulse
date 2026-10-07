import os
import numpy as np
import pandas as pd

# ==================================================
# CONFIG
# ==================================================

INPUT_FILE = r"C:\Users\Gaurav\Desktop\Projects\Avishkar2026\30341143\backend\processed\roadpulse_pune_recording.csv"

OUTPUT_FILE = r"C:\Users\Gaurav\Desktop\Projects\Avishkar2026\30341143\backend\processed\roadpulse_pune_events.csv"

WINDOW_SECONDS = 1.0
STEP_SECONDS = 0.5

MAX_GAP_SECONDS = 1.0

# ==================================================
# LOAD DATA
# ==================================================

print("Loading Pune recording...")

d = pd.read_csv(INPUT_FILE)

d = d.sort_values("seconds_elapsed").reset_index(drop=True)

# ==================================================
# SPEED BANDS
# ==================================================

def speed_band(speed):
    if speed < 1:
        return "STOPPED"
    elif speed < 3:
        return "VERY_SLOW"
    elif speed < 6:
        return "SLOW"
    elif speed < 10:
        return "MODERATE"
    else:
        return "MOVING"


# ==================================================
# CREATE 1-SECOND WINDOWS
# ==================================================

print("Creating windows...")

start = d["seconds_elapsed"].min()
end = d["seconds_elapsed"].max()

windows = []

current = start

while current + WINDOW_SECONDS <= end:

    window_end = current + WINDOW_SECONDS

    w = d[
        (d["seconds_elapsed"] >= current)
        & (d["seconds_elapsed"] < window_end)
    ]

    if len(w) >= 50:

        speed = w["speed"].median()

        windows.append(
            {
                "start": current,
                "end": window_end,
                "accel_mean": w["accel_mag"].mean(),
                "accel_std": w["accel_mag"].std(),
                "accel_max": w["accel_mag"].max(),
                "gyro_std": w["gyro_mag"].std(),
                "gyro_max": w["gyro_mag"].max(),
                "jerk_std": w["jerk"].std(),
                "speed": speed,
                "latitude": w["latitude"].median(),
                "longitude": w["longitude"].median(),
            }
        )

    current += STEP_SECONDS

events = pd.DataFrame(windows)

print("Total windows:", len(events))

# ==================================================
# SPEED BANDS
# ==================================================

events["speed_band"] = events["speed"].apply(speed_band)

# ==================================================
# ROBUST SPEED-ADAPTIVE BASELINES
# ==================================================

print("Calculating speed-adaptive baselines...")

baseline = (
    events
    .groupby("speed_band")
    .agg(
        accel_std_median=("accel_std", "median"),
        accel_std_mad=("accel_std", lambda x:
                       np.median(np.abs(x - np.median(x)))),
        gyro_std_median=("gyro_std", "median"),
        gyro_std_mad=("gyro_std", lambda x:
                      np.median(np.abs(x - np.median(x))))
    )
)

# Avoid zero MAD
baseline["accel_std_mad"] = baseline["accel_std_mad"].clip(lower=0.01)
baseline["gyro_std_mad"] = baseline["gyro_std_mad"].clip(lower=0.01)

# ==================================================
# JOIN BASELINES
# ==================================================

events = events.join(
    baseline,
    on="speed_band"
)

# ==================================================
# ROBUST Z-SCORES
# ==================================================

events["accel_score"] = (
    events["accel_std"]
    - events["accel_std_median"]
) / (
    1.4826 * events["accel_std_mad"]
)

events["gyro_score"] = (
    events["gyro_std"]
    - events["gyro_std_median"]
) / (
    1.4826 * events["gyro_std_mad"]
)

# ==================================================
# CANDIDATE DETECTION
# ==================================================

# ==================================================
# CANDIDATE DETECTION
# ==================================================

valid_features = events[
    [
        "accel_std",
        "accel_max",
        "gyro_std",
        "gyro_max",
        "accel_score",
        "gyro_score",
        "speed",
    ]
].notna().all(axis=1)

events["candidate"] = (
    valid_features
    & (events["speed"] >= 1.0)
    & (
        (events["accel_score"] >= 3.0)
        |
        (events["gyro_score"] >= 3.0)
    )
)

# Explicitly reject stopped windows
events.loc[
    events["speed"] < 1.0,
    "candidate"
] = False

# Explicitly reject stopped windows
events.loc[
    events["speed"] < 1.0,
    "candidate"
] = False

print(
    "Candidate windows:",
    int(events["candidate"].sum())
)

# ==================================================
# MERGE CANDIDATE WINDOWS
# ==================================================

candidate = events[
    events["candidate"]
].copy()

candidate = candidate.sort_values("start")

merged_events = []

if len(candidate) > 0:

    # Start the first event with explicit peak values
    first = candidate.iloc[0]

    current = {
        "start": float(first["start"]),
        "end": float(first["end"]),
        "peak_accel": float(first["accel_max"]),
        "peak_gyro": float(first["gyro_max"]),
        "peak_accel_score": float(first["accel_score"]),
        "peak_gyro_score": float(first["gyro_score"]),
        "speed": float(first["speed"]),
        "speed_band": first["speed_band"],
        "latitude": float(first["latitude"]),
        "longitude": float(first["longitude"]),
    }

    for i in range(1, len(candidate)):

        row = candidate.iloc[i]

        gap = float(row["start"]) - current["end"]

        if gap <= MAX_GAP_SECONDS:

            # Extend current event
            current["end"] = max(
                current["end"],
                float(row["end"])
            )

            # Update peak values
            current["peak_accel"] = max(
                current["peak_accel"],
                float(row["accel_max"])
            )

            current["peak_gyro"] = max(
                current["peak_gyro"],
                float(row["gyro_max"])
            )

            current["peak_accel_score"] = max(
                current["peak_accel_score"],
                float(row["accel_score"])
            )

            current["peak_gyro_score"] = max(
                current["peak_gyro_score"],
                float(row["gyro_score"])
            )

            # Keep latest location/speed information
            current["speed"] = float(row["speed"])
            current["speed_band"] = row["speed_band"]
            current["latitude"] = float(row["latitude"])
            current["longitude"] = float(row["longitude"])

        else:

            merged_events.append(current)

            current = {
                "start": float(row["start"]),
                "end": float(row["end"]),
                "peak_accel": float(row["accel_max"]),
                "peak_gyro": float(row["gyro_max"]),
                "peak_accel_score": float(row["accel_score"]),
                "peak_gyro_score": float(row["gyro_score"]),
                "speed": float(row["speed"]),
                "speed_band": row["speed_band"],
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
            }

    # Add final event
    merged_events.append(current)

# ==================================================
# BUILD FINAL EVENT TABLE
# ==================================================

result = pd.DataFrame(merged_events)

if len(result) > 0:

    result["duration"] = (
        result["end"] - result["start"]
    )

    result["speed_band"] = result["speed"].apply(
        speed_band
    )

    result = result[
        [
            "start",
            "end",
            "duration",
            "peak_accel",
            "peak_gyro",
            "peak_accel_score",
            "peak_gyro_score",
            "speed",
            "speed_band",
            "latitude",
            "longitude",
        ]
    ]

# ==================================================
# SAVE
# ==================================================

os.makedirs(
    os.path.dirname(OUTPUT_FILE),
    exist_ok=True
)

result.to_csv(
    OUTPUT_FILE,
    index=False
)

# ==================================================
# OUTPUT
# ==================================================

print()
print("==========================================")
print("PUNE EVENT DETECTOR")
print("==========================================")

print("Windows:", len(events))
print(
    "Candidate windows:",
    int(events["candidate"].sum())
)

print(
    "Merged events:",
    len(result)
)

if len(result) > 0:

    print()
    print("EVENT SUMMARY:")

    print(
        result.round(3).to_string(index=False)
    )

print()
print("SPEED BAND BASELINES:")

print(
    baseline.round(4).to_string()
)

print()
print("Saved:", OUTPUT_FILE)