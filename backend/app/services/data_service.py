"""CSV-backed data service for the prototype.

Routes only call the public functions here, so this module can later be
swapped for a PostgreSQL/PostGIS implementation without touching the API.
"""
import json
import math
import os
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from app.schemas import Event, Hotspot

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "processed"
EVENTS_CSV = PROCESSED_DIR / "roadpulse_pune_impact_scores.csv"
HOTSPOTS_CSV = PROCESSED_DIR / "roadpulse_pune_impact_clusters.csv"

# Hotspots were built from events with impact_score >= 45 (cluster_pune_impacts.py).
HOTSPOT_MIN_SCORE = 45
# Events are linked to the nearest hotspot centroid within this distance (metres).
# Hotspots use 30 m single-linkage clustering, so centroids can sit a bit further out.
LINK_RADIUS_M = 60

# Uploaded recordings live in backend/uploads/<uuid>/result.json (written by ingestion_service)
# Override with UPLOADS_DIR (e.g. a mounted persistent disk) in deployment.
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR") or Path(__file__).resolve().parents[2] / "uploads")


class DataUnavailable(Exception):
    """A required data file is missing or unreadable."""


class NotFound(Exception):
    """Requested record does not exist."""


class BadRequest(Exception):
    """Malformed request parameter (e.g. an invalid recording id)."""


def _clean(value):
    """Convert numpy/NaN values to JSON-safe Python values."""
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def records(df: pd.DataFrame) -> list[dict]:
    return [{k: _clean(v) for k, v in row.items()} for row in df.to_dict("records")]


