"""Sensor Logger recording -> impact events -> hotspots.

This is a function-level port of the research scripts, with identical
thresholds and formulas but no hard-coded paths or file output:

    prepare_pune_recording.py        -> prepare_recording()
    detect_pune_events.py            -> detect_events()
    score_pune_impact_signatures.py  -> score_events()
    cluster_pune_impacts.py          -> cluster_events()

The scripts in backend/scripts/ are left untouched. All scores are heuristic
prototype values, not validated pothole detections.
"""
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

from app.services.data_service import add_priority, confidence_level

# --- parameters copied from the research scripts ---------------------------
GYRO_TOLERANCE_S = 0.05
GPS_TOLERANCE_S = 2.0
WINDOW_SECONDS = 1.0
STEP_SECONDS = 0.5
MAX_GAP_SECONDS = 1.0
MIN_WINDOW_SAMPLES = 50
CANDIDATE_Z = 3.0
MIN_MOVING_SPEED = 1.0
HOTSPOT_MIN_SCORE = 45
HOTSPOT_RADIUS_M = 30
EARTH_RADIUS_M = 6371000

# --- sanity limits for uploaded data ---------------------------------------
MIN_SENSOR_ROWS = 500   # ~5 s at 100 Hz
MIN_GPS_ROWS = 2
MIN_DURATION_S = 5.0

# Columns each Sensor Logger file must contain
REQUIRED_COLUMNS = {
    "accelerometer": ["seconds_elapsed", "x", "y", "z"],
    "gyroscope": ["seconds_elapsed", "x", "y", "z"],
    "location": ["seconds_elapsed", "latitude", "longitude", "speed"],
}


class ProcessingError(Exception):
    """The recording is unusable. Message is safe to show to API clients."""


def _numeric(df: pd.DataFrame, cols: list[str], name: str) -> pd.DataFrame:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ProcessingError(f"{name} is missing required column(s): {', '.join(missing)}")
    df = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    return df.sort_values("seconds_elapsed").reset_index(drop=True)


def prepare_recording(accel: pd.DataFrame, gyro: pd.DataFrame, location: pd.DataFrame) -> pd.DataFrame:
    """Synchronise accelerometer, gyroscope and GPS and add accel_mag, gyro_mag, jerk."""
    accel = _numeric(accel, REQUIRED_COLUMNS["accelerometer"], "Accelerometer.csv")
    gyro = _numeric(gyro, REQUIRED_COLUMNS["gyroscope"], "Gyroscope.csv")
    gps = _numeric(location, REQUIRED_COLUMNS["location"], "Location.csv")

    if len(accel) < MIN_SENSOR_ROWS:
        raise ProcessingError(f"Insufficient accelerometer data: {len(accel)} valid rows (need {MIN_SENSOR_ROWS}+)")
    if len(gyro) < MIN_SENSOR_ROWS:
        raise ProcessingError(f"Insufficient gyroscope data: {len(gyro)} valid rows (need {MIN_SENSOR_ROWS}+)")
    if len(gps) < MIN_GPS_ROWS:
        raise ProcessingError(f"Insufficient GPS data: {len(gps)} valid rows (need {MIN_GPS_ROWS}+)")

    accel = accel.rename(columns={"x": "accelerometer_x", "y": "accelerometer_y", "z": "accelerometer_z"})
    gyro = gyro.rename(columns={"x": "gyroscope_x", "y": "gyroscope_y", "z": "gyroscope_z"})

    merged = pd.merge_asof(accel, gyro, on="seconds_elapsed", direction="nearest", tolerance=GYRO_TOLERANCE_S)
    merged = merged.dropna(subset=["gyroscope_x", "gyroscope_y", "gyroscope_z"]).reset_index(drop=True)
    if len(merged) < MIN_SENSOR_ROWS:
        raise ProcessingError("Accelerometer and gyroscope timestamps do not overlap enough to synchronise")

    merged = pd.merge_asof(merged, gps, on="seconds_elapsed", direction="nearest", tolerance=GPS_TOLERANCE_S)
    if merged["latitude"].notna().sum() == 0:
        raise ProcessingError("Insufficient GPS data: no GPS fix overlaps the sensor timeline")

    duration = merged["seconds_elapsed"].iloc[-1] - merged["seconds_elapsed"].iloc[0]
    if duration < MIN_DURATION_S:
        raise ProcessingError(f"Recording too short: {duration:.1f} s (need {MIN_DURATION_S:.0f}+ s)")

    merged["accel_mag"] = np.sqrt(merged["accelerometer_x"] ** 2 + merged["accelerometer_y"] ** 2 + merged["accelerometer_z"] ** 2)
    merged["gyro_mag"] = np.sqrt(merged["gyroscope_x"] ** 2 + merged["gyroscope_y"] ** 2 + merged["gyroscope_z"] ** 2)

    dt = merged["seconds_elapsed"].diff()
    jerk = merged["accel_mag"].diff() / dt.replace(0, np.nan)
    merged["jerk"] = jerk.replace([np.inf, -np.inf], np.nan).fillna(0)
    return merged


