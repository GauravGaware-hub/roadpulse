from typing import Optional

from fastapi import APIRouter

from app.routes.events import RecordingId, call_service
from app.schemas import HotspotDetail, HotspotList
from app.services import data_service as ds

router = APIRouter(prefix="/api", tags=["hotspots"])


@router.get("/hotspots", response_model=HotspotList)
def list_hotspots(recording_id: Optional[str] = RecordingId):
    return call_service(ds.list_hotspots, recording_id)


@router.get("/hotspots/{hotspot_id}", response_model=HotspotDetail)
def get_hotspot(hotspot_id: int, recording_id: Optional[str] = RecordingId):
    return call_service(ds.get_hotspot, hotspot_id, recording_id)
