"""
tests/test_event_logger.py
==========================
Unit tests for src/event_logger.py.

No database file, model weights, or real images are required.
A fresh in-memory-style SQLite database is created in a temporary directory
for each test function.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.event_logger import EventLogger


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def logger(tmp_path: Path) -> EventLogger:
    """Return a fresh EventLogger backed by a temporary SQLite database."""
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    db_path = tmp_path / "test_events.db"
    el = EventLogger(db_path=db_path, evidence_dir=evidence_dir)
    yield el
    el.close()


# ── Basic logging ─────────────────────────────────────────────────────────────

class TestLogEvent:

    def test_returns_uuid(self, logger):
        eid = logger.log_event(
            class_name="animal",
            confidence=0.85,
            camera_id="cam1",
            pole_id="pole1",
        )
        assert isinstance(eid, str)
        assert len(eid) == 36   # UUID4 format

    def test_event_retrievable(self, logger):
        eid = logger.log_event(
            class_name="person",
            confidence=0.72,
            camera_id="cam2",
            pole_id="pole3",
        )
        event = logger.get_event(eid)
        assert event is not None
        assert event["class_name"] == "person"
        assert abs(event["confidence"] - 0.72) < 1e-6
        assert event["camera_id"] == "cam2"
        assert event["review_status"] == EventLogger.PENDING

    def test_bbox_stored_correctly(self, logger):
        eid = logger.log_event(
            class_name="firearm",
            confidence=0.90,
            camera_id="cam1",
            pole_id="pole1",
            bbox=(10.0, 20.0, 110.0, 220.0),
        )
        event = logger.get_event(eid)
        assert event["bbox_x1"] == pytest.approx(10.0)
        assert event["bbox_y1"] == pytest.approx(20.0)
        assert event["bbox_x2"] == pytest.approx(110.0)
        assert event["bbox_y2"] == pytest.approx(220.0)

    def test_high_priority_stored(self, logger):
        eid = logger.log_event(
            class_name="firearm",
            confidence=0.88,
            camera_id="cam1",
            pole_id="pole1",
            alert_priority=EventLogger.PRIORITY_HIGH,
            alert_label="Potential weapon detected — review required",
        )
        event = logger.get_event(eid)
        assert event["alert_priority"] == "high"
        assert "review required" in event["alert_label"]

    def test_track_id_nullable(self, logger):
        eid = logger.log_event(
            class_name="animal",
            confidence=0.60,
            camera_id="cam1",
            pole_id="pole1",
            track_id=None,
        )
        event = logger.get_event(eid)
        assert event["track_id"] is None

    def test_track_id_stored(self, logger):
        eid = logger.log_event(
            class_name="person",
            confidence=0.75,
            camera_id="cam1",
            pole_id="pole1",
            track_id=42,
        )
        event = logger.get_event(eid)
        assert event["track_id"] == 42

    def test_source_ts_separate_from_server_ts(self, logger):
        src_ts = "2026-10-01T08:00:00+00:00"
        eid = logger.log_event(
            class_name="animal",
            confidence=0.5,
            camera_id="cam1",
            pole_id="pole1",
            source_ts=src_ts,
        )
        event = logger.get_event(eid)
        assert event["source_ts"] == src_ts
        assert event["server_ts"] != src_ts


# ── Retrieval ─────────────────────────────────────────────────────────────────

class TestRetrieval:

    def test_get_recent_events_ordering(self, logger):
        for cls in ["animal", "person", "firearm"]:
            logger.log_event(class_name=cls, confidence=0.5,
                             camera_id="c", pole_id="p")
        recent = logger.get_recent_events(limit=10)
        assert len(recent) == 3
        # Newest first
        assert recent[0]["class_name"] == "firearm"

    def test_get_events_by_class(self, logger):
        for _ in range(3):
            logger.log_event(class_name="animal", confidence=0.5,
                             camera_id="c", pole_id="p")
        logger.log_event(class_name="person", confidence=0.6,
                         camera_id="c", pole_id="p")
        results = logger.get_events_by_class("animal")
        assert len(results) == 3
        assert all(r["class_name"] == "animal" for r in results)

    def test_get_high_priority_events(self, logger):
        logger.log_event(class_name="animal", confidence=0.5,
                         camera_id="c", pole_id="p",
                         alert_priority=EventLogger.PRIORITY_NORMAL)
        logger.log_event(class_name="firearm", confidence=0.9,
                         camera_id="c", pole_id="p",
                         alert_priority=EventLogger.PRIORITY_HIGH)
        high = logger.get_high_priority_events()
        assert len(high) == 1
        assert high[0]["class_name"] == "firearm"

    def test_get_nonexistent_event_returns_none(self, logger):
        result = logger.get_event("00000000-0000-0000-0000-000000000000")
        assert result is None

    def test_count_by_class(self, logger):
        logger.log_event(class_name="animal", confidence=0.5,
                         camera_id="c", pole_id="p")
        logger.log_event(class_name="animal", confidence=0.6,
                         camera_id="c", pole_id="p")
        logger.log_event(class_name="person", confidence=0.7,
                         camera_id="c", pole_id="p")
        counts = logger.count_by_class()
        assert counts["animal"] == 2
        assert counts["person"] == 1
        assert "firearm" not in counts


# ── Review status ─────────────────────────────────────────────────────────────

class TestReviewStatus:

    def test_update_review_status_to_reviewed(self, logger):
        eid = logger.log_event(class_name="person", confidence=0.7,
                               camera_id="c", pole_id="p")
        updated = logger.update_review_status(eid, EventLogger.REVIEWED, notes="Confirmed ranger")
        assert updated is True
        event = logger.get_event(eid)
        assert event["review_status"] == "reviewed"
        assert event["operator_notes"] == "Confirmed ranger"

    def test_update_review_status_invalid(self, logger):
        eid = logger.log_event(class_name="animal", confidence=0.5,
                               camera_id="c", pole_id="p")
        with pytest.raises(ValueError, match="Invalid review status"):
            logger.update_review_status(eid, "unknown_status")

    def test_update_nonexistent_event_returns_false(self, logger):
        updated = logger.update_review_status(
            "deadbeef-0000-0000-0000-000000000000", EventLogger.DISMISSED
        )
        assert updated is False


# ── Evidence path validation ──────────────────────────────────────────────────

class TestEvidencePathValidation:

    def test_rejects_path_outside_evidence_dir(self, logger):
        with pytest.raises(ValueError, match="outside the allowed evidence"):
            logger.log_event(
                class_name="firearm",
                confidence=0.9,
                camera_id="c",
                pole_id="p",
                evidence_path="/etc/passwd",
            )

    def test_accepts_valid_evidence_path(self, logger, tmp_path):
        # Create a file inside the evidence directory
        evidence_file = logger.evidence_dir / "test_evidence.jpg"
        evidence_file.write_bytes(b"FAKEJPEG")
        eid = logger.log_event(
            class_name="firearm",
            confidence=0.9,
            camera_id="c",
            pole_id="p",
            evidence_path=evidence_file,
        )
        event = logger.get_event(eid)
        assert event["evidence_path"] is not None
        assert "test_evidence.jpg" in event["evidence_path"]


# ── Context manager ───────────────────────────────────────────────────────────

class TestContextManager:

    def test_context_manager_closes_gracefully(self, tmp_path):
        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir()
        with EventLogger(tmp_path / "cm.db", evidence_dir) as el:
            eid = el.log_event(class_name="animal", confidence=0.5,
                               camera_id="c", pole_id="p")
            assert eid is not None
        # After __exit__ the connection should be closed
        # (no assertion needed — just must not raise)