def speed_band(speed: float) -> str:
    if speed < 1:
        return "STOPPED"
    elif speed < 3:
        return "VERY_SLOW"
    elif speed < 6:
        return "SLOW"
    elif speed < 10:
        return "MODERATE"
    return "MOVING"


def _event_from_window(row) -> dict:
    return {
        "start": float(row["start"]), "end": float(row["end"]),
        "peak_accel": float(row["accel_max"]), "peak_gyro": float(row["gyro_max"]),
        "peak_accel_score": float(row["accel_score"]), "peak_gyro_score": float(row["gyro_score"]),
        "speed": float(row["speed"]), "speed_band": row["speed_band"],
        "latitude": float(row["latitude"]), "longitude": float(row["longitude"]),
    }


def detect_events(d: pd.DataFrame) -> pd.DataFrame:
    """1 s windows (0.5 s step) -> speed-adaptive robust z-scores -> merged candidate events."""
    t = d["seconds_elapsed"].to_numpy()
    windows = []
    current = t.min()
    end = t.max()
    while current + WINDOW_SECONDS <= end:
        lo = np.searchsorted(t, current, side="left")
        hi = np.searchsorted(t, current + WINDOW_SECONDS, side="left")
        if hi - lo >= MIN_WINDOW_SAMPLES:
            w = d.iloc[lo:hi]
            windows.append({
                "start": current, "end": current + WINDOW_SECONDS,
                "accel_mean": w["accel_mag"].mean(), "accel_std": w["accel_mag"].std(),
                "accel_max": w["accel_mag"].max(), "gyro_std": w["gyro_mag"].std(),
                "gyro_max": w["gyro_mag"].max(), "jerk_std": w["jerk"].std(),
                "speed": w["speed"].median(),
                "latitude": w["latitude"].median(), "longitude": w["longitude"].median(),
            })
        current += STEP_SECONDS

    cols = ["start", "end", "duration", "peak_accel", "peak_gyro", "peak_accel_score", "peak_gyro_score",
            "speed", "speed_band", "latitude", "longitude"]
    if not windows:
        return pd.DataFrame(columns=cols)

    ev = pd.DataFrame(windows)
    ev["speed_band"] = ev["speed"].apply(speed_band)

    def mad(x):
        return np.median(np.abs(x - np.median(x)))

    baseline = ev.groupby("speed_band").agg(
        accel_std_median=("accel_std", "median"), accel_std_mad=("accel_std", mad),
        gyro_std_median=("gyro_std", "median"), gyro_std_mad=("gyro_std", mad),
    )
    baseline["accel_std_mad"] = baseline["accel_std_mad"].clip(lower=0.01)
    baseline["gyro_std_mad"] = baseline["gyro_std_mad"].clip(lower=0.01)
    ev = ev.join(baseline, on="speed_band")

    ev["accel_score"] = (ev["accel_std"] - ev["accel_std_median"]) / (1.4826 * ev["accel_std_mad"])
    ev["gyro_score"] = (ev["gyro_std"] - ev["gyro_std_median"]) / (1.4826 * ev["gyro_std_mad"])

    valid = ev[["accel_std", "accel_max", "gyro_std", "gyro_max", "accel_score", "gyro_score", "speed"]].notna().all(axis=1)
    ev["candidate"] = (
        valid & (ev["speed"] >= MIN_MOVING_SPEED)
        & ((ev["accel_score"] >= CANDIDATE_Z) | (ev["gyro_score"] >= CANDIDATE_Z))
    )

    candidates = ev[ev["candidate"]].sort_values("start")
    merged = []
    if len(candidates) > 0:
        cur = _event_from_window(candidates.iloc[0])
        for i in range(1, len(candidates)):
            row = candidates.iloc[i]
            if float(row["start"]) - cur["end"] <= MAX_GAP_SECONDS:
                cur["end"] = max(cur["end"], float(row["end"]))
                cur["peak_accel"] = max(cur["peak_accel"], float(row["accel_max"]))
                cur["peak_gyro"] = max(cur["peak_gyro"], float(row["gyro_max"]))
                cur["peak_accel_score"] = max(cur["peak_accel_score"], float(row["accel_score"]))
                cur["peak_gyro_score"] = max(cur["peak_gyro_score"], float(row["gyro_score"]))
                cur["speed"] = float(row["speed"])
                cur["speed_band"] = row["speed_band"]
                cur["latitude"] = float(row["latitude"])
                cur["longitude"] = float(row["longitude"])
            else:
                merged.append(cur)
                cur = _event_from_window(row)
        merged.append(cur)

    if not merged:
        return pd.DataFrame(columns=cols)
    result = pd.DataFrame(merged)
    result["duration"] = result["end"] - result["start"]
    result["speed_band"] = result["speed"].apply(speed_band)
    return result[cols]


