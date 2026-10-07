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

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "roadpulse_stage1_features.csv"
)


# ============================================================
# SETTINGS
# ============================================================

WINDOW_SECONDS = 1.0
STEP_SECONDS = 0.5

MIN_SAMPLES_PER_WINDOW = 80

# Time that must separate a normal window
# from an annotated anomaly.
BUFFER_SECONDS = 3.0

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
# BASIC FUNCTIONS
# ============================================================

def rms(values):
    return np.sqrt(np.mean(np.square(values)))


def extract_features(window):

    ax = window["accelerometer_x"].to_numpy(dtype=float)
    ay = window["accelerometer_y"].to_numpy(dtype=float)
    az = window["accelerometer_z"].to_numpy(dtype=float)

    gx = window["gyroscope_x"].to_numpy(dtype=float)
    gy = window["gyroscope_y"].to_numpy(dtype=float)
    gz = window["gyroscope_z"].to_numpy(dtype=float)

    accel_mag = np.sqrt(
        ax**2 +
        ay**2 +
        az**2
    )

    gyro_mag = np.sqrt(
        gx**2 +
        gy**2 +
        gz**2
    )

    jerk = np.diff(
        accel_mag,
        prepend=accel_mag[0]
    )

    accel_mag = np.nan_to_num(accel_mag)
    gyro_mag = np.nan_to_num(gyro_mag)
    jerk = np.nan_to_num(jerk)

    features = {}

    # --------------------------------------------------------
    # Acceleration
    # --------------------------------------------------------

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

        features[f"{name}_range"] = (
            np.percentile(signal, 95) -
            np.percentile(signal, 5)
        )

    # --------------------------------------------------------
    # Gyroscope
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Jerk
    # --------------------------------------------------------

    features["jerk_mean"] = np.mean(jerk)
    features["jerk_std"] = np.std(jerk)
    features["jerk_min"] = np.min(jerk)
    features["jerk_max"] = np.max(jerk)
    features["jerk_rms"] = rms(jerk)

    features["jerk_p05"] = np.percentile(jerk, 5)
    features["jerk_p95"] = np.percentile(jerk, 95)

    features["jerk_range"] = (
        np.percentile(jerk, 95) -
        np.percentile(jerk, 5)
    )

    # --------------------------------------------------------
    # Event-oriented features
    # --------------------------------------------------------

    accel_mean = np.mean(accel_mag)
    accel_std = np.std(accel_mag)

    threshold = (
        accel_mean +
        2 * accel_std
    )

    strong_points = accel_mag > threshold

    features["strong_accel_count"] = int(
        np.sum(strong_points)
    )

    features["strong_accel_ratio"] = (
        np.mean(strong_points)
    )

    features["accel_peak_deviation"] = np.max(
        np.abs(accel_mag - accel_mean)
    )

    features["accel_energy"] = np.sum(
        accel_mag ** 2
    )

    features["gyro_energy"] = np.sum(
        gyro_mag ** 2
    )

    features["jerk_energy"] = np.sum(
        jerk ** 2
    )

    return features


# ============================================================
# WINDOW CREATION
# ============================================================

def create_windows(
    df,
    label,
    source_file,
    allowed_mask=None
):

    if "seconds_elapsed" not in df.columns:
        return []

    df = df.copy()

    if allowed_mask is not None:

        df = df.loc[
            allowed_mask
        ].copy()

    if df.empty:
        return []

    df = df.dropna(
        subset=ACCEL_COLS +
        GYRO_COLS +
        ["seconds_elapsed"]
    )

    if len(df) < MIN_SAMPLES_PER_WINDOW:
        return []

    df = df.sort_values(
        "seconds_elapsed"
    )

    start_time = df["seconds_elapsed"].min()
    end_time = df["seconds_elapsed"].max()

    windows = []

    current = start_time

    while (
        current + WINDOW_SECONDS
        <= end_time
    ):

        window_end = (
            current +
            WINDOW_SECONDS
        )

        window = df[
            (df["seconds_elapsed"] >= current) &
            (df["seconds_elapsed"] < window_end)
        ]

        if len(window) >= MIN_SAMPLES_PER_WINDOW:

            features = extract_features(
                window
            )

            features["label"] = label

            features["source_file"] = (
                source_file
            )

            features["window_start"] = (
                current
            )

            features["window_end"] = (
                window_end
            )

            windows.append(features)

        current += STEP_SECONDS

    return windows


# ============================================================
# NORMAL RECORDINGS
# ============================================================

