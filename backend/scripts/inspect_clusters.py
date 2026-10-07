import math
import pandas as pd


INPUT_FILE = r"backend\processed\roadpulse_events_clustered.csv"
CLUSTER_FILE = r"backend\processed\roadpulse_event_clusters.csv"


def haversine(lat1, lon1, lat2, lon2):

    R = 6371000.0

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return 2 * R * math.asin(
        math.sqrt(a)
    )


def main():

    print("=" * 70)
    print("ROADPULSE - MULTI-RECORDING CLUSTER INSPECTION")
    print("=" * 70)

    events = pd.read_csv(INPUT_FILE)
    clusters = pd.read_csv(CLUSTER_FILE)

    multi_clusters = clusters[
        clusters["unique_recordings"] >= 2
    ].copy()

    print(
        f"\nMulti-recording clusters: "
        f"{len(multi_clusters)}"
    )

    for _, cluster in multi_clusters.iterrows():

        cluster_id = int(
            cluster["cluster_id"]
        )

        group = events[
            events["cluster_id"] == cluster_id
        ].copy()

        center_lat = cluster["latitude"]
        center_lon = cluster["longitude"]

        print("\n" + "-" * 70)

        print(
            f"CLUSTER {cluster_id}"
        )

        print(
            f"Center: "
            f"{center_lat:.6f}, "
            f"{center_lon:.6f}"
        )

        print(
            f"Events: "
            f"{len(group)}"
        )

        print(
            f"Unique recordings: "
            f"{group['source_file'].nunique()}"
        )

        print("\nEVENTS:")

        for _, event in group.iterrows():

            distance = haversine(
                center_lat,
                center_lon,
                event["latitude"],
                event["longitude"]
            )

            print(
                f"  {event['source_file']:>8} | "
                f"{event['label']:<15} | "
                f"{event['motion_state']:<10} | "
                f"speed={event['median_speed_kmh']:>6.2f} | "
                f"distance={distance:>6.2f} m | "
                f"GPS=({event['latitude']:.6f}, "
                f"{event['longitude']:.6f})"
            )

    print("\n" + "=" * 70)
    print("INSPECTION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()