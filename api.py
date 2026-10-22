"""
api.py
======
FastAPI backend for the Forest Intrusion Detection System React dashboard.

This module wraps the existing src/ Python modules (EventLogger, AlertEngine,
Detector, EvidenceStore) behind a clean REST + WebSocket API.  It does NOT
replace or modify any of those modules.

Routes
------
  GET  /api/health
  GET  /api/dashboard/summary
  GET  /api/incidents
  GET  /api/incidents/{event_id}
  GET  /api/incidents/{event_id}/images
  GET  /api/poles
  GET  /api/cameras/discover
  GET  /api/monitor/status
  GET  /api/monitor/stream
  POST /api/monitor/start
  POST /api/monitor/stop
  PATCH /api/incidents/{event_id}
  GET  /api/incidents/{event_id}/evidence
  GET  /api/devices
  GET  /api/devices/{pole_id}
  GET  /api/analytics/detections
  GET  /api/model/metrics
  POST /api/detect/image
  POST /api/detect/video
  WS   /ws

Run
---
    pip install fastapi uvicorn[standard] python-multipart aiofiles
    uvicorn api:app --reload --host 0.0.0.0 --port 8000

CORS is configured to allow the Vite dev server on port 5173.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ── Path setup ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import (
    FastAPI, HTTPException, Query, UploadFile, File, WebSocket,
    WebSocketDisconnect, status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.config import Settings
from src.event_logger import EventLogger
from src.alert_engine import AlertEngine

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("forest_api")

# ── Application setup ─────────────────────────────────────────────────────────
app = FastAPI(
    title="Forest Intrusion Detection API",
    description="REST + WebSocket API for the Forest Intrusion Detection System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://127.0.0.1:5173",
        "http://localhost:4173",   # Vite preview
        os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Shared resources (initialised once on startup) ────────────────────────────
cfg            = Settings()
event_logger   = None
database_error = None
try:
    event_logger = EventLogger(evidence_dir=cfg.evidence_dir, uri=cfg.mongodb_uri,
                               database_name=cfg.mongodb_database)
except Exception as exc:
    database_error = str(exc)
alert_engine   = AlertEngine(firearm_conf_threshold=cfg.firearm_alert_threshold)
live_monitor = None
_event_loop: asyncio.AbstractEventLoop | None = None

# Serve evidence images as static files
EVIDENCE_DIR = cfg.evidence_dir
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/evidence", StaticFiles(directory=str(EVIDENCE_DIR)), name="evidence")

@app.middleware("http")
async def require_mongodb(request, call_next):
    db_free = {"/api/health", "/api/cameras/discover", "/api/monitor/status"}
    if request.url.path.startswith("/api/") and request.url.path not in db_free and event_logger is None:
        return JSONResponse(status_code=503, content={"detail": f"MongoDB unavailable: {database_error}"})
    return await call_next(request)

# ── WebSocket connection manager ──────────────────────────────────────────────

class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)
        logger.info("WS client connected (%d total)", len(self.active))

    def disconnect(self, ws: WebSocket) -> None:
        self.active = [c for c in self.active if c is not ws]
        logger.info("WS client disconnected (%d remaining)", len(self.active))

    async def broadcast(self, data: dict) -> None:
        dead: list[WebSocket] = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


ws_manager = ConnectionManager()

# ── Pydantic models ───────────────────────────────────────────────────────────

class PatchIncidentRequest(BaseModel):
    review_status: str                    # "pending" | "reviewed" | "dismissed"
    operator_notes: Optional[str] = None


# ── Helper: broadcast new events to all WS clients ───────────────────────────

async def _broadcast_event(event: dict) -> None:
    await ws_manager.broadcast({"type": "new_detection", "data": event})


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health() -> dict:
    """System health check."""
    model_ready = cfg.model_weights.exists()
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_ready": model_ready,
        "model_path": str(cfg.model_weights),
        "database": cfg.mongodb_database,
        "database_connected": event_logger is not None,
        "database_error": database_error,
        "version": "1.0.0",
    }


@app.get("/api/dashboard/summary")
def dashboard_summary() -> dict:
    """Aggregate summary for the Command Centre page."""
    counts = event_logger.count_by_class()
    total  = event_logger.count_events()

    # Events in the last 24 h
    all_recent = event_logger.get_recent_events(limit=500)
    now_ts = datetime.now(timezone.utc)

    def _age_h(ev: dict) -> float:
        try:
            ts = datetime.fromisoformat(ev["server_ts"])
            return (now_ts - ts).total_seconds() / 3600
        except Exception:
            return 9999

    today = [e for e in all_recent if _age_h(e) <= 24]
    high_count = event_logger.count_events({"alert_priority": {"$in": ["high", "critical"]}})
    pending = [e for e in all_recent if e["review_status"] == "pending"]

    return {
        "total_events_all_time": total,
        "total_events_today": len(today),
        "high_priority_count": high_count,
        "pending_review_count": len(pending),
        "class_breakdown": counts,
        "model_ready": cfg.model_weights.exists(),
        "recent_events": all_recent[:10],
    }


@app.get("/api/incidents")
def list_incidents(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    class_name: Optional[str] = Query(None),
    alert_priority: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    pole_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    segment_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
) -> dict:
    """
    Paginated, filterable list of detection events.

    All filters are AND-combined. ``search`` matches against pole_id,
    camera_id, class_name, and alert_label.
    """
    events = event_logger.query_events(
        class_name=class_name,
        priority=alert_priority,
        pole_id=pole_id,
        start=_normalize_date_filter(start_date),
        end=_normalize_date_filter(end_date),
        limit=5000,
    )

    if review_status:
        events = [e for e in events if e["review_status"] == review_status]
    if segment_id:
        events = [e for e in events if e.get("segment_id") == segment_id]
    if search:
        q = search.lower()
        events = [
            e for e in events
            if q in (e.get("pole_id") or "").lower()
            or q in (e.get("camera_id") or "").lower()
            or q in (e.get("class_name") or "").lower()
            or q in (e.get("alert_label") or "").lower()
        ]

    total = len(events)
    page  = events[offset: offset + limit]

    # Rewrite evidence_path to a URL the frontend can fetch
    for ev in page:
        ev["evidence_url"] = _evidence_url(ev.get("evidence_path"))

    return {"total": total, "offset": offset, "limit": limit, "items": page}


@app.get("/api/incidents/{event_id}")
def get_incident(event_id: str) -> dict:
    event = event_logger.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event["evidence_url"] = _evidence_url(event.get("evidence_path"))
    return event


@app.get("/api/incidents/{event_id}/images")
def get_event_images(event_id: str) -> list[dict]:
    if not event_logger.get_event(event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    return [{"event_id": event_id, "sequence": image["sequence"],
             "capture_timestamp": image["capture_timestamp"], "mime_type": image["mime_type"],
             "size_bytes": image["size_bytes"],
             "url": f"/api/incidents/{event_id}/images/{image['sequence']}"}
            for image in event_logger.get_event_images(event_id)]


@app.get("/api/incidents/{event_id}/images/{sequence}")
def get_event_image(event_id: str, sequence: int):
    image = next((x for x in event_logger.get_event_images(event_id) if x["sequence"] == sequence), None)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    path = Path(image["local_path"]).resolve()
    try:
        path.relative_to(EVIDENCE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid image reference")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Evidence image is missing")
    return FileResponse(path, media_type="image/jpeg")


@app.get("/api/poles")
def get_poles() -> list[dict]:
    poles = event_logger.get_poles()
    latest_by_pole = {}
    for event in event_logger.get_recent_events(limit=5000):
        latest_by_pole.setdefault(event.get("pole_id"), event)

    now = datetime.now(timezone.utc)
    for pole in poles:
        latest_event = latest_by_pole.get(pole.get("pole_id"))
        pole["latest_event"] = latest_event
        if latest_event:
            pole["location"] = pole.get("location") or latest_event.get("pole_location")
        if not pole.get("pole_name") and pole.get("pole_id") == cfg.pole_id:
            pole["pole_name"] = cfg.pole_name
        heartbeat = pole.get("last_heartbeat")
        try:
            heartbeat_at = datetime.fromisoformat(heartbeat)
            if heartbeat_at.tzinfo is None:
                heartbeat_at = heartbeat_at.replace(tzinfo=timezone.utc)
            is_online = (
                pole.get("status") == "online"
                and (now - heartbeat_at).total_seconds() <= 15
            )
        except (TypeError, ValueError):
            is_online = False
        pole["online"] = is_online
        pole["status"] = "online" if is_online else "offline"
    return poles


@app.get("/api/cameras/discover")
def camera_discovery(max_index: int = Query(8, ge=1, le=32)) -> list[dict]:
    from src.live_monitor import discover_cameras
    return discover_cameras(max_index=max_index, dshow=(os.name == "nt"))


@app.get("/api/monitor/stream")
def monitor_stream():
    """Stream annotated camera frames as MJPEG for browser <img> elements."""
    monitor = live_monitor
    if monitor is None or not monitor.status().get("running"):
        raise HTTPException(status_code=409, detail="Camera monitoring is not running")

    import cv2

    def frames():
        while True:
            frame = monitor.latest_frame()
            if frame is not None:
                ok, encoded = cv2.imencode(
                    ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 82]
                )
                if ok:
                    image = encoded.tobytes()
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        + f"Content-Length: {len(image)}\r\n\r\n".encode("ascii")
                        + image
                        + b"\r\n"
                    )
            time.sleep(0.1)

    return StreamingResponse(
        frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


def _get_live_monitor():
    global live_monitor
    if live_monitor is None:
        if event_logger is None:
            raise HTTPException(status_code=503, detail=f"MongoDB unavailable: {database_error}")
        if not cfg.model_weights.exists():
            raise HTTPException(status_code=503, detail=f"Model weights not found: {cfg.model_weights}")
        from src.detector import Detector
        from src.live_monitor import LiveMonitor
        detector = Detector(cfg.model_weights, conf=cfg.confidence_threshold, iou=cfg.iou_threshold)
        cfg.class_names = {int(k): str(v) for k, v in detector.class_names.items()}
        live_monitor = LiveMonitor(
            cfg, detector, event_logger, alert_engine, on_event=_publish_monitor_event
        )
    return live_monitor


@app.get("/api/monitor/status")
def monitor_status() -> dict:
    if event_logger is None:
        return {"running": False, "connected": False, "error": database_error}
    if live_monitor is None:
        return {"running": False, "connected": False, "camera_id": cfg.camera_id,
                "camera_index": cfg.camera_index, "message": "Stopped"}
    return live_monitor.status()


@app.post("/api/monitor/start")
def start_monitor(
    camera_index: int | None = None, camera_id: str | None = None
) -> dict:
    return _get_live_monitor().start(camera_index, camera_id)


@app.post("/api/monitor/stop")
def stop_monitor() -> dict:
    return live_monitor.stop() if live_monitor else {"running": False, "connected": False, "message": "Stopped"}


@app.patch("/api/incidents/{event_id}")
async def patch_incident(event_id: str, body: PatchIncidentRequest) -> dict:
    """Update review status and optional operator notes."""
    updated = event_logger.update_review_status(
        event_id, body.review_status, body.operator_notes
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Event not found")
    event = event_logger.get_event(event_id)
    event["evidence_url"] = _evidence_url(event.get("evidence_path"))

    # Notify WS clients
    await ws_manager.broadcast({"type": "incident_updated", "data": event})
    return event


@app.get("/api/devices")
def list_devices() -> dict:
    """
    Return a list of known poles derived from the event log.

    Real hardware telemetry (heartbeat, battery, signal) is not yet
    implemented. Fields that require hardware are explicitly marked
    ``null`` rather than fabricated.
    """
    events = event_logger.get_recent_events(limit=2000)
    poles: dict[str, dict] = {}

    for ev in events:
        pid = ev.get("pole_id", "unknown")
        if pid not in poles:
            poles[pid] = {
                "pole_id": pid,
                "camera_id": ev.get("camera_id"),
                "last_event_ts": ev.get("server_ts"),
                "event_count": 0,
                "high_priority_count": 0,
                # Hardware fields — not yet available
                "online": None,
                "last_heartbeat": None,
                "battery_pct": None,
                "signal_strength": None,
                "tamper_alert": False,
            }
        poles[pid]["event_count"] += 1
        if ev.get("alert_priority") == "high":
            poles[pid]["high_priority_count"] += 1
        # Keep most recent timestamp
        if ev.get("server_ts", "") > poles[pid]["last_event_ts"]:
            poles[pid]["last_event_ts"] = ev["server_ts"]

    return {"items": list(poles.values()), "total": len(poles)}


@app.get("/api/devices/{pole_id}")
def get_device(pole_id: str) -> dict:
    events = event_logger.get_recent_events(limit=2000)
    pole_events = [e for e in events if e.get("pole_id") == pole_id]
    if not pole_events:
        raise HTTPException(status_code=404, detail="Pole not found")

    latest = pole_events[0]
    for ev in pole_events:
        ev["evidence_url"] = _evidence_url(ev.get("evidence_path"))

    return {
        "pole_id": pole_id,
        "camera_id": latest.get("camera_id"),
        "last_event_ts": latest.get("server_ts"),
        "event_count": len(pole_events),
        "online": None,
        "last_heartbeat": None,
        "battery_pct": None,
        "signal_strength": None,
        "tamper_alert": False,
        "recent_events": pole_events[:20],
    }


@app.get("/api/analytics/detections")
def analytics_detections(
    days: int = Query(7, ge=1, le=90),
) -> dict:
    """
    Detection counts grouped by date and class for the last N days.
    Also returns high-priority counts per day.
    """
    events = event_logger.get_recent_events(limit=5000)
    now = datetime.now(timezone.utc)

    # Filter to the requested window
    def _days_ago(ev: dict) -> float:
        try:
            ts = datetime.fromisoformat(ev["server_ts"])
            return (now - ts).total_seconds() / 86400
        except Exception:
            return 9999

    window = [e for e in events if _days_ago(e) <= days]

    # Group by date string
    by_date: dict[str, dict] = {}
    by_class: dict[str, int] = {}
    for ev in window:
        date_str = ev["server_ts"][:10]
        if date_str not in by_date:
            by_date[date_str] = {"date": date_str, "animal": 0, "person": 0, "firearm": 0, "high": 0}
        cls = ev.get("class_name", "unknown")
        if cls in by_date[date_str]:
            by_date[date_str][cls] += 1
        by_class[cls] = by_class.get(cls, 0) + 1
        if ev.get("alert_priority") in {"high", "critical"}:
            by_date[date_str]["high"] += 1

    # Counts by pole
    by_pole: dict[str, int] = {}
    for ev in window:
        pid = ev.get("pole_id", "unknown")
        by_pole[pid] = by_pole.get(pid, 0) + 1

    # Review status breakdown
    review_counts: dict[str, int] = {}
    for ev in window:
        rs = ev.get("review_status", "unknown")
        review_counts[rs] = review_counts.get(rs, 0) + 1

    return {
        "days": days,
        "total": len(window),
        "by_date": sorted(by_date.values(), key=lambda x: x["date"]),
        "by_class": by_class,
        "by_pole": by_pole,
        "review_status_breakdown": review_counts,
    }


@app.get("/api/model/metrics")
def model_metrics() -> dict:
    """
    Return evaluation metrics from the most recent metrics.json run.

    If no evaluation has been run, returns model_ready=False with null fields.
    We never fabricate numbers.
    """
    runs_dir = PROJECT_ROOT / "runs" / "evaluate"
    metrics_file: Path | None = None

    if runs_dir.exists():
        # Find the most recent metrics.json
        candidates = sorted(
            runs_dir.glob("*/metrics.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            metrics_file = candidates[0]

    if not metrics_file:
        return {
            "available": False,
            "message": (
                "No evaluation results found. "
                "Run: python scripts/evaluate.py --weights models/best.pt"
            ),
            "metrics": None,
        }

    with metrics_file.open() as f:
        data = json.load(f)

    return {
        "available": True,
        "source_file": str(metrics_file),
        **data,
    }


@app.post("/api/detect/image")
async def detect_image(file: UploadFile = File(...)) -> dict:
    """
    Run YOLOv8 detection on an uploaded image.

    Returns detection results and logs events to the database.
    Requires models/best.pt to exist.
    """
    if not cfg.model_weights.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Model weights not found. Train the model in Colab "
                "and copy best.pt to models/."
            ),
        )

    try:
        from src.detector import Detector
        from src.evidence_store import EvidenceStore
        import numpy as np
        try:
            import cv2
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="opencv-python not installed. Run: pip install opencv-python"
            )
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    # Read uploaded image
    raw = await file.read()
    arr = np.frombuffer(raw, np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=422, detail="Could not decode image file.")

    t0 = time.perf_counter()
    detector = Detector(
        cfg.model_weights, conf=cfg.confidence_threshold, iou=cfg.iou_threshold
    )
    detections = detector.detect_image(frame)
    latency_ms = round((time.perf_counter() - t0) * 1000, 1)

    evidence_store = EvidenceStore(cfg.evidence_dir)
    alert_results  = alert_engine.evaluate_frame(detections)
    logged_events  = []

    for idx, det in enumerate(detections):
        alert = alert_results[idx]
        try:
            ev_path = evidence_store.save_crop(
                frame, det.bbox_xyxy, det.class_name, "api_upload"
            )
        except Exception:
            ev_path = None

        eid = event_logger.log_event(
            class_name=det.class_name,
            confidence=det.confidence,
            camera_id=cfg.camera_id,
            pole_id=cfg.pole_id,
            bbox=det.bbox_xyxy,
            alert_priority=alert.priority,
            alert_label=alert.label or None,
            evidence_path=ev_path,
        )
        event = event_logger.get_event(eid)
        event["evidence_url"] = _evidence_url(ev_path)
        logged_events.append(event)

        # Push to WebSocket clients
        await _broadcast_event(event)

    return {
        "filename": file.filename,
        "detections_count": len(detections),
        "latency_ms": latency_ms,
        "detections": [
            {
                "class_name": d.class_name,
                "confidence": round(d.confidence, 4),
                "bbox_xyxy": list(d.bbox_xyxy),
                "track_id": d.track_id,
            }
            for d in detections
        ],
        "events": logged_events,
    }


@app.post("/api/detect/video")
async def detect_video(file: UploadFile = File(...)) -> dict:
    """
    Run YOLOv8 detection on an uploaded video (frame-sampled for efficiency).

    Samples every 5th frame to reduce processing time on CPU.
    Returns aggregate detection counts and logged event IDs.
    """
    if not cfg.model_weights.exists():
        raise HTTPException(
            status_code=503,
            detail="Model weights not found. Copy best.pt to models/ first."
        )

    try:
        from src.detector import Detector
        from src.evidence_store import EvidenceStore
        import numpy as np
        import cv2
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    # Write to a temp file
    suffix = Path(file.filename or "video.mp4").suffix or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        detector = Detector(
            cfg.model_weights, conf=cfg.confidence_threshold, iou=cfg.iou_threshold
        )
        evidence_store = EvidenceStore(cfg.evidence_dir)

        cap = cv2.VideoCapture(str(tmp_path))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        cap.release()

        SAMPLE_EVERY = 5
        event_ids: list[str] = []
        frame_idx = 0
        class_counts: dict[str, int] = {}

        for frame_dets in detector.detect_video(tmp_path):
            if frame_idx % SAMPLE_EVERY == 0 and frame_dets:
                cap2 = cv2.VideoCapture(str(tmp_path))
                cap2.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ok, fr = cap2.read()
                cap2.release()

                if ok:
                    alert_results = alert_engine.evaluate_frame(frame_dets)
                    for idx, det in enumerate(frame_dets):
                        alert = alert_results[idx]
                        try:
                            ev_path = evidence_store.save_crop(
                                fr, det.bbox_xyxy, det.class_name, "api_video"
                            )
                        except Exception:
                            ev_path = None

                        eid = event_logger.log_event(
                            class_name=det.class_name,
                            confidence=det.confidence,
                            camera_id=cfg.camera_id,
                            pole_id=cfg.pole_id,
                            bbox=det.bbox_xyxy,
                            alert_priority=alert.priority,
                            alert_label=alert.label or None,
                            evidence_path=ev_path,
                        )
                        event_ids.append(eid)
                        class_counts[det.class_name] = \
                            class_counts.get(det.class_name, 0) + 1

            frame_idx += 1
    finally:
        tmp_path.unlink(missing_ok=True)

    return {
        "filename": file.filename,
        "total_frames": total_frames,
        "frames_sampled": frame_idx // SAMPLE_EVERY,
        "total_detections": sum(class_counts.values()),
        "class_counts": class_counts,
        "event_ids": event_ids,
    }


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time events.

    Messages sent to clients:
      { "type": "new_detection",   "data": <event_dict> }
      { "type": "incident_updated","data": <event_dict> }
      { "type": "ping" }

    Messages accepted from clients:
      { "type": "ping" }  → server responds with { "type": "pong" }
    """
    await ws_manager.connect(websocket)
    # Send initial greeting
    await websocket.send_json({
        "type": "connected",
        "data": {
            "message": "Forest Intrusion Detection WebSocket connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    })
    try:
        while True:
            msg = await websocket.receive_json()
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.warning("WS error: %s", exc)
        ws_manager.disconnect(websocket)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _publish_monitor_event(event: dict) -> None:
    loop = _event_loop
    if loop is None or loop.is_closed():
        logger.warning("Could not publish live detection: API event loop is unavailable")
        return
    loop.call_soon_threadsafe(
        lambda: asyncio.create_task(_broadcast_event(event))
    )


def _normalize_date_filter(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail=f"Invalid date/time filter: {value}"
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _evidence_url(path: str | Path | None) -> str | None:
    """Convert an absolute evidence file path to a relative URL."""
    if not path:
        return None
    p = Path(path)
    try:
        rel = p.relative_to(EVIDENCE_DIR)
        return f"/evidence/{rel.as_posix()}"
    except ValueError:
        return None


# ── Startup / shutdown ────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup() -> None:
    global _event_loop
    _event_loop = asyncio.get_running_loop()
    logger.info("Forest Intrusion API started")
    logger.info("Model weights: %s (exists=%s)", cfg.model_weights, cfg.model_weights.exists())
    logger.info("MongoDB database: %s (connected=%s)", cfg.mongodb_database, event_logger is not None)


@app.on_event("shutdown")
async def shutdown() -> None:
    if event_logger:
        event_logger.close()
    logger.info("Forest Intrusion API shut down")
