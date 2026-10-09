"""API tests: static dataset, hotspot priority rule, and the upload (ingest) flow.

Run from backend/:   python -m pytest tests -q
The real-recording test is skipped automatically when the (git-ignored) recording folder is absent.
"""
import io
import math
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import data_service as ds
from app.services import ingestion_service as ing

ROOT = Path(__file__).resolve().parents[2]
REAL = ROOT / "Vakratund_Colony-2026-10-06_12-32-23"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # isolate uploads from the real backend/uploads folder
    monkeypatch.setattr(ds, "UPLOADS_DIR", tmp_path)
    monkeypatch.setattr(ing, "UPLOADS_DIR", tmp_path)
    ds._load_recording.cache_clear()
    return TestClient(app)


def csv_bytes(header: str, rows) -> bytes:
    buf = io.StringIO()
    buf.write(header + "\n")
    for r in rows:
        buf.write(",".join(str(v) for v in r) + "\n")
    return buf.getvalue().encode()


def synthetic(seconds=60, hz=100):
    """A short synthetic drive: 8 m/s with two sharp spikes. Not real data."""
    rng = np.random.default_rng(0)
    n = seconds * hz
    t = np.arange(n) / hz + 0.5
    z = 9.8 + rng.normal(0, 0.15, n)
    for t0 in (20.0, 40.0):
        z += 18 * np.exp(-(((t - t0) / 0.05) ** 2))
    acc = csv_bytes("time,seconds_elapsed,z,y,x", [(0, t[i], z[i], 0.1, 0.1) for i in range(n)])
    gyr = csv_bytes("time,seconds_elapsed,z,y,x", [(0, t[i], 0.02, 0.02, 0.02) for i in range(n)])
    gt = np.arange(0, seconds + 1)
    loc = csv_bytes(
        "time,seconds_elapsed,speed,latitude,longitude",
        [(0, gt[i] + 0.6, 8.0, 18.5 + i * 7.2e-5, 73.8) for i in range(len(gt))],
    )
    return acc, gyr, loc


def files(acc, gyr, loc, **extra):
    d = {
        "accelerometer": ("Accelerometer.csv", acc, "text/csv"),
        "gyroscope": ("Gyroscope.csv", gyr, "text/csv"),
        "location": ("Location.csv", loc, "text/csv"),
    }
    d.update(extra)
    return d


# ---------------- static dataset ----------------
def test_root_and_health(client):
    assert client.get("/").json()["status"] == "running"
    assert client.get("/api/health").json() == {"status": "healthy", "service": "roadpulse-api"}


def test_static_stats_unchanged(client):
    s = client.get("/api/stats").json()
    assert (s["total_events"], s["total_hotspots"], s["strong_events"], s["moderate_events"], s["weak_events"], s["repeated_hotspots"]) == (50, 39, 26, 20, 4, 5)


def test_static_hotspot_priority_counts(client):
    items = client.get("/api/hotspots").json()["items"]
    counts = {k: sum(h["risk_level"] == k for h in items) for k in ("HIGH", "MEDIUM", "LOW")}
    assert counts == {"HIGH": 5, "MEDIUM": 12, "LOW": 22}


@pytest.mark.parametrize(
    "score,n,expected",
    [(90, 1, "MEDIUM"), (90, 2, "HIGH"), (80, 2, "HIGH"), (70, 2, "MEDIUM"), (70, 1, "LOW"), (59, 5, "LOW"), (45, 1, "LOW")],
)
def test_priority_rule(score, n, expected):
    assert ds.risk_level(score, n) == expected


def test_hotspot_detail_and_coordinates_unchanged(client):
    h = client.get("/api/hotspots/3").json()
    assert math.isclose(h["latitude"], 18.678510966666664) and math.isclose(h["longitude"], 73.83767513333333)
    assert len(h["events"]) == h["event_count"]


def test_event_filters_and_errors(client):
    assert client.get("/api/events?classification=STRONG_IMPACT&limit=500").json()["total"] == 26
    assert client.get("/api/events/999").status_code == 404
    assert client.get("/api/events?limit=0").status_code == 422
    assert client.get("/api/stats?recording_id=not-a-uuid").status_code == 400
    assert client.get("/api/stats?recording_id=00000000-0000-0000-0000-000000000000").status_code == 404


# ---------------- ingest: validation ----------------
def test_missing_required_files(client):
    acc, gyr, loc = synthetic(10)
    r = client.post("/api/ingest", files={"accelerometer": ("Accelerometer.csv", acc, "text/csv")})
    assert r.status_code == 400 and "Gyroscope.csv" in r.json()["detail"] and "Location.csv" in r.json()["detail"]


