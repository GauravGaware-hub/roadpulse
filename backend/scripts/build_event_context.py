import numpy as np
import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

EVENT_FILE = (
    BASE_DIR
    / "backend"
    / "processed"
    / "roadpulse_events.csv"
)

DATA_DIR = (
    BASE_DIR
    / "Combined CSV with GIS and Weather Data"
    / "Road Anomalies"
)

OUTPUT_FILE = (
    BASE_DIR
    / "backend"
    / "processed"
    / "roadpulse_events_context.csv"
)


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

SPEED_STOPPED = 3
SPEED_VERY_SLOW = 15
SPEED_SLOW = 30
SPEED_MOVING = 50


# ---------------------------------------------------------
# LOAD EVENTS
# ---------------------------------------------------------

events = pd.read_csv(EVENT_FILE)


def motion_state(speed):

    if speed < SPEED_STOPPED:
        return "STOPPED"

    elif speed < SPEED_VERY_SLOW:
        return "VERY_SLOW"

    elif speed < SPEED_SLOW:
        return "SLOW"

    elif speed < SPEED_MOVING:
        return "MOVING"

    else:
        return "FAST"


def haversine_distance_m(
    lat1,
    lon1,
    lat2,
    lon2
):

    R = 6371000

    lat1 = np.radians(lat1)
    lat2 = np.radians(lat2)

    dlat = lat2 - lat1
    dlon = np.radians(lon2 - lon1)

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    return (
        2
        * R
        * np.arcsin(
            np.sqrt(a)
        )
    )


# ---------------------------------------------------------
# CACHE RECORDINGS
# ---------------------------------------------------------

cache = {}


def load_recording(filename):

    if filename not in cache:

        path = DATA_DIR / filename

        cache[filename] = pd.read_csv(
            path
        )

    return cache[filename]


# ---------------------------------------------------------
# PROCESS EVENTS
# ---------------------------------------------------------

results = []


