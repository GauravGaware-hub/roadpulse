import os
import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NORMAL_DIR = os.path.join(
    BASE_DIR,
    "..",
    "Combined CSV with GIS and Weather Data",
    "Normal Road (No Annotation)"
)

ANOMALY_DIR = os.path.join(
    BASE_DIR,
    "..",
    "Combined CSV with GIS and Weather Data",
    "Road Anomalies"
)

OUTPUT_DIR = os.path.join(BASE_DIR, "processed")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "roadpulse_features.csv")


# ============================================================
# SETTINGS
# ============================================================

WINDOW_SECONDS = 1.0
STEP_SECONDS = 0.5
MIN_SAMPLES_PER_WINDOW = 80

RANDOM_STATE = 42


# ============================================================
# SENSOR COLUMNS
# ============================================================

ACCEL_COLS = [
    "accelerometer_x",
    "accelerometer_y",
    "accelerometer_z"
]

GYRO_COLS = [
    "gyroscope_x",
    "gyroscope_y",
    "gyroscope_z"
]


# ============================================================
# FEATURE EXTRACTION
# ============================================================

def rms(values):
    return np.sqrt(np.mean(np.square(values)))


def percentile_range(values):
    return np.percentile(values, 95) - np.percentile(values, 5)


def extract_features(window):
    """
    Extract event-oriented features from one sensor window.
    """

    ax = window["accelerometer_x"].to_numpy(dtype=float)
    ay = window["accelerometer_y"].to_numpy(dtype=float)
    az = window["accelerometer_z"].to_numpy(dtype=float)

    gx = window["gyroscope_x"].to_numpy(dtype=float)
    gy = window["gyroscope_y"].to_numpy(dtype=float)
    gz = window["gyroscope_z"].to_numpy(dtype=float)

    # --------------------------------------------------------
    # Acceleration magnitude
    # --------------------------------------------------------

    accel_mag = np.sqrt(ax**2 + ay**2 + az**2)

    # --------------------------------------------------------
    # Gyroscope magnitude
    # --------------------------------------------------------

    gyro_mag = np.sqrt(gx**2 + gy**2 + gz**2)

    # --------------------------------------------------------
    # Jerk
    # --------------------------------------------------------

    jerk = np.diff(accel_mag, prepend=accel_mag[0])

    # --------------------------------------------------------
    # Remove invalid values
    # --------------------------------------------------------

    accel_mag = np.nan_to_num(accel_mag)
    gyro_mag = np.nan_to_num(gyro_mag)
    jerk = np.nan_to_num(jerk)

    features = {}

    # ========================================================
    # ACCELERATION FEATURES
    # ========================================================

    for name, signal in [
        ("accel_x", ax),
        ("accel_y", ay),
        ("accel_z", az),
        ("accel_mag", accel_mag),
    ]:

        signal = np.nan_to_num(signal)

        features[f"{name}_mean"] = np.mean(signal)
        features[f"{name}_std"] = np.std(signal)
        features[f"{name}_min"] = np.min(signal)
        features[f"{name}_max"] = np.max(signal)

        features[f"{name}_rms"] = rms(signal)

        features[f"{name}_p05"] = np.percentile(signal, 5)
        features[f"{name}_p25"] = np.percentile(signal, 25)
        features[f"{name}_p50"] = np.percentile(signal, 50)
        features[f"{name}_p75"] = np.percentile(signal, 75)
        features[f"{name}_p95"] = np.percentile(signal, 95)

        features[f"{name}_p95_p05_range"] = percentile_range(signal)

    # ========================================================
    # GYROSCOPE FEATURES
    # ========================================================

    for name, signal in [
        ("gyro_x", gx),
        ("gyro_y", gy),
        ("gyro_z", gz),
        ("gyro_mag", gyro_mag),
    ]:

        signal = np.nan_to_num(signal)

        features[f"{name}_mean"] = np.mean(signal)
        features[f"{name}_std"] = np.std(signal)
        features[f"{name}_min"] = np.min(signal)
        features[f"{name}_max"] = np.max(signal)
        features[f"{name}_rms"] = rms(signal)

    # ========================================================
    # JERK FEATURES
    # ========================================================

    features["jerk_mean"] = np.mean(jerk)
    features["jerk_std"] = np.std(jerk)
    features["jerk_min"] = np.min(jerk)
    features["jerk_max"] = np.max(jerk)
    features["jerk_rms"] = rms(jerk)

    features["jerk_p95"] = np.percentile(jerk, 95)
    features["jerk_p05"] = np.percentile(jerk, 5)

    features["jerk_range"] = (
        np.percentile(jerk, 95) -
        np.percentile(jerk, 5)
    )

    # ========================================================
    # EVENT / PEAK FEATURES
    # ========================================================

    accel_mean = np.mean(accel_mag)
    accel_std = np.std(accel_mag)

    # Number of strong deviations from the window's baseline
    threshold = accel_mean + (2 * accel_std)

    strong_points = accel_mag > threshold

    features["strong_accel_count"] = int(np.sum(strong_points))

    features["strong_accel_ratio"] = (
        np.sum(strong_points) / len(accel_mag)
        if len(accel_mag) > 0
        else 0
    )

    # Largest deviation from the local baseline
    features["accel_peak_deviation"] = (
        np.max(np.abs(accel_mag - accel_mean))
    )

    # Energy
    features["accel_energy"] = np.sum(accel_mag ** 2)

    features["gyro_energy"] = np.sum(gyro_mag ** 2)

    features["jerk_energy"] = np.sum(jerk ** 2)

    return features


