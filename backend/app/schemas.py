"""Pydantic response models for the RoadPulse API."""
from typing import Literal, Optional

from pydantic import BaseModel


class Event(BaseModel):
    id: int  # 0-based row position in roadpulse_pune_impact_scores.csv
    start: float
    end: float
    duration: float
    peak_time: float
    peak_accel: float
    event_median_accel: Optional[float] = None
    peak_prominence: Optional[float] = None
    peak_width: Optional[float] = None
    before_accel: Optional[float] = None
    after_accel: Optional[float] = None
    rise_rate: Optional[float] = None
    fall_rate: Optional[float] = None
    shape_balance: Optional[float] = None
    peak_gyro_near: Optional[float] = None
    before_speed: Optional[float] = None
    after_speed: Optional[float] = None
    speed_change: Optional[float] = None
    speed: Optional[float] = None
    speed_band: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    impact_score: float
    classification: str
    hotspot_id: Optional[int] = None  # derived, see data_service


class EventList(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Event]


class Hotspot(BaseModel):
    id: int
    latitude: float
    longitude: float
    event_count: int
    strong_events: int
    moderate_events: int
    max_impact_score: float
    mean_impact_score: float
    max_peak_accel: float
    mean_peak_accel: float
    first_event: float
    last_event: float
    # Derived (see data_service): confidence from observation count; priority from impact score + repeats
    confidence_level: str
    risk_level: str


class HotspotDetail(Hotspot):
    events: list[Event]


class HotspotList(BaseModel):
    total: int
    items: list[Hotspot]


class Stats(BaseModel):
    total_events: int
    total_hotspots: int
    strong_events: int
    moderate_events: int
    weak_events: int
    highest_impact_score: float
    events_with_gps: int
    repeated_hotspots: int


class IngestResult(BaseModel):
    """Result of processing one uploaded Sensor Logger recording (one vehicle/trip)."""
    status: Literal["processed", "failed"]
    recording_id: str
    rows_processed: int = 0
    duration_seconds: float = 0.0
    gps_rows: int = 0
    events_detected: int = 0
    hotspots_detected: int = 0
    files_used: list[str] = []
    files_ignored: list[str] = []
    recording_started: Optional[str] = None
    error: Optional[str] = None
    note: str = (
        "Impact events are heuristic prototype detections of potential road anomalies from a single "
        "recording; they are not validated pothole detections or multi-vehicle confirmation."
    )
    events: list[Event] = []
    hotspots: list[Hotspot] = []