def score_events(rec: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Impact-shape signature and heuristic impact_score for each candidate event."""
    out = []
    for _, event in events.iterrows():
        start, end = float(event["start"]), float(event["end"])
        e = rec[(rec["seconds_elapsed"] >= start) & (rec["seconds_elapsed"] <= end)]
        e = e.dropna(subset=["seconds_elapsed", "accel_mag", "gyro_mag", "speed"])
        if e.empty:
            continue

        peak_row = e.loc[e["accel_mag"].idxmax()]
        peak_time = float(peak_row["seconds_elapsed"])
        peak_accel = float(peak_row["accel_mag"])
        sec = e["seconds_elapsed"]

        before = e[(sec >= peak_time - 0.15) & (sec < peak_time)]
        after = e[(sec > peak_time) & (sec <= peak_time + 0.15)]

        before_accel = rise_rate = np.nan
        if not before.empty:
            before_accel = float(before["accel_mag"].median())
            dt = peak_time - float(before["seconds_elapsed"].min())
            if dt > 0:
                rise_rate = (peak_accel - before_accel) / dt

        after_accel = fall_rate = np.nan
        if not after.empty:
            after_accel = float(after["accel_mag"].median())
            dt = float(after["seconds_elapsed"].max()) - peak_time
            if dt > 0:
                fall_rate = (peak_accel - after_accel) / dt

        event_median = float(e["accel_mag"].median())
        peak_prominence = peak_accel / event_median if event_median > 0 else np.nan

        above_80 = e[e["accel_mag"] >= peak_accel * 0.80]
        peak_width = (float(above_80["seconds_elapsed"].max()) - float(above_80["seconds_elapsed"].min())
                      if len(above_80) > 0 else 0.0)

        near = e[(sec >= peak_time - 0.15) & (sec <= peak_time + 0.15)]
        peak_gyro_near = float(near["gyro_mag"].max()) if not near.empty else np.nan

        bs = e[(sec >= peak_time - 0.5) & (sec < peak_time - 0.2)]
        as_ = e[(sec > peak_time + 0.2) & (sec <= peak_time + 0.5)]
        if not bs.empty and not as_.empty:
            before_speed = float(bs["speed"].median())
            after_speed = float(as_["speed"].median())
            speed_change = after_speed - before_speed
        else:
            before_speed = after_speed = speed_change = np.nan

        if pd.notna(rise_rate) and pd.notna(fall_rate) and rise_rate > 0 and fall_rate > 0:
            shape_balance = min(rise_rate, fall_rate) / max(rise_rate, fall_rate)
        else:
            shape_balance = np.nan

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

        classification = "STRONG_IMPACT" if score >= 70 else "MODERATE_IMPACT" if score >= 45 else "WEAK_IMPACT"

        out.append({
            "start": start, "end": end, "duration": float(event["duration"]),
            "peak_time": peak_time, "peak_accel": peak_accel, "event_median_accel": event_median,
            "peak_prominence": peak_prominence, "peak_width": peak_width,
            "before_accel": before_accel, "after_accel": after_accel,
            "rise_rate": rise_rate, "fall_rate": fall_rate, "shape_balance": shape_balance,
            "peak_gyro_near": peak_gyro_near, "before_speed": before_speed, "after_speed": after_speed,
            "speed_change": speed_change, "speed": float(event["speed"]), "speed_band": event["speed_band"],
            "latitude": float(event["latitude"]), "longitude": float(event["longitude"]),
            "impact_score": score, "classification": classification,
        })

    df = pd.DataFrame(out)
    if df.empty:
        return df
    return df.sort_values(["impact_score", "peak_accel"], ascending=False).reset_index(drop=True)


def cluster_events(scored: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """30 m spatial clustering of events with impact_score >= 45.

    Returns (hotspots, scored) where scored gains an `id` column and a
    `hotspot_id` column linking each clustered event to its hotspot.
    """
    scored = scored.copy()
    scored.insert(0, "id", range(len(scored)))
    scored["hotspot_id"] = pd.array([None] * len(scored), dtype="object")
    if scored.empty:
        return pd.DataFrame(), scored

    cand = scored[(scored["impact_score"] >= HOTSPOT_MIN_SCORE)].dropna(subset=["latitude", "longitude"]).copy()
    if cand.empty:
        return pd.DataFrame(), scored

    coords = np.radians(cand[["latitude", "longitude"]].values)
    cand["cluster"] = DBSCAN(eps=HOTSPOT_RADIUS_M / EARTH_RADIUS_M, min_samples=1, metric="haversine").fit_predict(coords)

    rows = []
    for cid, g in cand.groupby("cluster"):
        rows.append({
            "id": int(cid), "latitude": g["latitude"].mean(), "longitude": g["longitude"].mean(),
            "event_count": len(g),
            "strong_events": int((g["classification"] == "STRONG_IMPACT").sum()),
            "moderate_events": int((g["classification"] == "MODERATE_IMPACT").sum()),
            "max_impact_score": float(g["impact_score"].max()), "mean_impact_score": float(g["impact_score"].mean()),
            "max_peak_accel": float(g["peak_accel"].max()), "mean_peak_accel": float(g["peak_accel"].mean()),
            "first_event": float(g["start"].min()), "last_event": float(g["end"].max()),
        })
    hotspots = pd.DataFrame(rows).sort_values(["event_count", "max_impact_score"], ascending=False).reset_index(drop=True)
    hotspots["confidence_level"] = hotspots["event_count"].map(confidence_level)
    add_priority(hotspots)

    for idx, cid in cand["cluster"].items():
        scored.at[idx, "hotspot_id"] = int(cid)
    return hotspots, scored


def process_recording(accel: pd.DataFrame, gyro: pd.DataFrame, location: pd.DataFrame) -> dict:
    """Run the full pipeline. Returns DataFrames plus summary counters."""
    rec = prepare_recording(accel, gyro, location)
    candidates = detect_events(rec)
    scored = score_events(rec, candidates)
    hotspots, scored = cluster_events(scored)
    return {
        "rows_processed": len(rec),
        "duration_seconds": float(rec["seconds_elapsed"].iloc[-1] - rec["seconds_elapsed"].iloc[0]),
        "gps_rows": int(len(location)),
        "events": scored,
        "hotspots": hotspots,
    }
