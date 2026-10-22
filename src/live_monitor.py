"""Single-owner live camera worker with cooldowns and six-frame evidence bursts."""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable

import cv2

from src.evidence_store import EvidenceStore

logger = logging.getLogger(__name__)


def discover_cameras(max_index: int = 8, *, dshow: bool = False) -> list[dict[str, Any]]:
    found = []
    backend = cv2.CAP_DSHOW if dshow and hasattr(cv2, "CAP_DSHOW") else cv2.CAP_ANY
    for index in range(max_index):
        cap = cv2.VideoCapture(index, backend)
        opened = cap.isOpened()
        if opened:
            ok, _ = cap.read()
            opened = bool(ok)
        cap.release()
        if opened:
            found.append({"camera_index": index, "camera_id": f"camera_{index:02d}", "status": "available"})
    return found


class LiveMonitor:
    def __init__(self, cfg, detector, event_logger, alert_engine, *, capture_factory=None,
                 on_event: Callable[[dict], None] | None = None):
        self.cfg, self.detector, self.logger, self.alert_engine = cfg, detector, event_logger, alert_engine
        self.capture_factory = capture_factory or cv2.VideoCapture
        self.on_event = on_event
        self._lock = threading.Lock()
        self._thread = None
        self._stop = threading.Event()
        self._frame = None
        self._status = {"running": False, "camera_id": cfg.camera_id, "camera_index": cfg.camera_index,
                        "connected": False, "message": "Stopped", "last_heartbeat": None}
        self._last_event: dict[str, float] = {}
        self._recent_frames = deque(maxlen=6)
        self._last_burst_frame_at = 0.0
        self._last_heartbeat_at = 0.0
        self._error = None

    def status(self):
        with self._lock:
            return {**self._status, "error": self._error}

    def latest_frame(self):
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def start(self, camera_index: int | None = None, camera_id: str | None = None) -> dict:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return {**self._status, "message": "Monitoring is already running"}
            if camera_index is not None:
                self.cfg.camera_index = int(camera_index)
                self.cfg.camera_id = camera_id or f"camera_{self.cfg.camera_index:02d}"
            elif camera_id:
                self.cfg.camera_id = camera_id
            self._stop.clear()
            self._error = None
            self._thread = threading.Thread(target=self._run, name="forest-camera-monitor", daemon=True)
            self._status.update(running=True, camera_index=self.cfg.camera_index,
                                camera_id=self.cfg.camera_id, message="Connecting")
            self._thread.start()
            return dict(self._status)

    def stop(self) -> dict:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=3)
        with self._lock:
            self._status.update(running=False, connected=False, message="Stopped")
            try:
                self.logger.update_pole_heartbeat(self.cfg.pole_id, camera_id=self.cfg.camera_id,
                    online=False, pole_name=self.cfg.pole_name, location=self.cfg.pole_location)
            except Exception as exc:
                self._error = f"Could not update pole status: {exc}"
            return dict(self._status)

    def _run(self):
        backend = cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else cv2.CAP_ANY
        cap = self.capture_factory(self.cfg.camera_index, backend)
        try:
            if not cap.isOpened():
                raise RuntimeError(f"Camera {self.cfg.camera_index} could not be opened")
            with self._lock:
                self._status.update(connected=True, message="Monitoring")
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    raise RuntimeError("Camera read failed or camera disconnected")
                now = time.monotonic()
                if now - self._last_burst_frame_at >= self.cfg.burst_interval_seconds:
                    self._recent_frames.append((now, frame.copy(), datetime.now(timezone.utc).isoformat()))
                    self._last_burst_frame_at = now
                detections = self.detector.detect_image(frame)
                annotated = frame.copy()
                for det in detections:
                    x1, y1, x2, y2 = map(int, det.bbox_xyxy)
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 120, 255), 2)
                    cv2.putText(annotated, f"{det.class_name} {det.confidence:.2f}", (x1, max(15, y1-5)),
                                cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 120, 255), 2)
                with self._lock:
                    self._frame = annotated
                    self._status["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
                if now - self._last_heartbeat_at >= 5:
                    self.logger.update_pole_heartbeat(self.cfg.pole_id, camera_id=self.cfg.camera_id,
                        online=True, pole_name=self.cfg.pole_name, location=self.cfg.pole_location)
                    self._last_heartbeat_at = now
                if detections:
                    alerts = self.alert_engine.evaluate_frame(detections)
                    for idx, det in enumerate(detections):
                        key = f"{det.class_name}:{det.track_id if det.track_id is not None else 'camera'}"
                        if now - self._last_event.get(key, -1e9) < self.cfg.event_cooldown_seconds:
                            continue
                        self._last_event[key] = now
                        self._capture_event(det, frame, alerts[idx], now)
        except Exception as exc:
            with self._lock:
                self._error = str(exc)
                self._status.update(connected=False, message="Camera error", running=False)
            try:
                self.logger.update_pole_heartbeat(self.cfg.pole_id, camera_id=self.cfg.camera_id,
                    online=False, pole_name=self.cfg.pole_name, location=self.cfg.pole_location)
            except Exception:
                logger.exception("Could not mark pole %s offline after camera failure", self.cfg.pole_id)
        finally:
            cap.release()
            with self._lock:
                self._status["running"] = False

    def _capture_event(self, det, frame, alert, now):
        # Use the latest frames; repeat the trigger frame only when startup is too recent.
        samples = [(ts, f.copy(), captured_at) for ts, f, captured_at in self._recent_frames]
        if not samples:
            samples = [(now, frame.copy(), datetime.now(timezone.utc).isoformat())]
        while len(samples) < 6:
            samples.insert(0, (samples[0][0], samples[0][1].copy(), samples[0][2]))
        samples = samples[-6:]
        frames = [f for _, f, _ in samples]
        event_id = str(__import__("uuid").uuid4())
        paths = EvidenceStore(self.cfg.evidence_dir).save_burst(frames, event_id)
        image_meta = [{"path": p, "capture_timestamp": sample[2]} for p, sample in zip(paths, samples)]
        try:
            self.logger.log_event(class_name=det.class_name, confidence=det.confidence,
                camera_id=self.cfg.camera_id, pole_id=self.cfg.pole_id, bbox=det.bbox_xyxy,
                track_id=det.track_id, alert_priority=alert.priority, alert_label=alert.label or None,
                evidence_path=paths[0], image_records=image_meta, pole_location=self.cfg.pole_location,
                event_id=event_id)
            if self.on_event:
                event = self.logger.get_event(event_id)
                if event:
                    try:
                        self.on_event(event)
                    except Exception:
                        logger.exception("Could not publish detection event %s", event_id)
        except Exception:
            # Evidence files remain for recovery and the worker reports persistence failure.
            raise
