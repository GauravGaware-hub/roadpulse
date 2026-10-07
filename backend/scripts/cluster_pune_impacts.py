import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN

BASE = r"C:\Users\Gaurav\Desktop\Projects\Avishkar2026\30341143"

INPUT = BASE + r"\backend\processed\roadpulse_pune_impact_scores.csv"
OUTPUT = BASE + r"\backend\processed\roadpulse_pune_impact_clusters.csv"

df = pd.read_csv(INPUT)

print()
print("=" * 110)
print("PUNE IMPACT SPATIAL CLUSTERING")
print("=" * 110)

print("\nTotal impact events:", len(df))

# Only reasonably strong candidates
candidates = df[
    df["impact_score"] >= 45
].copy()

print("Candidates with score >= 45:", len(candidates))

if candidates.empty:
    print("\nNo candidates found.")
    raise SystemExit

# Remove rows with missing GPS
candidates = candidates.dropna(
    subset=["latitude", "longitude"]
).copy()

# Convert latitude/longitude to radians
coordinates = np.radians(
    candidates[["latitude", "longitude"]].values
)

# 30 metre spatial radius
EARTH_RADIUS_METERS = 6371000
RADIUS_METERS = 30

epsilon = RADIUS_METERS / EARTH_RADIUS_METERS

model = DBSCAN(
    eps=epsilon,
    min_samples=1,
    metric="haversine"
)

candidates["cluster_id"] = model.fit_predict(coordinates)

# Build cluster summary
clusters = []

for cluster_id, group in candidates.groupby("cluster_id"):

    if cluster_id == -1:
        continue

    lat = group["latitude"].mean()
    lon = group["longitude"].mean()

    clusters.append({
        "cluster_id": int(cluster_id),
        "event_count": len(group),
        "max_impact_score": group["impact_score"].max(),
        "mean_impact_score": group["impact_score"].mean(),
        "max_peak_accel": group["peak_accel"].max(),
        "mean_peak_accel": group["peak_accel"].mean(),
        "strong_events": int(
            (group["classification"] == "STRONG_IMPACT").sum()
        ),
        "moderate_events": int(
            (group["classification"] == "MODERATE_IMPACT").sum()
        ),
        "latitude": lat,
        "longitude": lon,
        "first_event": group["start"].min(),
        "last_event": group["end"].max(),
    })

cluster_df = pd.DataFrame(clusters)

cluster_df = cluster_df.sort_values(
    ["event_count", "max_impact_score"],
    ascending=False
)

print("\nNumber of spatial clusters:", len(cluster_df))

print("\n" + "-" * 110)
print("SPATIAL CLUSTERS")
print("-" * 110)

print(
    cluster_df[
        [
            "cluster_id",
            "event_count",
            "strong_events",
            "moderate_events",
            "max_impact_score",
            "mean_impact_score",
            "max_peak_accel",
            "latitude",
            "longitude",
        ]
    ]
    .to_string(index=False)
)

print("\n" + "-" * 110)
print("MOST REPEATED LOCATIONS")
print("-" * 110)

repeated = cluster_df[
    cluster_df["event_count"] >= 2
]

if repeated.empty:
    print("No locations have 2 or more impact events within 30 metres.")
else:
    print(
        repeated[
            [
                "cluster_id",
                "event_count",
                "strong_events",
                "max_impact_score",
                "mean_impact_score",
                "max_peak_accel",
                "latitude",
                "longitude",
            ]
        ].to_string(index=False)
    )

cluster_df.to_csv(OUTPUT, index=False)

print("\nSaved:")
print(OUTPUT)