def test_empty_file_rejected(client):
    acc, gyr, loc = synthetic(10)
    r = client.post("/api/ingest", files=files(b"", gyr, loc))
    assert r.status_code == 400 and "empty" in r.json()["detail"].lower()


def test_wrong_columns_rejected_without_traceback(client):
    acc, gyr, loc = synthetic(10)
    r = client.post("/api/ingest", files=files(loc, gyr, loc))  # Location.csv uploaded as accelerometer
    assert r.status_code == 422
    assert "missing required column" in r.json()["detail"] and "Traceback" not in r.text


def test_garbage_csv_rejected(client):
    r = client.post("/api/ingest", files=files(b"hello\n", b"hello\n", b"hello\n"))
    assert r.status_code == 422


def test_too_short_recording_rejected(client):
    acc, gyr, loc = synthetic(3)
    r = client.post("/api/ingest", files=files(acc, gyr, loc))
    assert r.status_code == 422


def test_failed_upload_keeps_no_raw_csv(client, tmp_path):
    client.post("/api/ingest", files=files(b"hello\n", b"hello\n", b"hello\n"))
    leftovers = [p for p in tmp_path.rglob("*.csv")]
    assert leftovers == []


# ---------------- ingest: success path ----------------
def test_synthetic_recording_end_to_end(client):
    acc, gyr, loc = synthetic(60)
    r = client.post("/api/ingest", files=files(acc, gyr, loc))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "processed" and body["rows_processed"] > 5000
    assert body["events_detected"] == len(body["events"]) >= 1
    assert body["hotspots_detected"] == len(body["hotspots"])
    rid = body["recording_id"]
    # the same result is retrievable, and served through the dashboard endpoints
    assert client.get(f"/api/ingest/{rid}").json()["events_detected"] == body["events_detected"]
    assert client.get(f"/api/stats?recording_id={rid}").json()["total_events"] == body["events_detected"]
    assert client.get(f"/api/ingest/{rid}/hotspots").json()["total"] == body["hotspots_detected"]
    # static dataset is unaffected
    assert client.get("/api/stats").json()["total_events"] == 50


def test_each_upload_gets_its_own_recording_id(client):
    acc, gyr, loc = synthetic(30)
    a = client.post("/api/ingest", files=files(acc, gyr, loc)).json()["recording_id"]
    b = client.post("/api/ingest", files=files(acc, gyr, loc)).json()["recording_id"]
    assert a != b


def test_optional_files_validated_and_not_stored(client, tmp_path):
    acc, gyr, loc = synthetic(30)
    meta = csv_bytes("version,device name,recording time,device id", [(3, "X", "2026-10-06_12-32-23", "secret-device-id")])
    tot = csv_bytes("time,seconds_elapsed,z,y,x", [(0, 0.5, 9.8, 0, 0)])
    r = client.post("/api/ingest", files=files(acc, gyr, loc, metadata=("Metadata.csv", meta, "text/csv"), total_acceleration=("TotalAcceleration.csv", tot, "text/csv")))
    assert r.status_code == 200
    rid = r.json()["recording_id"]
    assert r.json()["recording_started"] == "2026-10-06_12-32-23"
    stored = sorted(p.name for p in (tmp_path / rid).iterdir())
    assert stored == ["Accelerometer.csv", "Gyroscope.csv", "Location.csv", "result.json"]  # no device id kept
    assert "secret-device-id" not in (tmp_path / rid / "result.json").read_text()


def test_stale_saved_result_follows_current_priority_rule(client, tmp_path):
    acc, gyr, loc = synthetic(60)
    rid = client.post("/api/ingest", files=files(acc, gyr, loc)).json()["recording_id"]
    import json
    p = tmp_path / rid / "result.json"
    d = json.loads(p.read_text())
    for h in d["hotspots"]:
        h["risk_level"] = "HIGH"
    p.write_text(json.dumps(d))
    ds._load_recording.cache_clear()
    for h in client.get(f"/api/hotspots?recording_id={rid}").json()["items"]:
        assert h["risk_level"] == ds.risk_level(h["max_impact_score"], h["event_count"])


