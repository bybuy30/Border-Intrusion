"""
src/event_logger.py
===================
SQLite-backed event logger for detection events.

Schema
------
Each row in the ``events`` table represents a single object detection that
passed the alert pipeline.  Fields deliberately mirror what a future web
dashboard will need without pre-optimising for an unknown schema.

    event_id        TEXT  PRIMARY KEY   UUID v4
    source_ts       TEXT               ISO 8601 timestamp from the source frame
                                       (may be None if not available)
    server_ts       TEXT               ISO 8601 timestamp when the event was
                                       recorded by this process
    camera_id       TEXT
    pole_id         TEXT
    segment_id      TEXT               Optional video segment identifier
    class_name      TEXT               "animal" | "person" | "firearm"
    confidence      REAL
    track_id        INTEGER            Temporary session tracking ID (nullable)
    bbox_x1         REAL               Bounding-box pixel coordinates
    bbox_y1         REAL
    bbox_x2         REAL
    bbox_y2         REAL
    alert_priority  TEXT               "normal" | "high"
    alert_label     TEXT               Human-readable label (e.g. "Potential weapon
                                       detected — review required")
    evidence_path   TEXT               Path to the saved evidence image (nullable)
    review_status   TEXT               "pending" | "reviewed" | "dismissed"
    operator_notes  TEXT               Free-text notes added during review

Security notes
--------------
- All SQL statements use parameterised queries (no string formatting of
  user-supplied values into SQL).
- File paths stored in evidence_path are validated to be within the allowed
  evidence directory before insertion.
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class EventLogger:
    """
    Manages detection events in a SQLite database.

    Parameters
    ----------
    db_path:
        Path to the SQLite file.  Created automatically if it does not exist.
    evidence_dir:
        Absolute path to the directory that stores evidence images.  Used to
        validate that stored paths are within the expected directory.
    """

    # Review status constants
    PENDING = "pending"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"

    # Alert priority constants
    PRIORITY_NORMAL = "normal"
    PRIORITY_HIGH = "high"

    def __init__(self, db_path: str | Path, evidence_dir: str | Path) -> None:
        self.db_path = Path(db_path)
        self.evidence_dir = Path(evidence_dir).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection = self._connect()
        self._create_schema()

    # ── Connection ────────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")   # Better concurrent access
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _create_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id        TEXT PRIMARY KEY,
                source_ts       TEXT,
                server_ts       TEXT NOT NULL,
                camera_id       TEXT NOT NULL,
                pole_id         TEXT NOT NULL,
                segment_id      TEXT,
                class_name      TEXT NOT NULL,
                confidence      REAL NOT NULL,
                track_id        INTEGER,
                bbox_x1         REAL,
                bbox_y1         REAL,
                bbox_x2         REAL,
                bbox_y2         REAL,
                alert_priority  TEXT NOT NULL DEFAULT 'normal',
                alert_label     TEXT,
                evidence_path   TEXT,
                review_status   TEXT NOT NULL DEFAULT 'pending',
                operator_notes  TEXT
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_server_ts "
            "ON events(server_ts);"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_class "
            "ON events(class_name);"
        )
        self._conn.commit()

    # ── Write ─────────────────────────────────────────────────────────────────

    def log_event(
        self,
        *,
        class_name: str,
        confidence: float,
        camera_id: str,
        pole_id: str,
        bbox: tuple[float, float, float, float] | None = None,
        track_id: int | None = None,
        alert_priority: str = PRIORITY_NORMAL,
        alert_label: str | None = None,
        evidence_path: str | Path | None = None,
        source_ts: str | None = None,
        segment_id: str | None = None,
    ) -> str:
        """
        Insert a single detection event and return its UUID.

        Parameters
        ----------
        class_name:
            Detected class (``"animal"``, ``"person"``, or ``"firearm"``).
        confidence:
            Model confidence score (0.0–1.0).
        camera_id, pole_id:
            Identifiers for the recording device.
        bbox:
            Bounding box as ``(x1, y1, x2, y2)`` pixel coordinates.
        track_id:
            Temporary tracking ID for this session (nullable).
        alert_priority:
            ``"normal"`` or ``"high"``.
        alert_label:
            Human-readable alert label.  For firearm detections the
            ``AlertEngine`` sets this to
            ``"Potential weapon detected — review required"``.
        evidence_path:
            Path to the saved cropped evidence image.  Must be inside
            ``evidence_dir``.
        source_ts:
            Timestamp embedded in the source frame or video segment
            (ISO 8601).  May be ``None`` if unavailable.
        segment_id:
            Optional identifier for the video segment being processed.

        Returns
        -------
        str
            UUID of the newly created event.
        """
        event_id = str(uuid.uuid4())
        server_ts = datetime.now(timezone.utc).isoformat()

        # Validate and sanitise evidence_path
        safe_evidence_path: str | None = None
        if evidence_path is not None:
            safe_evidence_path = self._validate_evidence_path(evidence_path)

        x1 = y1 = x2 = y2 = None
        if bbox is not None:
            x1, y1, x2, y2 = bbox

        self._conn.execute(
            """
            INSERT INTO events (
                event_id, source_ts, server_ts, camera_id, pole_id,
                segment_id, class_name, confidence, track_id,
                bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                alert_priority, alert_label,
                evidence_path, review_status, operator_notes
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?
            )
            """,
            (
                event_id, source_ts, server_ts, camera_id, pole_id,
                segment_id, class_name, confidence, track_id,
                x1, y1, x2, y2,
                alert_priority, alert_label,
                safe_evidence_path, self.PENDING, None,
            ),
        )
        self._conn.commit()
        logger.debug("Logged event %s — %s (%.2f)", event_id, class_name, confidence)
        return event_id

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the most recent events, newest first."""
        cur = self._conn.execute(
            "SELECT * FROM events ORDER BY server_ts DESC LIMIT ?", (limit,)
        )
        return [dict(row) for row in cur.fetchall()]

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        """Return a single event by its UUID, or None if not found."""
        cur = self._conn.execute(
            "SELECT * FROM events WHERE event_id = ?", (event_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_events_by_class(
        self, class_name: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Return events filtered by class name."""
        cur = self._conn.execute(
            "SELECT * FROM events WHERE class_name = ? ORDER BY server_ts DESC LIMIT ?",
            (class_name, limit),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_high_priority_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return events with alert_priority = 'high'."""
        cur = self._conn.execute(
            "SELECT * FROM events WHERE alert_priority = 'high' "
            "ORDER BY server_ts DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]

    # ── Update ────────────────────────────────────────────────────────────────

    def update_review_status(
        self,
        event_id: str,
        status: str,
        notes: str | None = None,
    ) -> bool:
        """
        Update the review status of an event.

        Parameters
        ----------
        event_id:
            UUID of the event to update.
        status:
            One of ``"pending"``, ``"reviewed"``, or ``"dismissed"``.
        notes:
            Optional operator notes.

        Returns
        -------
        bool
            True if the row was found and updated; False otherwise.
        """
        valid_statuses = {self.PENDING, self.REVIEWED, self.DISMISSED}
        if status not in valid_statuses:
            raise ValueError(
                f"Invalid review status {status!r}. "
                f"Must be one of: {sorted(valid_statuses)}"
            )
        cur = self._conn.execute(
            "UPDATE events SET review_status = ?, operator_notes = ? "
            "WHERE event_id = ?",
            (status, notes, event_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    # ── Statistics ────────────────────────────────────────────────────────────

    def count_by_class(self) -> dict[str, int]:
        """Return a dictionary of {class_name: count} for all events."""
        cur = self._conn.execute(
            "SELECT class_name, COUNT(*) as cnt FROM events GROUP BY class_name"
        )
        return {row["class_name"]: row["cnt"] for row in cur.fetchall()}

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            logger.debug("EventLogger closed.")

    def __enter__(self) -> "EventLogger":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _validate_evidence_path(self, path: str | Path) -> str:
        """
        Ensure the evidence path is within the allowed evidence directory.

        Raises
        ------
        ValueError
            If the resolved path escapes ``evidence_dir``.
        """
        p = Path(path).resolve()
        try:
            p.relative_to(self.evidence_dir)
        except ValueError as exc:
            raise ValueError(
                f"Evidence path {p} is outside the allowed evidence "
                f"directory {self.evidence_dir}."
            ) from exc
        return str(p)
