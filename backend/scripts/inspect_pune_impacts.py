import pandas as pd
import numpy as np

BASE = r"C:\Users\Gaurav\Desktop\Projects\Avishkar2026\30341143"

recording_path = (
    BASE + r"\backend\processed\roadpulse_pune_recording.csv"
)

events_path = (
    BASE + r"\backend\processed\roadpulse_pune_events.csv"
)

df = pd.read_csv(recording_path)
events = pd.read_csv(events_path)

df["seconds_elapsed"] = pd.to_numeric(
    df["seconds_elapsed"], errors="coerce"
)

df["accel_mag"] = pd.to_numeric(
    df["accel_mag"], errors="coerce"
)

df["gyro_mag"] = pd.to_numeric(
    df["gyro_mag"], errors="coerce"
)

df["speed"] = pd.to_numeric(
    df["speed"], errors="coerce"
)

# --------------------------------------------------
# Top 10 events by acceleration
# --------------------------------------------------

top_events = events.sort_values(
    "peak_accel",
    ascending=False
).head(10)

print()
print("=" * 100)
print("PUNE IMPACT INSPECTION")
print("=" * 100)

for number, (_, event) in enumerate(
    top_events.iterrows(),
    start=1
):

    start = float(event["start"])
    end = float(event["end"])

    # Find actual acceleration peak
    section = df[
        (df["seconds_elapsed"] >= start) &
        (df["seconds_elapsed"] <= end)
    ].copy()

    if section.empty:
        continue

    peak_index = section["accel_mag"].idxmax()
    peak_time = float(
        section.loc[peak_index, "seconds_elapsed"]
    )

    # 0.5 second before and after peak
    around = df[
        (df["seconds_elapsed"] >= peak_time - 0.5) &
        (df["seconds_elapsed"] <= peak_time + 0.5)
    ].copy()

    # Sample approximately every 0.1 second
    around["bucket"] = (
        np.round(
            (around["seconds_elapsed"] - peak_time) / 0.1
        ) * 0.1
    )

    summary = (
        around
        .groupby("bucket", as_index=False)
        .agg(
            accel=("accel_mag", "mean"),
            gyro=("gyro_mag", "mean"),
            speed=("speed", "mean")
        )
    )

    print()
    print("-" * 100)
    print(
        f"EVENT #{number} | "
        f"{start:.3f}s → {end:.3f}s | "
        f"speed={event['speed']:.2f} km/h"
    )

    print(
        f"Peak at {peak_time:.3f}s | "
        f"Peak acceleration={section['accel_mag'].max():.3f}"
    )

    print()
    print(
        "Relative time | Acceleration | Gyro | Speed"
    )

    print(
        summary.round(3).to_string(index=False)
    )

print()
print("=" * 100)