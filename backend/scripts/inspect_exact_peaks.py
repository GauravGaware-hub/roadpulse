import pandas as pd

BASE = r"C:\Users\Gaurav\Desktop\Projects\Avishkar2026\30341143"

df = pd.read_csv(
    BASE + r"\backend\processed\roadpulse_pune_recording.csv"
)

events = pd.read_csv(
    BASE + r"\backend\processed\roadpulse_pune_events.csv"
)

top = events.sort_values(
    "peak_accel",
    ascending=False
).head(5)

print()
print("=" * 100)
print("EXACT PEAK SIGNATURES")
print("=" * 100)

for number, (_, event) in enumerate(top.iterrows(), 1):

    start = float(event["start"])
    end = float(event["end"])

    section = df[
        (df["seconds_elapsed"] >= start) &
        (df["seconds_elapsed"] <= end)
    ]

    peak_idx = section["accel_mag"].idxmax()

    peak_time = float(
        df.loc[peak_idx, "seconds_elapsed"]
    )

    around = df[
        (df["seconds_elapsed"] >= peak_time - 0.15) &
        (df["seconds_elapsed"] <= peak_time + 0.15)
    ].copy()

    around["relative_time"] = (
        around["seconds_elapsed"] - peak_time
    )

    print()
    print(
        f"EVENT #{number} | "
        f"{start:.3f} → {end:.3f}s | "
        f"speed={event['speed']:.2f} km/h"
    )

    print(
        f"Peak time={peak_time:.6f}s | "
        f"Peak acceleration={section['accel_mag'].max():.3f}"
    )

    print()

    print(
        around[
            [
                "relative_time",
                "accel_mag",
                "gyro_mag",
                "speed"
            ]
        ].round(4).to_string(index=False)
    )