for _, event in events.iterrows():

    filename = event["source_file"]

    df = load_recording(filename)


    start = float(
        event["start"]
    )

    end = float(
        event["end"]
    )


    # -----------------------------------------------------
    # EVENT DATA
    # -----------------------------------------------------

    mask = (
        (df["seconds_elapsed"] >= start)
        & (df["seconds_elapsed"] <= end)
    )

    segment = df.loc[
        mask
    ].copy()


    if len(segment) < 5:

        continue


    # -----------------------------------------------------
    # GPS SPEED
    # -----------------------------------------------------

    lat = pd.to_numeric(
        segment["location_latitude"],
        errors="coerce"
    ).to_numpy()

    lon = pd.to_numeric(
        segment["location_longitude"],
        errors="coerce"
    ).to_numpy()

    time = pd.to_numeric(
        segment["seconds_elapsed"],
        errors="coerce"
    ).to_numpy()


    distances = haversine_distance_m(
        lat[:-1],
        lon[:-1],
        lat[1:],
        lon[1:]
    )

    dt = np.diff(time)

    valid = dt > 0

    distances = distances[valid]
    dt = dt[valid]

    speed_kmh = (
        distances / dt
    ) * 3.6


    if len(speed_kmh) == 0:

        continue


    median_speed = float(
        np.median(speed_kmh)
    )

    mean_speed = float(
        np.mean(speed_kmh)
    )

    min_speed = float(
        np.min(speed_kmh)
    )

    max_speed = float(
        np.max(speed_kmh)
    )

    speed_range = (
        max_speed
        - min_speed
    )


    # -----------------------------------------------------
    # SPEED TREND
    # -----------------------------------------------------

    half = len(speed_kmh) // 2

    if half >= 2:

        first_half = np.mean(
            speed_kmh[:half]
        )

        second_half = np.mean(
            speed_kmh[half:]
        )

        speed_change = (
            second_half
            - first_half
        )

    else:

        speed_change = 0


    # -----------------------------------------------------
    # ACCELERATION
    # -----------------------------------------------------

    ax = pd.to_numeric(
        segment["accelerometer_x"],
        errors="coerce"
    ).to_numpy()

    ay = pd.to_numeric(
        segment["accelerometer_y"],
        errors="coerce"
    ).to_numpy()

    az = pd.to_numeric(
        segment["accelerometer_z"],
        errors="coerce"
    ).to_numpy()


    accel_mag = np.sqrt(
        ax ** 2
        + ay ** 2
        + az ** 2
    )


    accel_std = float(
        np.std(accel_mag)
    )

    accel_max = float(
        np.max(accel_mag)
    )

    accel_range = float(
        np.max(accel_mag)
        - np.min(accel_mag)
    )


    # -----------------------------------------------------
    # GYROSCOPE
    # -----------------------------------------------------

    gx = pd.to_numeric(
        segment["gyroscope_x"],
        errors="coerce"
    ).to_numpy()

    gy = pd.to_numeric(
        segment["gyroscope_y"],
        errors="coerce"
    ).to_numpy()

    gz = pd.to_numeric(
        segment["gyroscope_z"],
        errors="coerce"
    ).to_numpy()


    gyro_mag = np.sqrt(
        gx ** 2
        + gy ** 2
        + gz ** 2
    )


    gyro_std = float(
        np.std(gyro_mag)
    )

    gyro_max = float(
        np.max(gyro_mag)
    )


    # -----------------------------------------------------
    # CONTEXT FLAGS
    # -----------------------------------------------------

    state = motion_state(
        median_speed
    )


    was_stopped = (
        min_speed < SPEED_STOPPED
    )

    strong_deceleration = (
        speed_change < -10
    )

    strong_acceleration = (
        speed_change > 10
    )

    high_motion = (
        accel_std > 0.75
        or gyro_std > 0.08
    )


    # -----------------------------------------------------
    # CONTEXT INTERPRETATION
    # -----------------------------------------------------

    if state == "STOPPED":

        context = "STOPPED"

    elif strong_deceleration:

        context = "DECELERATION"

    elif strong_acceleration:

        context = "ACCELERATION"

    elif high_motion:

        context = "MOVING_MOTION_EVENT"

    else:

        context = "NORMAL_MOTION"


    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    results.append({

        "event_id": int(event.name) + 1,

        "source_file": filename,

        "start": start,

        "end": end,

        "duration": end - start,

        "annotation_label": event["label"],

        "latitude": event["latitude"],

        "longitude": event["longitude"],

        "median_speed_kmh": round(
            median_speed,
            3
        ),

        "mean_speed_kmh": round(
            mean_speed,
            3
        ),

        "min_speed_kmh": round(
            min_speed,
            3
        ),

        "max_speed_kmh": round(
            max_speed,
            3
        ),

        "speed_range_kmh": round(
            speed_range,
            3
        ),

        "speed_change_kmh": round(
            speed_change,
            3
        ),

        "motion_state": state,

        "was_stopped": was_stopped,

        "strong_deceleration": (
            strong_deceleration
        ),

        "strong_acceleration": (
            strong_acceleration
        ),

        "accel_std": round(
            accel_std,
            4
        ),

        "accel_max": round(
            accel_max,
            4
        ),

        "accel_range": round(
            accel_range,
            4
        ),

        "gyro_std": round(
            gyro_std,
            4
        ),

        "gyro_max": round(
            gyro_max,
            4
        ),

        "high_motion": high_motion,

        "context": context,
    })


# ---------------------------------------------------------
# SAVE
# ---------------------------------------------------------

result = pd.DataFrame(
    results
)

result.to_csv(
    OUTPUT_FILE,
    index=False
)


# ---------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------

print()
print("=" * 80)
print("ROADPULSE EVENT CONTEXT ANALYSIS")
print("=" * 80)

print(
    f"Events processed: {len(result)}"
)

print()
print("Motion states:")

print(
    result["motion_state"]
    .value_counts()
)

print()
print("Context categories:")

print(
    result["context"]
    .value_counts()
)

print()
print("Annotation × context:")

print(
    pd.crosstab(
        result["annotation_label"],
        result["context"]
    )
)

print()
print(
    f"Saved: {OUTPUT_FILE}"
)