import pandas as pd
import numpy as np

RECORDING = r"C:\Users\Gaurav\Desktop\Projects\Avishkar2026\30341143\backend\processed\roadpulse_pune_recording.csv"
EVENTS = r"C:\Users\Gaurav\Desktop\Projects\Avishkar2026\30341143\backend\processed\roadpulse_pune_events.csv"
OUTPUT = r"C:\Users\Gaurav\Desktop\Projects\Avishkar2026\30341143\backend\processed\roadpulse_pune_impact_scores.csv"

print("Loading Pune recording...")
df = pd.read_csv(RECORDING)

print("Loading detected events...")
events = pd.read_csv(EVENTS)

results = []

for _, event in events.iterrows():

    start = float(event["start"])
    end = float(event["end"])

    event_df = df[
        (df["seconds_elapsed"] >= start) &
        (df["seconds_elapsed"] <= end)
    ].copy()

    if event_df.empty:
        continue

    event_df["accel_mag"] = pd.to_numeric(
        event_df["accel_mag"], errors="coerce"
    )

    event_df["gyro_mag"] = pd.to_numeric(
        event_df["gyro_mag"], errors="coerce"
    )

    event_df["speed"] = pd.to_numeric(
        event_df["speed"], errors="coerce"
    )

    event_df = event_df.dropna(
        subset=["seconds_elapsed", "accel_mag", "gyro_mag", "speed"]
    )

    if event_df.empty:
        continue

    peak_idx = event_df["accel_mag"].idxmax()
    peak_row = event_df.loc[peak_idx]

    peak_time = float(peak_row["seconds_elapsed"])
    peak_accel = float(peak_row["accel_mag"])

    # 150 ms before and after peak
    before = event_df[
        (event_df["seconds_elapsed"] >= peak_time - 0.15) &
        (event_df["seconds_elapsed"] < peak_time)
    ]

    after = event_df[
        (event_df["seconds_elapsed"] > peak_time) &
        (event_df["seconds_elapsed"] <= peak_time + 0.15)
    ]

    if before.empty:
        before_accel = np.nan
        rise_rate = np.nan
    else:
        before_accel = float(before["accel_mag"].median())
        dt_before = peak_time - float(before["seconds_elapsed"].min())

        if dt_before > 0:
            rise_rate = (peak_accel - before_accel) / dt_before
        else:
            rise_rate = np.nan

    if after.empty:
        after_accel = np.nan
        fall_rate = np.nan
    else:
        after_accel = float(after["accel_mag"].median())
        dt_after = float(after["seconds_elapsed"].max()) - peak_time

        if dt_after > 0:
            fall_rate = (peak_accel - after_accel) / dt_after
        else:
            fall_rate = np.nan

    # Peak prominence relative to local event median
    event_median = float(event_df["accel_mag"].median())

    if event_median > 0:
        peak_prominence = peak_accel / event_median
    else:
        peak_prominence = np.nan

    # Width above 80% of peak
    threshold_80 = peak_accel * 0.80

    above_80 = event_df[
        event_df["accel_mag"] >= threshold_80
    ]

    if len(above_80) > 0:
        peak_width = (
            float(above_80["seconds_elapsed"].max())
            - float(above_80["seconds_elapsed"].min())
        )
    else:
        peak_width = 0.0

    # Maximum gyro around the peak
    gyro_near_peak = event_df[
        (event_df["seconds_elapsed"] >= peak_time - 0.15) &
        (event_df["seconds_elapsed"] <= peak_time + 0.15)
    ]

    if gyro_near_peak.empty:
        peak_gyro_near = np.nan
    else:
        peak_gyro_near = float(gyro_near_peak["gyro_mag"].max())

    # Speed change around the event
    before_speed_df = event_df[
        (event_df["seconds_elapsed"] >= peak_time - 0.5) &
        (event_df["seconds_elapsed"] < peak_time - 0.2)
    ]

    after_speed_df = event_df[
        (event_df["seconds_elapsed"] > peak_time + 0.2) &
        (event_df["seconds_elapsed"] <= peak_time + 0.5)
    ]

    if not before_speed_df.empty and not after_speed_df.empty:
        before_speed = float(before_speed_df["speed"].median())
        after_speed = float(after_speed_df["speed"].median())
        speed_change = after_speed - before_speed
    else:
        before_speed = np.nan
        after_speed = np.nan
        speed_change = np.nan

    # Shape balance:
    # Similar rise/fall rates indicate a sharp impact.
    if (
        pd.notna(rise_rate)
        and pd.notna(fall_rate)
        and rise_rate > 0
        and fall_rate > 0
    ):
        shape_balance = min(rise_rate, fall_rate) / max(
            rise_rate, fall_rate
        )
    else:
        shape_balance = np.nan

    # Simple impact score.
    score = 0

    if peak_prominence >= 3:
        score += 30
    elif peak_prominence >= 2:
        score += 20
    elif peak_prominence >= 1.5:
        score += 10

    if peak_accel >= 25:
        score += 25
    elif peak_accel >= 20:
        score += 20
    elif peak_accel >= 15:
        score += 10

    if pd.notna(shape_balance):
        if shape_balance >= 0.50:
            score += 20
        elif shape_balance >= 0.30:
            score += 10

    if peak_width <= 0.10:
        score += 15
    elif peak_width <= 0.20:
        score += 10

    if pd.notna(peak_gyro_near):
        if peak_gyro_near >= 2:
            score += 10
        elif peak_gyro_near >= 1:
            score += 5

    if score >= 70:
        classification = "STRONG_IMPACT"
    elif score >= 45:
        classification = "MODERATE_IMPACT"
    else:
        classification = "WEAK_IMPACT"

    results.append({
        "start": start,
        "end": end,
        "duration": float(event["duration"]),
        "peak_time": peak_time,
        "peak_accel": peak_accel,
        "event_median_accel": event_median,
        "peak_prominence": peak_prominence,
        "peak_width": peak_width,
        "before_accel": before_accel,
        "after_accel": after_accel,
        "rise_rate": rise_rate,
        "fall_rate": fall_rate,
        "shape_balance": shape_balance,
        "peak_gyro_near": peak_gyro_near,
        "before_speed": before_speed,
        "after_speed": after_speed,
        "speed_change": speed_change,
        "speed": float(event["speed"]),
        "speed_band": event["speed_band"],
        "latitude": float(event["latitude"]),
        "longitude": float(event["longitude"]),
        "impact_score": score,
        "classification": classification,
    })

result_df = pd.DataFrame(results)

result_df = result_df.sort_values(
    ["impact_score", "peak_accel"],
    ascending=False
)

print("\n" + "=" * 110)
print("PUNE IMPACT SIGNATURE ANALYSIS")
print("=" * 110)

print("\nClassification:")
print(result_df["classification"].value_counts())

print("\nScore:")
print(result_df["impact_score"].describe().round(2))

print("\nTOP 20 EVENTS:")
print(
    result_df[
        [
            "start",
            "end",
            "duration",
            "peak_accel",
            "peak_prominence",
            "peak_width",
            "shape_balance",
            "peak_gyro_near",
            "speed",
            "speed_band",
            "impact_score",
            "classification",
            "latitude",
            "longitude",
        ]
    ]
    .head(20)
    .to_string(index=False)
)

result_df.to_csv(OUTPUT, index=False)

print("\nSaved:")
print(OUTPUT)