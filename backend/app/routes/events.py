from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas import Event, EventList, Stats
from app.services import data_service as ds

router = APIRouter(prefix="/api", tags=["events"])

# Omitted -> static Pune research dataset; given -> that uploaded recording's processed result
RecordingId = Query(None, description="Uploaded recording UUID. Omit for the static Pune dataset.")


def call_service(fn, *args):
    """Map data-service errors to HTTP errors (no tracebacks leak to clients)."""
    try:
        return fn(*args)
    except ds.BadRequest as exc:
        raise HTTPException(400, str(exc))
    except ds.NotFound as exc:
        raise HTTPException(404, str(exc))
    except ds.DataUnavailable as exc:
        raise HTTPException(503, str(exc))


@router.get("/events", response_model=EventList)
def list_events(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    classification: Optional[str] = Query(None, description="STRONG_IMPACT, MODERATE_IMPACT or WEAK_IMPACT"),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    recording_id: Optional[str] = RecordingId,
):
    return call_service(ds.list_events, limit, offset, classification, min_score, recording_id)


@router.get("/events/{event_id}", response_model=Event)
def get_event(event_id: int, recording_id: Optional[str] = RecordingId):
    return call_service(ds.get_event, event_id, recording_id)


@router.get("/stats", response_model=Stats)
def stats(recording_id: Optional[str] = RecordingId):
    return call_service(ds.get_stats, recording_id)
