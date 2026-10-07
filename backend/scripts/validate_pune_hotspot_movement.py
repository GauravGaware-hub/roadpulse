import pandas as pd
import numpy as np

BASE = r"C:\Users\Gaurav\Desktop\Projects\Avishkar2026\30341143"

EVENTS = BASE + r"\backend\processed\roadpulse_pune_impact_scores.csv"

df = pd.read_csv(EVENTS)

# Recreate the same 30 m clustering
from sklearn.cluster import DBSCAN

candidates = df[
    df["impact_score"] >= 45
].copy()

coords = np.radians(
    candidates[["latitude", "longitude"]].values
)

EARTH_RADIUS = 6371000
RADIUS = 30

model = DBSCAN(
    eps=RADIUS / EARTH_RADIUS,
    min_samples=1,
    metric="haversine"
)

candidates["cluster_id"] = model.fit_predict(coords)

repeated = (
    candidates.groupby("cluster_id")
    .size()
    .reset_index(name="count")
)

repeated = repeated[
    repeated["count"] >= 2
]

print()
print("=" * 110)
print("PUNE HOTSPOT MOVEMENT VALIDATION")
print("=" * 110)

for cluster_id in repeated["cluster_id"]:

    group = candidates[
        candidates["cluster_id"] == cluster_id
    ].sort_values("start").reset_index(drop=True)

    print()
    print("-" * 110)
    print(
        f"CLUSTER {cluster_id} | "
        f"{len(group)} EVENTS"
    )

    for i in range(len(group)):

        event = group.iloc[i]

        print(
            f"\nEvent {i+1}: "
            f"{event['start']:.2f}–{event['end']:.2f}s"
        )

        print(
            f"Location: "
            f"{event['latitude']:.6f}, "
            f"{event['longitude']:.6f}"
        )

        print(
            f"Speed: {event['speed']:.2f} km/h | "
            f"Score: {event['impact_score']:.0f} | "
            f"Peak accel: {event['peak_accel']:.2f}"
        )

        if i > 0:

            previous = group.iloc[i - 1]

            lat1 = np.radians(previous["latitude"])
            lon1 = np.radians(previous["longitude"])

            lat2 = np.radians(event["latitude"])
            lon2 = np.radians(event["longitude"])

            dlat = lat2 - lat1
            dlon = lon2 - lon1

            a = (
                np.sin(dlat / 2) ** 2
                +
                np.cos(lat1)
                * np.cos(lat2)
                * np.sin(dlon / 2) ** 2
            )

            distance = (
                2
                * EARTH_RADIUS
                * np.arcsin(np.sqrt(a))
            )

            time_gap = (
                event["start"]
                - previous["end"]
            )

            print(
                f"Distance from previous impact: "
                f"{distance:.2f} m"
            )

            print(
                f"Time gap after previous event: "
                f"{time_gap:.2f} s"
            )

            if time_gap > 0:

                estimated_speed = (
                    distance / time_gap
                ) * 3.6

                print(
                    f"Approx. travel speed between events: "
                    f"{estimated_speed:.2f} km/h"
                )

print()
print("=" * 110)