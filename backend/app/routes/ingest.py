from typing import Optional

from fastapi import APIRouter, File, Header, HTTPException, Query, UploadFile

from app.routes.events import call_service
from app.schemas import EventList, HotspotList, IngestResult, Stats
from app.services import data_service as ds
from app.services import ingestion_service as ing

router = APIRouter(prefix="/api", tags=["ingest"])


@router.post("/ingest", response_model=IngestResult)
def ingest(
    accelerometer: Optional[UploadFile] = File(None, description="Accelerometer.csv (required)"),
    gyroscope: Optional[UploadFile] = File(None, description="Gyroscope.csv (required)"),
    location: Optional[UploadFile] = File(None, description="Location.csv (required)"),
    total_acceleration: Optional[UploadFile] = File(None, description="TotalAcceleration.csv (optional)"),
    metadata: Optional[UploadFile] = File(None, description="Metadata.csv (optional)"),
    x_upload_key: Optional[str] = Header(None, description="Optional idempotency key: a repeated key returns the original recording instead of creating a duplicate"),
):
    """Upload a Sensor Logger recording and process it synchronously."""
    try:
        return ing.ingest({
            "accelerometer": accelerometer,
            "gyroscope": gyroscope,
            "location": location,
            "total_acceleration": total_acceleration,
            "metadata": metadata,
        }, x_upload_key)
    except ing.IngestError as exc:
        raise HTTPException(exc.status_code, exc.message)


@router.get("/ingest/{recording_id}", response_model=IngestResult)
def get_ingest(recording_id: str):
    try:
        return ing.get_result(recording_id)
    except ing.IngestError as exc:
        raise HTTPException(exc.status_code, exc.message)


# Dashboard-shaped views of a processed recording (read from the saved result, never re-processed)
@router.get("/ingest/{recording_id}/events", response_model=EventList)
def recording_events(
    recording_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    classification: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None, ge=0, le=100),
):
    return call_service(ds.list_events, limit, offset, classification, min_score, recording_id)


@router.get("/ingest/{recording_id}/hotspots", response_model=HotspotList)
def recording_hotspots(recording_id: str):
    return call_service(ds.list_hotspots, recording_id)


@router.get("/ingest/{recording_id}/stats", response_model=Stats)
def recording_stats(recording_id: str):
    return call_service(ds.get_stats, recording_id)
