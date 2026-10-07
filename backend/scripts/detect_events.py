import os
import glob
import numpy as np
import pandas as pd


# ============================================================
# CONFIG
# ============================================================

DATA_DIR = r"Combined CSV with GIS and Weather Data\Road Anomalies"
OUTPUT_FILE = r"backend\processed\roadpulse_events.csv"

WINDOW_SECONDS = 1.0
STEP_SECONDS = 0.5

# Current detector thresholds.
# We are NOT tuning these yet.
ACCEL_STD_THRESHOLD = 0.75
GYRO_STD_THRESHOLD = 0.08

MAX_GAP_SECONDS = 1.0


# ============================================================
# HELPERS
# ============================================================

def get_motion_state(speed_kmh):
    if pd.isna(speed_kmh):
        return "UNKNOWN"

    if speed_kmh < 3:
        return "STOPPED"
    elif speed_kmh < 15:
        return "VERY_SLOW"
    elif speed_kmh < 30:
        return "SLOW"
    elif speed_kmh < 50:
        return "MOVING"
    else:
        return "FAST"


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Distance between two GPS coordinates in meters.
    """
    R = 6371000.0

    lat1 = np.radians(lat1)
    lat2 = np.radians(lat2)

    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    return 2 * R * np.arcsin(np.sqrt(a))


def calculate_speed(df):
    """
    Estimate vehicle speed from consecutive GPS points.
    """

    lat = pd.to_numeric(df["location_latitude"], errors="coerce")
    lon = pd.to_numeric(df["location_longitude"], errors="coerce")
    time = pd.to_numeric(df["seconds_elapsed"], errors="coerce")

    speed = np.full(len(df), np.nan)

    for i in range(1, len(df)):
        if (
            pd.isna(lat.iloc[i])
            or pd.isna(lon.iloc[i])
            or pd.isna(lat.iloc[i - 1])
            or pd.isna(lon.iloc[i - 1])
            or pd.isna(time.iloc[i])
            or pd.isna(time.iloc[i - 1])
        ):
            continue

        dt = time.iloc[i] - time.iloc[i - 1]

        if dt <= 0:
            continue

        distance = haversine_distance(
            lat.iloc[i - 1],
            lon.iloc[i - 1],
            lat.iloc[i],
            lon.iloc[i],
        )

        speed[i] = (distance / dt) * 3.6

    # First point gets the nearest valid speed.
    if len(speed) > 1:
        speed[0] = speed[1]

    return speed


def get_window_label(window):
    """
    Determine annotation label for a window.

    If multiple labels occur, combine them.
    If nothing is annotated, return UNKNOWN.
    """

    labels = (
        window["annotation_text"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    labels = labels[labels != ""]

    if len(labels) == 0:
        return "UNKNOWN"

    labels = sorted(set(labels))

    if len(labels) == 1:
        return labels[0]

    return ",".join(labels)


# ============================================================
# PROCESS ONE FILE
# ============================================================

def process_file(file_path):

    filename = os.path.basename(file_path)

    print(f"\nProcessing: {filename}")

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"  ERROR reading file: {e}")
        return []

    required_columns = [
        "seconds_elapsed",
        "accelerometer_x",
        "accelerometer_y",
        "accelerometer_z",
        "gyroscope_x",
        "gyroscope_y",
        "gyroscope_z",
        "annotation_text",
        "location_latitude",
        "location_longitude",
    ]

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        print(f"  SKIPPED - missing columns: {missing}")
        return []

    # --------------------------------------------------------
    # Numeric conversion
    # --------------------------------------------------------

    numeric_columns = [
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

    for col in numeric_columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df = df.dropna(
        subset=[
            "seconds_elapsed",
            "accelerometer_x",
            "accelerometer_y",
            "accelerometer_z",
            "gyroscope_x",
            "gyroscope_y",
            "gyroscope_z",
        ]
    ).reset_index(drop=True)

    if len(df) < 100:
        print("  SKIPPED - too few rows")
        return []

    # --------------------------------------------------------
    # Sensor magnitudes
    # --------------------------------------------------------

    df["accel_mag"] = np.sqrt(
        df["accelerometer_x"] ** 2
        + df["accelerometer_y"] ** 2
        + df["accelerometer_z"] ** 2
    )

    df["gyro_mag"] = np.sqrt(
        df["gyroscope_x"] ** 2
        + df["gyroscope_y"] ** 2
        + df["gyroscope_z"] ** 2
    )

    # Changes between consecutive samples.
    df["accel_change"] = df["accel_mag"].diff().abs().fillna(0)
    df["gyro_change"] = df["gyro_mag"].diff().abs().fillna(0)

    # --------------------------------------------------------
    # GPS-derived speed
    # --------------------------------------------------------

    df["speed_kmh"] = calculate_speed(df)

    # --------------------------------------------------------
    # Window parameters
    # --------------------------------------------------------

    start_time = df["seconds_elapsed"].min()
    end_time = df["seconds_elapsed"].max()

    window_starts = np.arange(
        start_time,
        end_time - WINDOW_SECONDS + 0.001,
        STEP_SECONDS
    )

    candidate_windows = []

    for window_start in window_starts:

        window_end = window_start + WINDOW_SECONDS

        window = df[
            (df["seconds_elapsed"] >= window_start)
            & (df["seconds_elapsed"] < window_end)
        ]

        if len(window) < 50:
            continue

        accel_std = window["accel_mag"].std()
        gyro_std = window["gyro_mag"].std()

        accel_change = window["accel_change"].mean()
        gyro_change = window["gyro_change"].mean()

        motion_score = (
            accel_std
            + gyro_std
            + accel_change
            + gyro_change
        )

        is_candidate = (
            accel_std > ACCEL_STD_THRESHOLD
            and gyro_std > GYRO_STD_THRESHOLD
        )

        if not is_candidate:
            continue

        candidate_windows.append({
            "start": window_start,
            "end": window_end,
            "motion_score": motion_score,
        })

    # --------------------------------------------------------
    # Merge nearby candidate windows
    # --------------------------------------------------------

    events = []

    if candidate_windows:

        current = candidate_windows[0].copy()

        for candidate in candidate_windows[1:]:

            gap = candidate["start"] - current["end"]

            if gap <= MAX_GAP_SECONDS:

                current["end"] = max(
                    current["end"],
                    candidate["end"]
                )

                current["motion_score"] = max(
                    current["motion_score"],
                    candidate["motion_score"]
                )

            else:

                events.append(current)
                current = candidate.copy()

        events.append(current)

    # --------------------------------------------------------
    # Convert episodes to event records
    # --------------------------------------------------------

    file_events = []

    for event_number, event in enumerate(events, start=1):

        event_start = event["start"]
        event_end = event["end"]

        event_df = df[
            (df["seconds_elapsed"] >= event_start)
            & (df["seconds_elapsed"] <= event_end)
        ]

        if len(event_df) == 0:
            continue

        # GPS
        valid_gps = event_df[
            event_df["location_latitude"].notna()
            & event_df["location_longitude"].notna()
        ]

        if len(valid_gps) > 0:
            latitude = valid_gps["location_latitude"].median()
            longitude = valid_gps["location_longitude"].median()
        else:
            latitude = np.nan
            longitude = np.nan

        # Speed
        median_speed = event_df["speed_kmh"].median()

        # Motion state
        motion_state = get_motion_state(
            median_speed
        )

        # Label
        label = get_window_label(event_df)

        file_events.append({
            "source_file": filename,
            "event": event_number,
            "start": round(event_start, 2),
            "end": round(event_end, 2),
            "duration": round(
                event_end - event_start,
                2
            ),
            "peak_motion": round(
                event["motion_score"],
                3
            ),
            "max_accel": round(
                event_df["accel_mag"].max(),
                3
            ),
            "max_gyro": round(
                event_df["gyro_mag"].max(),
                3
            ),
            "median_speed_kmh": round(
                median_speed,
                2
            ) if not pd.isna(median_speed) else np.nan,
            "motion_state": motion_state,
            "latitude": latitude,
            "longitude": longitude,
            "label": label,
        })

    print(
        f"  rows={len(df):,} | "
        f"candidate_windows={len(candidate_windows)} | "
        f"events={len(file_events)}"
    )

    return file_events


# ============================================================
# MAIN
# ============================================================

def main():

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

    files = sorted(
        glob.glob(
            os.path.join(DATA_DIR, "*.csv")
        )
    )

    print("=" * 70)
    print("ROADPULSE - MULTI-RECORDING EVENT DETECTOR")
    print("=" * 70)

    print(f"Dataset directory: {DATA_DIR}")
    print(f"CSV files found: {len(files)}")

    all_events = []

    processed_files = 0

    for file_path in files:

        filename = os.path.basename(file_path)

        # 99.csv has no annotation_text.
        if filename == "99.csv":
            print(f"\nSkipping {filename} - no annotations")
            continue

        events = process_file(file_path)

        all_events.extend(events)

        processed_files += 1

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    events_df = pd.DataFrame(all_events)

    if len(events_df) == 0:
        print("\nNo events detected.")
        return

    events_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    print(
        f"Processed recordings: {processed_files}"
    )

    print(
        f"Total motion episodes: {len(events_df)}"
    )

    print("\nLABEL COUNTS:")
    print(
        events_df["label"]
        .value_counts()
        .to_string()
    )

    print("\nEVENTS PER RECORDING:")
    print(
        events_df["source_file"]
        .value_counts()
        .describe()
        .to_string()
    )

    print("\nMOTION STATES:")
    print(
        events_df["motion_state"]
        .value_counts()
        .to_string()
    )

    print("\nLABEL × MOTION STATE:")
    print(
        pd.crosstab(
            events_df["label"],
            events_df["motion_state"]
        ).to_string()
    )

    print("\nGPS COVERAGE:")
    gps_valid = (
        events_df["latitude"].notna()
        & events_df["longitude"].notna()
    )

    print(
        f"Events with GPS: "
        f"{gps_valid.sum()} / {len(events_df)}"
    )

    print("\nEVENT DURATION:")
    print(
        events_df["duration"]
        .describe()
        .to_string()
    )

    print("\nOUTPUT:")
    print(OUTPUT_FILE)

    print("\nFirst 20 events:")
    print(
        events_df.head(20).to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()