@pytest.mark.skipif(not REAL.exists(), reason="real recording folder not present")
def test_real_pune_recording(client):
    fs = {k: (f"{n}.csv", (REAL / f"{n}.csv").read_bytes(), "text/csv") for k, n in (("accelerometer", "Accelerometer"), ("gyroscope", "Gyroscope"), ("location", "Location"))}
    r = client.post("/api/ingest", files=fs)
    assert r.status_code == 200
    b = r.json()
    assert (b["rows_processed"], b["events_detected"], b["hotspots_detected"]) == (134468, 50, 39)


# ---------------- ingest: idempotency (no duplicate recordings on retry) ----------------
def test_same_upload_key_returns_original_recording(client, tmp_path):
    acc, gyr, loc = synthetic(30)
    h = {"X-Upload-Key": "key-abc"}
    a = client.post("/api/ingest", files=files(acc, gyr, loc), headers=h).json()
    b = client.post("/api/ingest", files=files(acc, gyr, loc), headers=h).json()
    assert a["recording_id"] == b["recording_id"]
    assert b["events_detected"] == a["events_detected"]
    assert len([p for p in tmp_path.iterdir() if p.is_dir()]) == 1  # one recording on disk, not two


def test_different_or_missing_key_creates_new_recording(client, tmp_path):
    acc, gyr, loc = synthetic(30)
    ids = {
        client.post("/api/ingest", files=files(acc, gyr, loc), headers={"X-Upload-Key": "k1"}).json()["recording_id"],
        client.post("/api/ingest", files=files(acc, gyr, loc), headers={"X-Upload-Key": "k2"}).json()["recording_id"],
        client.post("/api/ingest", files=files(acc, gyr, loc)).json()["recording_id"],
    }
    assert len(ids) == 3


def test_failed_upload_does_not_poison_its_key(client):
    acc, gyr, loc = synthetic(30)
    h = {"X-Upload-Key": "retry-me"}
    assert client.post("/api/ingest", files=files(b"hello\n", gyr, loc), headers=h).status_code == 422
    ok = client.post("/api/ingest", files=files(acc, gyr, loc), headers=h)  # corrected files, same key
    assert ok.status_code == 200 and ok.json()["status"] == "processed"


def test_concurrent_duplicate_requests_create_one_recording(client, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    acc, gyr, loc = synthetic(30)
    def go(_):
        return TestClient(app).post("/api/ingest", files=files(acc, gyr, loc), headers={"X-Upload-Key": "race"}).json()["recording_id"]
    with ThreadPoolExecutor(4) as ex:
        ids = set(ex.map(go, range(4)))
    assert len(ids) == 1
    assert len([p for p in tmp_path.iterdir() if p.is_dir()]) == 1


# ---------------- ingest: processing lock + key bookkeeping ----------------
def test_only_one_recording_is_processed_at_a_time(client, monkeypatch):
    import threading, time
    from concurrent.futures import ThreadPoolExecutor
    real = ing.process_recording
    state = {"now": 0, "max": 0}
    guard = threading.Lock()

    def counted(*a, **k):
        with guard:
            state["now"] += 1
            state["max"] = max(state["max"], state["now"])
        time.sleep(0.3)
        try:
            return real(*a, **k)
        finally:
            with guard:
                state["now"] -= 1

    monkeypatch.setattr(ing, "process_recording", counted)
    acc, gyr, loc = synthetic(30)

    def go(i):
        return TestClient(app).post("/api/ingest", files=files(acc, gyr, loc), headers={"X-Upload-Key": f"lock-{i}"}).status_code

    with ThreadPoolExecutor(4) as ex:
        codes = list(ex.map(go, range(4)))
    assert codes == [200] * 4
    assert state["max"] == 1  # simultaneous uploads queued instead of running together


def test_key_eviction_is_bounded_and_never_drops_a_held_lock(monkeypatch):
    import threading
    monkeypatch.setattr(ing, "_KEY_MAX", 3)
    monkeypatch.setattr(ing, "_KEY_LOCKS", {})
    monkeypatch.setattr(ing, "_KEY_RESULTS", {})
    held = threading.Lock()
    held.acquire()  # simulates the oldest key still being processed
    ing._KEY_LOCKS["in-flight"] = held
    for i in range(6):
        ing._KEY_LOCKS[f"k{i}"] = threading.Lock()
        ing._KEY_RESULTS[f"k{i}"] = f"rec{i}"
        ing._evict_keys()
    assert "in-flight" in ing._KEY_LOCKS          # held lock survived
    assert len(ing._KEY_LOCKS) <= 3
    assert set(ing._KEY_RESULTS) <= set(ing._KEY_LOCKS)  # results evicted together with their locks