def process_normal_files():

    all_windows = []

    for filename in sorted(
        os.listdir(NORMAL_DIR)
    ):

        if not filename.endswith(".csv"):
            continue

        path = os.path.join(
            NORMAL_DIR,
            filename
        )

        print(
            f"Processing NORMAL: {filename}"
        )

        df = pd.read_csv(path)

        windows = create_windows(
            df,
            "NORMAL",
            filename
        )

        all_windows.extend(
            windows
        )

    return all_windows


# ============================================================
# ANOMALY RECORDINGS
# ============================================================

def process_anomaly_files():

    all_windows = []

    for filename in sorted(
        os.listdir(ANOMALY_DIR)
    ):

        if not filename.endswith(".csv"):
            continue

        if filename == "99.csv":
            continue

        path = os.path.join(
            ANOMALY_DIR,
            filename
        )

        print(
            f"Processing ANOMALY: {filename}"
        )

        df = pd.read_csv(path)

        if "annotation_text" not in df.columns:
            continue

        df = df.sort_values(
            "seconds_elapsed"
        ).reset_index(drop=True)

        annotations = (
            df["annotation_text"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        event_mask = annotations.isin(
            ["Bump", "Pothole"]
        )

        if not event_mask.any():
            continue

        # ----------------------------------------------------
        # Find each continuous annotated event
        # ----------------------------------------------------

        event_indices = np.where(
            event_mask.to_numpy()
        )[0]

        groups = []

        group_start = event_indices[0]
        previous = event_indices[0]

        for index in event_indices[1:]:

            time_gap = (
                df.loc[index, "seconds_elapsed"]
                -
                df.loc[previous, "seconds_elapsed"]
            )

            if time_gap > 0.05:

                groups.append(
                    (group_start, previous)
                )

                group_start = index

            previous = index

        groups.append(
            (group_start, previous)
        )

        # ----------------------------------------------------
        # Build safe-normal mask
        # ----------------------------------------------------

        safe_mask = np.ones(
            len(df),
            dtype=bool
        )

        for start_idx, end_idx in groups:

            start_time = df.loc[
                start_idx,
                "seconds_elapsed"
            ]

            end_time = df.loc[
                end_idx,
                "seconds_elapsed"
            ]

            unsafe_start = (
                start_time -
                BUFFER_SECONDS
            )

            unsafe_end = (
                end_time +
                BUFFER_SECONDS
            )

            unsafe = (
                (df["seconds_elapsed"] >= unsafe_start)
                &
                (df["seconds_elapsed"] <= unsafe_end)
            )

            safe_mask[unsafe.to_numpy()] = False

        # ----------------------------------------------------
        # Extract safe normal windows
        # ----------------------------------------------------

        normal_windows = create_windows(
            df,
            "NORMAL",
            filename,
            safe_mask
        )

        all_windows.extend(
            normal_windows
        )

        # ----------------------------------------------------
        # Extract anomaly windows
        # ----------------------------------------------------

        for start_idx, end_idx in groups:

            event_df = df.loc[
                start_idx:end_idx
            ].copy()

            labels = (
                event_df["annotation_text"]
                .fillna("")
                .astype(str)
                .str.strip()
                .unique()
            )

            if len(labels) != 1:
                continue

            label = labels[0].upper()

            anomaly_windows = create_windows(
                event_df,
                label,
                filename
            )

            all_windows.extend(
                anomaly_windows
            )

    return all_windows


# ============================================================
# MAIN
# ============================================================

def main():

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    print("=" * 60)
    print("ROADPULSE STAGE 1 DATASET")
    print("=" * 60)

    normal_windows = (
        process_normal_files()
    )

    print(
        f"\nOriginal normal windows: "
        f"{len(normal_windows)}"
    )

    anomaly_windows = (
        process_anomaly_files()
    )

    print(
        f"Windows from anomaly recordings: "
        f"{len(anomaly_windows)}"
    )

    all_windows = (
        normal_windows +
        anomaly_windows
    )

    dataset = pd.DataFrame(
        all_windows
    )

    dataset = dataset.sample(
        frac=1,
        random_state=RANDOM_STATE
    ).reset_index(drop=True)

    dataset.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\n" + "=" * 60)
    print("STAGE 1 DATASET CREATED")
    print("=" * 60)

    print(
        f"\nTotal windows: "
        f"{len(dataset)}"
    )

    print("\nCLASS DISTRIBUTION:")

    print(
        dataset["label"]
        .value_counts()
        .to_string()
    )

    print("\nRECORDING COUNT BY CLASS:")

    print(
        dataset.groupby(
            "label"
        )["source_file"]
        .nunique()
        .to_string()
    )

    non_features = [
        "label",
        "source_file",
        "window_start",
        "window_end"
    ]

    feature_count = len([
        c for c in dataset.columns
        if c not in non_features
    ])

    print(
        f"\nFeature count: "
        f"{feature_count}"
    )

    print("\nSaved to:")

    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
