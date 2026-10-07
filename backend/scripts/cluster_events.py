import os
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN


# ============================================================
# CONFIG
# ============================================================

INPUT_FILE = r"backend\processed\roadpulse_events.csv"

OUTPUT_EVENTS = r"backend\processed\roadpulse_events_clustered.csv"
OUTPUT_CLUSTERS = r"backend\processed\roadpulse_event_clusters.csv"

CLUSTER_RADIUS_METERS = 30
MIN_RECORDINGS = 2


# ============================================================
# SPATIAL CLUSTERING
# ============================================================

def cluster_coordinates(df, radius_meters):

    coordinates = np.radians(
        df[["latitude", "longitude"]].values
    )

    earth_radius = 6371000.0
    epsilon = radius_meters / earth_radius

    model = DBSCAN(
        eps=epsilon,
        min_samples=1,
        metric="haversine"
    )

    return model.fit_predict(coordinates)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("ROADPULSE - SPATIAL EVENT CLUSTERING")
    print("=" * 70)

    if not os.path.exists(INPUT_FILE):
        print("\nERROR: Input file not found:")
        print(INPUT_FILE)
        return

    df = pd.read_csv(INPUT_FILE)

    print(f"\nEvents loaded: {len(df)}")

    # --------------------------------------------------------
    # GPS
    # --------------------------------------------------------

    df = df.dropna(
        subset=["latitude", "longitude"]
    ).copy()

    print(
        f"Events with GPS: {len(df)}"
    )

    if len(df) == 0:
        print("No GPS events available.")
        return

    # --------------------------------------------------------
    # Cluster events
    # --------------------------------------------------------

    df["cluster_id"] = cluster_coordinates(
        df,
        CLUSTER_RADIUS_METERS
    )

    # --------------------------------------------------------
    # Build cluster summaries
    # --------------------------------------------------------

    clusters = []

    for cluster_id, group in df.groupby("cluster_id"):

        unique_recordings = group[
            "source_file"
        ].nunique()

        unique_labels = sorted(
            set(
                group["label"]
                .astype(str)
            )
        )

        latitude = group["latitude"].median()
        longitude = group["longitude"].median()

        event_count = len(group)

        multi_recording = (
            unique_recordings >= MIN_RECORDINGS
        )

        bump_count = (
            group["label"]
            .astype(str)
            .str.contains("Bump")
            .sum()
        )

        pothole_count = (
            group["label"]
            .astype(str)
            .str.contains("Pothole")
            .sum()
        )

        unknown_count = (
            group["label"]
            .astype(str)
            .eq("UNKNOWN")
            .sum()
        )

        clusters.append({
            "cluster_id": cluster_id,
            "latitude": latitude,
            "longitude": longitude,
            "event_count": event_count,
            "unique_recordings": unique_recordings,
            "bump_evidence": bump_count,
            "pothole_evidence": pothole_count,
            "unknown_events": unknown_count,
            "labels": ",".join(unique_labels),
            "multi_recording": multi_recording,
        })

    clusters_df = pd.DataFrame(clusters)

    # --------------------------------------------------------
    # Sort strongest clusters first
    # --------------------------------------------------------

    clusters_df = clusters_df.sort_values(
        by=[
            "unique_recordings",
            "event_count"
        ],
        ascending=False
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Save clustered EVENTS
    # --------------------------------------------------------

    df.to_csv(
        OUTPUT_EVENTS,
        index=False
    )

    # --------------------------------------------------------
    # Save CLUSTER summaries
    # --------------------------------------------------------

    clusters_df.to_csv(
        OUTPUT_CLUSTERS,
        index=False
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("CLUSTER SUMMARY")
    print("=" * 70)

    print(
        f"Total spatial clusters: "
        f"{len(clusters_df)}"
    )

    print(
        f"Clusters with >= {MIN_RECORDINGS} recordings: "
        f"{clusters_df['multi_recording'].sum()}"
    )

    print(
        f"Clusters with only one recording: "
        f"{(~clusters_df['multi_recording']).sum()}"
    )

    print("\nUNIQUE RECORDINGS PER CLUSTER:")

    print(
        clusters_df["unique_recordings"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\nTOP MULTI-RECORDING CLUSTERS:")

    multi = clusters_df[
        clusters_df["multi_recording"]
    ]

    if len(multi) == 0:

        print(
            "No multi-recording clusters found "
            f"within {CLUSTER_RADIUS_METERS} metres."
        )

    else:

        print(
            multi.head(30).to_string(
                index=False
            )
        )

    print("\nOUTPUT EVENTS:")
    print(OUTPUT_EVENTS)

    print("\nOUTPUT CLUSTERS:")
    print(OUTPUT_CLUSTERS)


if __name__ == "__main__":
    main()