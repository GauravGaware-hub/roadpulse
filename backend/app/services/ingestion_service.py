"""Receive a Sensor Logger recording, store it, process it, persist the result.

Layout per recording:  backend/uploads/<recording_id>/
    Accelerometer.csv, Gyroscope.csv, Location.csv   raw sensor data (needed to reproduce results)
    result.json                                      processing result (or a failed-status record)

Privacy: uploads are saved under fixed names (never the client's filenames),
Metadata.csv is read only for the recording start time and is NOT stored (it holds a device id),
and TotalAcceleration.csv is validated but not stored because the pipeline does not use it.
"""
import json
import shutil
import uuid
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import UploadFile

from app.services import data_service as ds
from app.services.processing_service import ProcessingError, process_recording

UPLOADS_DIR = ds.UPLOADS_DIR  # single definition lives in data_service (env: UPLOADS_DIR)
MAX_FILE_BYTES = 200 * 1024 * 1024  # per file

# form field -> (canonical file name, required?)
FIELDS = {
    "accelerometer": ("Accelerometer.csv", True),
    "gyroscope": ("Gyroscope.csv", True),
    "location": ("Location.csv", True),
    "total_acceleration": ("TotalAcceleration.csv", False),
    "metadata": ("Metadata.csv", False),
}
STORED = {"accelerometer", "gyroscope", "location"}


class IngestError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def _save_upload(upload: UploadFile, dest: Path, label: str) -> None:
    size = 0
    with dest.open("wb") as out:
        while chunk := upload.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise IngestError(413, f"{label} is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB")
            out.write(chunk)
    if size == 0:
        raise IngestError(400, f"{label} is empty")


def _read_csv(path: Path, label: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
    except Exception:
        raise IngestError(422, f"{label} is not a valid CSV file")
    if df.empty:
        raise IngestError(422, f"{label} contains no data rows")
    return df


def _write_result(rec_dir: Path, payload: dict) -> None:
    (rec_dir / "result.json").write_text(json.dumps(payload), encoding="utf-8")


def ingest(files: dict[str, Optional[UploadFile]]) -> dict:
    """files maps form-field name -> upload (None when not provided)."""
    provided = {k: f for k, f in files.items() if f is not None and f.filename}
    missing = [FIELDS[k][0] for k, (_, req) in FIELDS.items() if req and k not in provided]
    if missing:
        raise IngestError(400, f"Missing required file(s): {', '.join(missing)}")

    recording_id = str(uuid.uuid4())
    rec_dir = UPLOADS_DIR / recording_id
    rec_dir.mkdir(parents=True)
    used, ignored, started = [], [], None
    try:
        # Store required sensor files
        for key in STORED:
            name = FIELDS[key][0]
            _save_upload(provided[key], rec_dir / name, name)
            used.append(name)

        # Optional files: validated, not stored
        if "total_acceleration" in provided:
            tmp = rec_dir / "_tmp.csv"
            _save_upload(provided["total_acceleration"], tmp, "TotalAcceleration.csv")
            cols = pd.read_csv(tmp, nrows=1).columns
            tmp.unlink()
            if "seconds_elapsed" not in cols:
                raise IngestError(422, "TotalAcceleration.csv is missing required column(s): seconds_elapsed")
            ignored.append("TotalAcceleration.csv (not used by the current pipeline)")
        if "metadata" in provided:
            tmp = rec_dir / "_tmp.csv"
            _save_upload(provided["metadata"], tmp, "Metadata.csv")
            try:
                meta = pd.read_csv(tmp)
                started = str(meta["recording time"].iloc[0]) if "recording time" in meta.columns else None
            except Exception:
                tmp.unlink()
                raise IngestError(422, "Metadata.csv is not a valid CSV file")
            tmp.unlink()
            ignored.append("Metadata.csv (only the recording start time is kept)")

        accel = _read_csv(rec_dir / "Accelerometer.csv", "Accelerometer.csv")
        gyro = _read_csv(rec_dir / "Gyroscope.csv", "Gyroscope.csv")
        loc = _read_csv(rec_dir / "Location.csv", "Location.csv")
        out = process_recording(accel, gyro, loc)
    except (IngestError, ProcessingError) as exc:
        status = exc.status_code if isinstance(exc, IngestError) else 422
        message = exc.message if isinstance(exc, IngestError) else str(exc)
        _write_result(rec_dir, {"status": "failed", "recording_id": recording_id, "error": message})
        raise IngestError(status, message)
    except Exception:
        # Unexpected failure: keep details out of the API response
        _write_result(rec_dir, {"status": "failed", "recording_id": recording_id, "error": "Processing failed"})
        raise IngestError(500, "Processing failed due to an internal error")

    events = ds.records(out["events"]) if len(out["events"]) else []
    hotspots = ds.records(out["hotspots"]) if len(out["hotspots"]) else []
    result = {
        "status": "processed",
        "recording_id": recording_id,
        "rows_processed": out["rows_processed"],
        "duration_seconds": out["duration_seconds"],
        "gps_rows": out["gps_rows"],
        "events_detected": len(events),
        "hotspots_detected": len(hotspots),
        "files_used": used,
        "files_ignored": ignored,
        "recording_started": started,
        "events": events,
        "hotspots": hotspots,
    }
    _write_result(rec_dir, result)
    return result


def get_result(recording_id: str) -> dict:
    try:
        rid = str(uuid.UUID(recording_id))  # also blocks path traversal
    except ValueError:
        raise IngestError(400, "Invalid recording id")
    path = UPLOADS_DIR / rid / "result.json"
    if not path.exists():
        raise IngestError(404, f"Recording {rid} not found")
    return json.loads(path.read_text(encoding="utf-8"))


def delete_recording(recording_id: str) -> None:
    """Helper for tests/cleanup."""
    shutil.rmtree(UPLOADS_DIR / str(uuid.UUID(recording_id)), ignore_errors=True)
