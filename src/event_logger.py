"""MongoDB persistence for detection events, evidence metadata, and poles."""
from __future__ import annotations

import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class EventLogger:
    PENDING, REVIEWED, DISMISSED = "pending", "reviewed", "dismissed"
    PRIORITY_NORMAL, PRIORITY_HIGH, PRIORITY_CRITICAL = "normal", "high", "critical"

    def __init__(self, database: Any = None, evidence_dir: str | Path = "storage/evidence",
                 *, uri: str | None = None, database_name: str = "forest_intrusion",
                 server_selection_timeout_ms: int = 3000) -> None:
        self.evidence_dir = Path(evidence_dir).resolve()
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self._client = None
        if database is None:
            if not uri:
                raise RuntimeError("MongoDB is not configured. Set MONGODB_URI in .env.")
            try:
                from pymongo import MongoClient
                from pymongo.errors import PyMongoError
            except ImportError as exc:
                raise RuntimeError("PyMongo is required. Install dependencies with pip install -r requirements.txt.") from exc
            try:
                self._client = MongoClient(uri, serverSelectionTimeoutMS=server_selection_timeout_ms)
                self._client.admin.command("ping")
                database = self._client[database_name]
            except Exception as exc:
                if self._client:
                    self._client.close()
                raise ConnectionError(
                    f"Could not connect to MongoDB ({type(exc).__name__}). "
                    "Verify MONGODB_URI, network access, and database availability."
                ) from exc
        self.db = database
        self.events = database["events"]
        self.event_images = database["event_images"]
        self.poles = database["poles"]
        self._initialize_indexes()

    def _initialize_indexes(self) -> None:
        self.events.create_index("event_id", unique=True)
        self.events.create_index([("server_ts", -1)])
        self.events.create_index("class_name")
        self.events.create_index("pole_id")
        self.events.create_index("alert_priority")
        self.event_images.create_index([("event_id", 1), ("sequence", 1)], unique=True)
        self.event_images.create_index("event_id")
        self.poles.create_index("pole_id", unique=True)

    def log_event(self, *, class_name: str, confidence: float, camera_id: str,
                  pole_id: str, bbox: tuple[float, float, float, float] | None = None,
                  track_id: int | None = None, alert_priority: str = "normal",
                  alert_label: str | None = None, evidence_path: str | Path | None = None,
                  source_ts: str | None = None, segment_id: str | None = None,
                  pole_location: Any = None, image_records: list[dict] | None = None,
                  first_detection_time: str | None = None, last_detection_time: str | None = None,
                  intrusion_duration_seconds: float | None = None,
                  event_id: str | None = None) -> str:
        event_id = event_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        safe_path = self._validate_evidence_path(evidence_path) if evidence_path else None
        if image_records is not None and len(image_records) != 6:
            raise ValueError("Exactly six event image records are required.")
        if safe_path and image_records is None:
            # Compatibility for existing upload callers: retain six real JPEG files
            # and independent Mongo metadata even when the source is a single still.
            source = Path(safe_path)
            burst_dir = self.evidence_dir / event_id
            burst_dir.mkdir(parents=True, exist_ok=False)
            image_records = []
            for sequence in range(1, 7):
                target = burst_dir / f"{sequence:02d}.jpg"
                shutil.copy2(source, target)
                image_records.append({"path": target, "capture_timestamp": now,
                                      "metadata": {"source": "single-frame compatibility copy"}})
            safe_path = str((burst_dir / "01.jpg").resolve())
        doc = {
            "event_id": event_id, "source_ts": source_ts, "server_ts": now,
            "detection_timestamp": source_ts or now, "camera_id": camera_id,
            "pole_id": pole_id, "pole_location": pole_location, "segment_id": segment_id,
            "class_name": class_name, "detected_class": class_name,
            "confidence": float(confidence), "track_id": track_id,
            "bbox": list(bbox) if bbox else None,
            "bbox_x1": bbox[0] if bbox else None, "bbox_y1": bbox[1] if bbox else None,
            "bbox_x2": bbox[2] if bbox else None, "bbox_y2": bbox[3] if bbox else None,
            "alert_priority": alert_priority, "alert_label": alert_label,
            "evidence_path": safe_path, "review_status": self.PENDING,
            "operator_notes": None, "first_detection_time": first_detection_time or now,
            "last_detection_time": last_detection_time or now,
            "intrusion_duration_seconds": intrusion_duration_seconds,
            "image_count": len(image_records or []),
        }
        records = []
        for seq, item in enumerate(image_records or [], 1):
            path = self._validate_evidence_path(item["path"])
            p = Path(path)
            if not p.is_file():
                raise FileNotFoundError(f"Evidence image is missing: {p}")
            records.append({"event_id": event_id, "sequence": seq,
                "capture_timestamp": item.get("capture_timestamp", now), "local_path": path,
                "mime_type": "image/jpeg", "size_bytes": p.stat().st_size,
                "metadata": item.get("metadata")})
        # Persist event before associated images. On image insertion failure, expose a clear error
        # and mark the event as partial so operators can identify the incomplete evidence set.
        self.events.insert_one(doc)
        if records:
            try:
                self.event_images.insert_many(records, ordered=True)
            except Exception as exc:
                self.events.update_one({"event_id": event_id}, {"$set": {"evidence_error": str(exc)}})
                raise RuntimeError(f"Event {event_id} saved but image metadata insertion failed: {exc}") from exc
        self.poles.update_one({"pole_id": pole_id}, {"$set": {
            "pole_id": pole_id, "camera_id": camera_id, "last_detection_ts": now,
            "latest_alert_status": alert_priority}}, upsert=True)
        return event_id

    def add_event_images(self, event_id: str, paths: list[str | Path], timestamps: list[str] | None = None) -> None:
        if len(paths) != 6:
            raise ValueError("Exactly six burst images are required.")
        now = datetime.now(timezone.utc).isoformat()
        records = []
        for i, raw_path in enumerate(paths, 1):
            path = self._validate_evidence_path(raw_path)
            records.append({"event_id": event_id, "sequence": i,
                "capture_timestamp": (timestamps or [])[i-1] if timestamps and len(timestamps) >= i else now,
                "local_path": path, "mime_type": "image/jpeg", "size_bytes": Path(path).stat().st_size})
        self.event_images.insert_many(records, ordered=True)
        self.events.update_one({"event_id": event_id}, {"$set": {"image_count": 6}})

    def get_event_images(self, event_id: str) -> list[dict]:
        return [self._clean(x) for x in self.event_images.find({"event_id": event_id}).sort("sequence", 1)]

    def get_recent_events(self, limit: int = 50) -> list[dict]:
        return [self._clean(x) for x in self.events.find().sort("server_ts", -1).limit(max(0, limit))]

    def query_events(self, *, start: str | None = None, end: str | None = None,
                     pole_id: str | None = None, class_name: str | None = None,
                     priority: str | None = None, limit: int = 500) -> list[dict]:
        query: dict[str, Any] = {}
        if start or end:
            query["server_ts"] = {**({"$gte": start} if start else {}), **({"$lte": end} if end else {})}
        for key, value in (("pole_id", pole_id), ("class_name", class_name), ("alert_priority", priority)):
            if value: query[key] = value
        return [self._clean(x) for x in self.events.find(query).sort("server_ts", -1).limit(max(0, limit))]

    def get_event(self, event_id: str) -> dict | None:
        return self._clean(self.events.find_one({"event_id": event_id}))

    def get_events_by_class(self, class_name: str, limit: int = 100) -> list[dict]:
        return self.query_events(class_name=class_name, limit=limit)

    def get_high_priority_events(self, limit: int = 100) -> list[dict]:
        return [self._clean(x) for x in self.events.find({"alert_priority": {"$in": ["high", "critical"]}}).sort("server_ts", -1).limit(limit)]

    def update_review_status(self, event_id: str, status: str, notes: str | None = None) -> bool:
        if status not in {self.PENDING, self.REVIEWED, self.DISMISSED}:
            raise ValueError(f"Invalid review status {status!r}.")
        return self.events.update_one({"event_id": event_id}, {"$set": {"review_status": status, "operator_notes": notes}}).matched_count > 0

    def count_by_class(self) -> dict[str, int]:
        return {x["_id"]: x["count"] for x in self.events.aggregate([{"$group": {"_id": "$class_name", "count": {"$sum": 1}}}]) if x.get("_id")}

    def count_events(self, query: dict | None = None) -> int:
        return self.events.count_documents(query or {})

    def upsert_pole(self, pole_id: str, **fields: Any) -> None:
        self.poles.update_one({"pole_id": pole_id}, {"$set": {"pole_id": pole_id, **fields}}, upsert=True)

    def update_pole_heartbeat(self, pole_id: str, *, camera_id: str, online: bool,
                               pole_name: str | None = None, location: Any = None,
                               latest_alert_status: str | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        data = {"camera_id": camera_id, "status": "online" if online else "offline", "last_heartbeat": now}
        if pole_name is not None: data["pole_name"] = pole_name
        if location is not None: data["location"] = location
        if latest_alert_status is not None: data["latest_alert_status"] = latest_alert_status
        self.upsert_pole(pole_id, **data)

    def get_poles(self) -> list[dict]:
        return [self._clean(p) for p in self.poles.find().sort("pole_id", 1)]

    def close(self) -> None:
        if self._client is not None: self._client.close()

    def __enter__(self): return self
    def __exit__(self, *_): self.close()

    def _validate_evidence_path(self, path: str | Path) -> str:
        p = Path(path).resolve()
        try: p.relative_to(self.evidence_dir)
        except ValueError as exc: raise ValueError(f"Evidence path {p} is outside the allowed evidence directory {self.evidence_dir}.") from exc
        return str(p)

    @staticmethod
    def _clean(doc: dict | None) -> dict | None:
        if doc is None: return None
        result = dict(doc); result.pop("_id", None); return result
