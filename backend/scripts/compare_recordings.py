import pandas as pd
import numpy as np
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = (
    BASE_DIR
    / "Combined CSV with GIS and Weather Data"
    / "Road Anomalies"
)


FILES = [
    "46.csv",
    "47.csv",
    "68.csv",
    "79.csv",
]


def load_file(filename):
    path = DATA_DIR / filename

    df = pd.read_csv(path)

    required = [
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

    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(
            f"{filename} is missing columns: {missing}"
        )

    return df


def signal_summary(df):
    accel = np.sqrt(
        df["accelerometer_x"] ** 2
        + df["accelerometer_y"] ** 2
        + df["accelerometer_z"] ** 2
    )

    gyro = np.sqrt(
        df["gyroscope_x"] ** 2
        + df["gyroscope_y"] ** 2
        + df["gyroscope_z"] ** 2
    )

    return {
        "rows": len(df),
        "duration_s": df["seconds_elapsed"].max()
        - df["seconds_elapsed"].min(),

        "lat_start": df["location_latitude"].iloc[0],
        "lon_start": df["location_longitude"].iloc[0],

        "lat_end": df["location_latitude"].iloc[-1],
        "lon_end": df["location_longitude"].iloc[-1],

        "accel_mean": accel.mean(),
        "accel_std": accel.std(),
        "accel_max": accel.max(),

        "gyro_mean": gyro.mean(),
        "gyro_std": gyro.std(),
        "gyro_max": gyro.max(),
    }


def compare_signals(df1, df2):
    """
    Compare the raw acceleration signal after interpolating
    both recordings onto the same normalized timeline.

    Correlation close to 1:
        highly similar signal

    Correlation close to 0:
        substantially different signal

    Negative:
        opposite pattern
    """

    accel1 = np.sqrt(
        df1["accelerometer_x"] ** 2
        + df1["accelerometer_y"] ** 2
        + df1["accelerometer_z"] ** 2
    ).to_numpy()

    accel2 = np.sqrt(
        df2["accelerometer_x"] ** 2
        + df2["accelerometer_y"] ** 2
        + df2["accelerometer_z"] ** 2
    ).to_numpy()

    n = min(len(accel1), len(accel2))

    if n < 10:
        return np.nan

    x1 = np.linspace(0, 1, len(accel1))
    x2 = np.linspace(0, 1, len(accel2))

    common = np.linspace(0, 1, n)

    a1 = np.interp(common, x1, accel1)
    a2 = np.interp(common, x2, accel2)

    correlation = np.corrcoef(a1, a2)[0, 1]

    return correlation


print()
print("=" * 80)
print("ROADPULSE RECORDING INDEPENDENCE CHECK")
print("=" * 80)

data = {}

for filename in FILES:

    print(f"\nLoading {filename}...")

    df = load_file(filename)

    data[filename] = df

    summary = signal_summary(df)

    print(
        f"Rows: {summary['rows']}"
    )

    print(
        f"Duration: {summary['duration_s']:.2f} sec"
    )

    print(
        f"Start GPS: "
        f"{summary['lat_start']:.6f}, "
        f"{summary['lon_start']:.6f}"
    )

    print(
        f"End GPS: "
        f"{summary['lat_end']:.6f}, "
        f"{summary['lon_end']:.6f}"
    )

    print(
        f"Acceleration: "
        f"mean={summary['accel_mean']:.4f}, "
        f"std={summary['accel_std']:.4f}, "
        f"max={summary['accel_max']:.4f}"
    )

    print(
        f"Gyroscope: "
        f"mean={summary['gyro_mean']:.4f}, "
        f"std={summary['gyro_std']:.4f}, "
        f"max={summary['gyro_max']:.4f}"
    )


print()
print("=" * 80)
print("PAIRWISE ACCELERATION-SIGNAL CORRELATION")
print("=" * 80)

files = list(data.keys())

for i in range(len(files)):

    for j in range(i + 1, len(files)):

        f1 = files[i]
        f2 = files[j]

        correlation = compare_signals(
            data[f1],
            data[f2]
        )

        print(
            f"{f1:8s} vs {f2:8s} "
            f"correlation = {correlation:.4f}"
        )


print()
print("=" * 80)
print("INTERPRETATION")
print("=" * 80)

print(
    """
The GPS coordinates being identical does NOT prove that the
recordings are independent.

The raw sensor comparison helps determine whether these files
look like separate recordings or highly similar/repeated data.

High signal correlation suggests similar/repeated recordings.

Low signal correlation suggests substantially different
sensor recordings.

This is an investigation only; it is not a final independence
classifier.
"""
)