import pandas as pd

BASE = r"C:\Users\Gaurav\Desktop\Projects\Avishkar2026\30341143"

events_path = BASE + r"\backend\processed\roadpulse_pune_impact_scores.csv"
clusters_path = BASE + r"\backend\processed\roadpulse_pune_impact_clusters.csv"

events = pd.read_csv(events_path)
clusters = pd.read_csv(clusters_path)

print()
print("=" * 110)
print("PUNE REPEATED IMPACT HOTSPOTS")
print("=" * 110)

# Recreate cluster assignment
import numpy as np
from sklearn.cluster import DBSCAN

candidates = events[
    events["impact_score"] >= 45
].copy()

coordinates = np.radians(
    candidates[["latitude", "longitude"]].values
)

earth_radius = 6371000
radius = 30

model = DBSCAN(
    eps=radius / earth_radius,
    min_samples=1,
    metric="haversine"
)

candidates["cluster_id"] = model.fit_predict(coordinates)

repeated_clusters = (
    candidates.groupby("cluster_id")
    .size()
    .reset_index(name="event_count")
)

repeated_clusters = repeated_clusters[
    repeated_clusters["event_count"] >= 2
].sort_values(
    "event_count",
    ascending=False
)

print(
    "\nRepeated clusters:",
    len(repeated_clusters)
)

for _, cluster in repeated_clusters.iterrows():

    cluster_id = int(cluster["cluster_id"])

    group = candidates[
        candidates["cluster_id"] == cluster_id
    ].sort_values("start")

    print()
    print("-" * 110)

    print(
        f"CLUSTER {cluster_id} | "
        f"{len(group)} EVENTS"
    )

    print(
        f"Location: "
        f"{group['latitude'].mean():.6f}, "
        f"{group['longitude'].mean():.6f}"
    )

    print()

    print(
        group[
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
        .round(3)
        .to_string(index=False)
    )

    print()

    if len(group) > 1:

        times = group["start"].sort_values().values

        print("Time gaps between events:")

        for i in range(1, len(times)):

            gap = times[i] - times[i - 1]

            print(
                f"  {gap:.2f} seconds"
            )

print()
print("=" * 110)