def _read(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise DataUnavailable(f"Data file not found: {path.name}")
    try:
        return pd.read_csv(path)
    except Exception as exc:
        raise DataUnavailable(f"Could not read {path.name}") from exc


def _haversine_m(lat, lon, lats, lons):
    lat, lon, lats, lons = map(np.radians, (lat, lon, lats, lons))
    a = np.sin((lats - lat) / 2) ** 2 + np.cos(lat) * np.cos(lats) * np.sin((lons - lon) / 2) ** 2
    return 2 * 6371000 * np.arcsin(np.sqrt(a))


def confidence_level(event_count: int) -> str:
    # More passes over the same spot -> higher confidence
    return "HIGH" if event_count >= 3 else "MEDIUM" if event_count == 2 else "LOW"


def risk_level(max_score: float, event_count: int) -> str:
    """Inspection priority: impact severity AND repeated observations (prototype heuristic).

    HIGH   (priority inspection): max impact score >= 80 and 2+ observations
    MEDIUM (inspect):             score >= 80 with a single observation, or score >= 60 with 2+ observations
    LOW    (monitor):             everything else (single moderate/weak observations, weak repeats)
    No independent-recording count exists in the data (one trip), so it is not used.
    """
    repeated = event_count >= 2
    if max_score >= 80 and repeated:
        return "HIGH"
    if max_score >= 80 or (max_score >= 60 and repeated):
        return "MEDIUM"
    return "LOW"


def add_priority(hotspots: pd.DataFrame) -> pd.DataFrame:
    """Add risk_level (priority) to a hotspot frame from its score and observation count."""
    hotspots["risk_level"] = [risk_level(s, n) for s, n in zip(hotspots["max_impact_score"], hotspots["event_count"])]
    return hotspots


# Loaded once per process; restart the server to pick up regenerated CSVs.
# Exceptions are not cached by lru_cache, so a file added later is picked up.
@lru_cache(maxsize=1)
def _load() -> tuple[pd.DataFrame, pd.DataFrame]:
    events = _read(EVENTS_CSV)
    hotspots = _read(HOTSPOTS_CSV)

    events.insert(0, "id", range(len(events)))

    hotspots = hotspots.rename(columns={"cluster_id": "id"})
    hotspots["confidence_level"] = hotspots["event_count"].map(confidence_level)
    add_priority(hotspots)

    # Derive event -> hotspot link (nearest centroid) for candidate events with GPS
    hotspot_ids = []
    h_lat = hotspots["latitude"].to_numpy()
    h_lon = hotspots["longitude"].to_numpy()
    for row in events.itertuples():
        hid = None
        if row.impact_score >= HOTSPOT_MIN_SCORE and not pd.isna(row.latitude):
            d = _haversine_m(row.latitude, row.longitude, h_lat, h_lon)
            j = int(np.argmin(d))
            if d[j] <= LINK_RADIUS_M:
                hid = int(hotspots["id"].iloc[j])
        hotspot_ids.append(hid)
    events["hotspot_id"] = pd.Series(hotspot_ids, dtype="object")
    return events, hotspots


# Uploaded recordings are read from the result.json saved at ingestion time;
# the processing pipeline is never re-run. The cache survives only until restart,
# but result.json stays on disk, so the recording is simply reloaded on demand.
@lru_cache(maxsize=8)
def _load_recording(rid: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    path = UPLOADS_DIR / rid / "result.json"
    if not path.exists():
        raise NotFound(f"Recording {rid} not found")
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DataUnavailable(f"Could not read result for recording {rid}") from exc
    if result.get("status") != "processed":
        raise NotFound(f"Recording {rid} has no processed result")

    events = pd.DataFrame(result.get("events", []), columns=list(Event.model_fields))
    hotspots = pd.DataFrame(result.get("hotspots", []), columns=list(Hotspot.model_fields))
    add_priority(hotspots)  # recompute so recordings saved earlier follow the current priority rule
    events["hotspot_id"] = pd.Series([None if pd.isna(v) else int(v) for v in events["hotspot_id"]],
                                     index=events.index, dtype="object")
    return events, hotspots


def _frames(recording_id: Optional[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(events, hotspots) for the static Pune dataset, or for an uploaded recording."""
    if recording_id is None:
        return _load()
    try:
        rid = str(uuid.UUID(recording_id))  # also blocks path traversal
    except ValueError:
        raise BadRequest("Invalid recording id")
    return _load_recording(rid)


def list_events(limit: int, offset: int, classification: Optional[str], min_score: Optional[float],
                recording_id: Optional[str] = None) -> dict:
    events, _ = _frames(recording_id)
    df = events
    if classification:
        df = df[df["classification"].str.upper() == classification.upper()]
    if min_score is not None:
        df = df[df["impact_score"] >= min_score]
    return {"total": len(df), "limit": limit, "offset": offset,
            "items": records(df.iloc[offset:offset + limit])}


def get_event(event_id: int, recording_id: Optional[str] = None) -> dict:
    events, _ = _frames(recording_id)
    if event_id < 0 or event_id >= len(events):
        raise NotFound(f"Event {event_id} not found")
    return records(events.iloc[[event_id]])[0]


def list_hotspots(recording_id: Optional[str] = None) -> dict:
    _, hotspots = _frames(recording_id)
    df = hotspots.sort_values(["event_count", "max_impact_score"], ascending=False)
    return {"total": len(df), "items": records(df)}


def get_hotspot(hotspot_id: int, recording_id: Optional[str] = None) -> dict:
    events, hotspots = _frames(recording_id)
    match = hotspots[hotspots["id"] == hotspot_id]
    if match.empty:
        raise NotFound(f"Hotspot {hotspot_id} not found")
    hotspot = records(match)[0]
    hotspot["events"] = records(events[events["hotspot_id"] == hotspot_id])
    return hotspot


def get_stats(recording_id: Optional[str] = None) -> dict:
    events, hotspots = _frames(recording_id)
    cls = events["classification"]
    return {
        "total_events": len(events),
        "total_hotspots": len(hotspots),
        "strong_events": int((cls == "STRONG_IMPACT").sum()),
        "moderate_events": int((cls == "MODERATE_IMPACT").sum()),
        "weak_events": int((cls == "WEAK_IMPACT").sum()),
        "highest_impact_score": float(events["impact_score"].max()) if len(events) else 0.0,
        "events_with_gps": int(events[["latitude", "longitude"]].notna().all(axis=1).sum()),
        "repeated_hotspots": int((hotspots["event_count"] >= 2).sum()),
    }