# ============================================================
# WINDOW GENERATION
# ============================================================

def create_windows(df, label, source_file):

    if "seconds_elapsed" not in df.columns:
        return []

    df = df.copy()

    df = df.dropna(
        subset=ACCEL_COLS + GYRO_COLS + ["seconds_elapsed"]
    )

    if len(df) < MIN_SAMPLES_PER_WINDOW:
        return []

    start_time = df["seconds_elapsed"].min()
    end_time = df["seconds_elapsed"].max()

    windows = []

    current = start_time

    while current + WINDOW_SECONDS <= end_time:

        window_end = current + WINDOW_SECONDS

        window = df[
            (df["seconds_elapsed"] >= current) &
            (df["seconds_elapsed"] < window_end)
        ]

        if len(window) >= MIN_SAMPLES_PER_WINDOW:

            features = extract_features(window)

            features["label"] = label
            features["source_file"] = source_file
            features["window_start"] = current
            features["window_end"] = window_end

            windows.append(features)

        current += STEP_SECONDS

    return windows


# ============================================================
# NORMAL DATA
# ============================================================

def process_normal_files():

    all_windows = []

    for filename in sorted(os.listdir(NORMAL_DIR)):

        if not filename.lower().endswith(".csv"):
            continue

        path = os.path.join(NORMAL_DIR, filename)

        print(f"Processing NORMAL: {filename}")

        try:
            df = pd.read_csv(path)

            windows = create_windows(
                df,
                "NORMAL",
                filename
            )

            all_windows.extend(windows)

        except Exception as e:

            print(f"ERROR processing {filename}: {e}")

    return all_windows


# ============================================================
# ANOMALY DATA
# ============================================================

def process_anomaly_files():

    all_windows = []

    for filename in sorted(os.listdir(ANOMALY_DIR)):

        if not filename.lower().endswith(".csv"):
            continue

        # 99.csv has no annotation_text
        if filename == "99.csv":
            print("Skipping 99.csv - no annotation_text")
            continue

        path = os.path.join(ANOMALY_DIR, filename)

        print(f"Processing ANOMALY: {filename}")

        try:

            df = pd.read_csv(path)

            if "annotation_text" not in df.columns:
                print("  No annotation_text - skipped")
                continue

            df["annotation_text"] = (
                df["annotation_text"]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            # Only use known anomaly labels
            df = df[
                df["annotation_text"].isin(
                    ["Bump", "Pothole"]
                )
            ].copy()

            if df.empty:
                continue

            # ------------------------------------------------
            # Find continuous annotation regions
            # ------------------------------------------------

            df = df.sort_values("seconds_elapsed")

            time_diff = df["seconds_elapsed"].diff()

            new_group = (
                time_diff > 0.05
            ).cumsum()

            for _, group in df.groupby(new_group):

                if group.empty:
                    continue

                labels = group["annotation_text"].unique()

                # Avoid mixed-label groups
                if len(labels) != 1:
                    continue

                label = labels[0]

                windows = create_windows(
                    group,
                    label.upper(),
                    filename
                )

                all_windows.extend(windows)

        except Exception as e:

            print(f"ERROR processing {filename}: {e}")

    return all_windows


# ============================================================
# MAIN
# ============================================================

def main():

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("\n========================================")
    print("ROADPULSE FEATURE EXTRACTION")
    print("========================================\n")

    normal_windows = process_normal_files()

    print(
        f"\nNormal windows generated: "
        f"{len(normal_windows)}"
    )

    anomaly_windows = process_anomaly_files()

    print(
        f"Anomaly windows generated: "
        f"{len(anomaly_windows)}"
    )

    all_windows = (
        normal_windows +
        anomaly_windows
    )

    if not all_windows:

        print("No windows generated.")
        return

    dataset = pd.DataFrame(all_windows)

    # Shuffle
    dataset = dataset.sample(
        frac=1,
        random_state=RANDOM_STATE
    ).reset_index(drop=True)

    dataset.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\n========================================")
    print("DATASET CREATED")
    print("========================================")

    print(f"Total windows: {len(dataset)}")

    print("\nCLASS DISTRIBUTION:")
    print(
        dataset["label"]
        .value_counts()
        .to_string()
    )

    print("\nFEATURE COUNT:")

    non_features = [
        "label",
        "source_file",
        "window_start",
        "window_end"
    ]

    feature_count = len(
        [
            c for c in dataset.columns
            if c not in non_features
        ]
    )

    print(feature_count)

    print("\nSaved to:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
