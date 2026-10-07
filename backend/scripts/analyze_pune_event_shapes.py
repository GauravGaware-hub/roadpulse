import pandas as pd
import numpy as np

BASE = r"C:\Users\Gaurav\Desktop\Projects\Avishkar2026\30341143"

recording_path = (
    BASE + r"\backend\processed\roadpulse_pune_recording.csv"
)

events_path = (
    BASE + r"\backend\processed\roadpulse_pune_events.csv"
)

print("Loading Pune recording...")
df = pd.read_csv(recording_path)

print("Loading detected events...")
events = pd.read_csv(events_path)

# --------------------------------------------------
# Basic preparation
# --------------------------------------------------

df["seconds_elapsed"] = pd.to_numeric(
    df["seconds_elapsed"],
    errors="coerce"
)

df["accel_mag"] = pd.to_numeric(
    df["accel_mag"],
    errors="coerce"
)

df["gyro_mag"] = pd.to_numeric(
    df["gyro_mag"],
    errors="coerce"
)

df["speed"] = pd.to_numeric(
    df["speed"],
    errors="coerce"
)

# --------------------------------------------------
# Analyze strongest events
# --------------------------------------------------

strongest = events.sort_values(
    ["peak_accel", "peak_gyro"],
    ascending=False
).head(10)

results = []

for _, event in strongest.iterrows():

    start = float(event["start"])
    end = float(event["end"])

    # 1 second before and after
    before = df[
        (df["seconds_elapsed"] >= start - 1.0) &
        (df["seconds_elapsed"] < start)
    ]

    during = df[
        (df["seconds_elapsed"] >= start) &
        (df["seconds_elapsed"] <= end)
    ]

    after = df[
        (df["seconds_elapsed"] > end) &
        (df["seconds_elapsed"] <= end + 1.0)
    ]

    if len(during) == 0:
        continue

    # --------------------------------------------------
    # Acceleration statistics
    # --------------------------------------------------

    before_accel = (
        before["accel_mag"].median()
        if len(before) else np.nan
    )

    during_accel = during["accel_mag"]

    after_accel = (
        after["accel_mag"].median()
        if len(after) else np.nan
    )

    peak_accel = during_accel.max()

    median_accel = during_accel.median()

    accel_std = during_accel.std()

    # How much higher is the peak than the pre-event baseline?
    peak_rise = (
        peak_accel - before_accel
        if pd.notna(before_accel)
        else np.nan
    )

    # --------------------------------------------------
    # Strong acceleration duration
    # --------------------------------------------------

    threshold = before_accel + (
        0.5 * peak_rise
        if pd.notna(peak_rise)
        else 0
    )

    strong = during_accel > threshold

    if strong.any():
        strong_duration = (
            strong.sum() /
            max(len(during), 1)
        ) * (end - start)
    else:
        strong_duration = 0.0

    # --------------------------------------------------
    # Speed change
    # --------------------------------------------------

    before_speed = (
        before["speed"].median()
        if len(before) else np.nan
    )

    during_speed = during["speed"].median()

    after_speed = (
        after["speed"].median()
        if len(after) else np.nan
    )

    speed_change = (
        during_speed - before_speed
        if pd.notna(before_speed)
        else np.nan
    )

    # --------------------------------------------------
    # Gyroscope
    # --------------------------------------------------

    gyro_peak = during["gyro_mag"].max()
    gyro_median = during["gyro_mag"].median()

    # --------------------------------------------------
    # Store
    # --------------------------------------------------

    results.append({
        "start": start,
        "end": end,
        "duration": end - start,

        "peak_accel": peak_accel,
        "before_accel": before_accel,
        "after_accel": after_accel,
        "peak_rise": peak_rise,
        "median_accel": median_accel,
        "accel_std": accel_std,

        "strong_duration": strong_duration,

        "peak_gyro": gyro_peak,
        "median_gyro": gyro_median,

        "before_speed": before_speed,
        "during_speed": during_speed,
        "after_speed": after_speed,
        "speed_change": speed_change,

        "latitude": event["latitude"],
        "longitude": event["longitude"],
    })


result_df = pd.DataFrame(results)

print()
print("=" * 100)
print("PUNE EVENT SHAPE ANALYSIS — TOP 10 EVENTS")
print("=" * 100)

print(
    result_df.round(3).to_string(index=False)
)

# --------------------------------------------------
# Save
# --------------------------------------------------

output_path = (
    BASE +
    r"\backend\processed\roadpulse_pune_event_shapes.csv"
)

result_df.to_csv(
    output_path,
    index=False
)

print()
print("Saved:")
print(output_path)