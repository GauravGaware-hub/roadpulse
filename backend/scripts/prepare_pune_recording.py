import os
import numpy as np
import pandas as pd

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

INPUT_DIR = r"C:\Users\Gaurav\Desktop\Projects\Avishkar2026\30341143\Vakratund_Colony-2026-10-06_12-32-23"

OUTPUT_DIR = r"C:\Users\Gaurav\Desktop\Projects\Avishkar2026\30341143\backend\processed"

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "roadpulse_pune_recording.csv"
)

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

print("Loading Sensor Logger files...")

accel = pd.read_csv(
    os.path.join(INPUT_DIR, "Accelerometer.csv")
)

gyro = pd.read_csv(
    os.path.join(INPUT_DIR, "Gyroscope.csv")
)

location = pd.read_csv(
    os.path.join(INPUT_DIR, "Location.csv")
)

print("Accelerometer rows:", len(accel))
print("Gyroscope rows:", len(gyro))
print("Location rows:", len(location))

# --------------------------------------------------
# SORT
# --------------------------------------------------

accel = accel.sort_values("seconds_elapsed").reset_index(drop=True)
gyro = gyro.sort_values("seconds_elapsed").reset_index(drop=True)
location = location.sort_values("seconds_elapsed").reset_index(drop=True)

# --------------------------------------------------
# RENAME
# --------------------------------------------------

accel = accel.rename(
    columns={
        "x": "accelerometer_x",
        "y": "accelerometer_y",
        "z": "accelerometer_z",
    }
)

gyro = gyro.rename(
    columns={
        "x": "gyroscope_x",
        "y": "gyroscope_y",
        "z": "gyroscope_z",
    }
)

# --------------------------------------------------
# SELECT COLUMNS
# --------------------------------------------------

accel = accel[
    [
        "time",
        "seconds_elapsed",
        "accelerometer_x",
        "accelerometer_y",
        "accelerometer_z",
    ]
]

gyro = gyro[
    [
        "seconds_elapsed",
        "gyroscope_x",
        "gyroscope_y",
        "gyroscope_z",
    ]
]

location = location[
    [
        "seconds_elapsed",
        "latitude",
        "longitude",
        "speed",
        "bearing",
        "horizontalAccuracy",
        "verticalAccuracy",
    ]
]

# --------------------------------------------------
# ALIGN GYROSCOPE
# --------------------------------------------------

print("Aligning gyroscope...")

merged = pd.merge_asof(
    accel.sort_values("seconds_elapsed"),
    gyro.sort_values("seconds_elapsed"),
    on="seconds_elapsed",
    direction="nearest",
    tolerance=0.05,
)

# --------------------------------------------------
# REMOVE UNMATCHED GYROSCOPE ROWS
# --------------------------------------------------

before = len(merged)

merged = merged.dropna(
    subset=[
        "gyroscope_x",
        "gyroscope_y",
        "gyroscope_z",
    ]
).reset_index(drop=True)

removed = before - len(merged)

print(
    "Removed rows without gyroscope match:",
    removed
)

# --------------------------------------------------
# GPS ALIGNMENT
# --------------------------------------------------

print("Aligning GPS...")

gps = location.copy()

gps_numeric = [
    "latitude",
    "longitude",
    "speed",
    "bearing",
    "horizontalAccuracy",
    "verticalAccuracy",
]

for column in gps_numeric:
    gps[column] = pd.to_numeric(
        gps[column],
        errors="coerce"
    )

merged = pd.merge_asof(
    merged.sort_values("seconds_elapsed"),
    gps.sort_values("seconds_elapsed"),
    on="seconds_elapsed",
    direction="nearest",
    tolerance=2.0,
)

# --------------------------------------------------
# SENSOR FEATURES
# --------------------------------------------------

print("Calculating sensor features...")

merged["accel_mag"] = np.sqrt(
    merged["accelerometer_x"] ** 2
    + merged["accelerometer_y"] ** 2
    + merged["accelerometer_z"] ** 2
)

merged["gyro_mag"] = np.sqrt(
    merged["gyroscope_x"] ** 2
    + merged["gyroscope_y"] ** 2
    + merged["gyroscope_z"] ** 2
)

# --------------------------------------------------
# JERK
# --------------------------------------------------

dt = merged["seconds_elapsed"].diff()

merged["jerk"] = (
    merged["accel_mag"].diff()
    / dt.replace(0, np.nan)
)

merged["jerk"] = merged["jerk"].replace(
    [np.inf, -np.inf],
    np.nan
)

# First row naturally has no previous sample.
merged["jerk"] = merged["jerk"].fillna(0)

# --------------------------------------------------
# SAVE
# --------------------------------------------------

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

merged.to_csv(
    OUTPUT_FILE,
    index=False
)

# --------------------------------------------------
# FINAL CHECK
# --------------------------------------------------

print()
print("==========================================")
print("ROADPULSE PUNE RECORDING CREATED")
print("==========================================")

print("Output:", OUTPUT_FILE)
print("Rows:", len(merged))
print("Columns:", len(merged.columns))

print(
    "Duration:",
    round(
        merged["seconds_elapsed"].iloc[-1]
        - merged["seconds_elapsed"].iloc[0],
        2
    ),
    "seconds"
)

print()
print("Missing values:")

print(
    merged[
        [
            "accelerometer_x",
            "accelerometer_y",
            "accelerometer_z",
            "gyroscope_x",
            "gyroscope_y",
            "gyroscope_z",
            "latitude",
            "longitude",
            "speed",
            "accel_mag",
            "gyro_mag",
            "jerk",
        ]
    ].isna().sum()
)

print()
print("First rows:")

print(
    merged.head(5).to_string(index=False)
)