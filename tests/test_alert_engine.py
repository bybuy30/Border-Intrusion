"""
tests/test_alert_engine.py
==========================
Unit tests for src/alert_engine.py.

These tests exercise all alert priority rules without requiring a model,
dataset, or any external dependencies beyond pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.alert_engine import AlertEngine, AlertResult
from src.detector import Detection


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def engine() -> AlertEngine:
    return AlertEngine(
        firearm_conf_threshold=0.40,
        person_firearm_iou_threshold=0.05,
    )


def make_detection(
    class_name: str,
    confidence: float,
    bbox: tuple = (100.0, 100.0, 200.0, 200.0),
    track_id: int | None = None,
) -> Detection:
    """Helper to build a Detection without needing a real model."""
    return Detection(
        bbox_xyxy=bbox,
        class_id={"animal": 0, "person": 1, "firearm": 2}.get(class_name, 99),
        class_name=class_name,
        confidence=confidence,
        track_id=track_id,
    )


# ── Animal detections ─────────────────────────────────────────────────────────

class TestAnimalAlerts:

    def test_animal_always_normal_priority(self, engine):
        result = engine.evaluate(
            class_name="animal",
            confidence=0.99,
            bbox=(0, 0, 100, 100),
            concurrent_detections=[],
        )
        assert result.priority == AlertEngine.PRIORITY_NORMAL

    def test_animal_empty_label(self, engine):
        result = engine.evaluate(
            class_name="animal",
            confidence=0.99,
            bbox=(0, 0, 100, 100),
            concurrent_detections=[],
        )
        assert result.label == ""

    def test_animal_no_associated_ids(self, engine):
        result = engine.evaluate(
            class_name="animal",
            confidence=0.6,
            bbox=(0, 0, 50, 50),
            concurrent_detections=[make_detection("person", 0.8)],
        )
        assert result.associated_ids == []


# ── Person detections ─────────────────────────────────────────────────────────

class TestPersonAlerts:

    def test_person_alone_normal_priority(self, engine):
        result = engine.evaluate(
            class_name="person",
            confidence=0.90,
            bbox=(0, 0, 100, 200),
            concurrent_detections=[],
        )
        assert result.priority == AlertEngine.PRIORITY_NORMAL

    def test_person_with_animal_still_normal(self, engine):
        result = engine.evaluate(
            class_name="person",
            confidence=0.85,
            bbox=(0, 0, 100, 200),
            concurrent_detections=[make_detection("animal", 0.75)],
        )
        assert result.priority == AlertEngine.PRIORITY_NORMAL


# ── Firearm detections ────────────────────────────────────────────────────────

class TestFirearmAlerts:

    def test_firearm_above_threshold_high_priority(self, engine):
        result = engine.evaluate(
            class_name="firearm",
            confidence=0.85,
            bbox=(0, 0, 100, 100),
            concurrent_detections=[],
        )
        assert result.priority == AlertEngine.PRIORITY_HIGH

    def test_firearm_below_threshold_normal_priority(self, engine):
        result = engine.evaluate(
            class_name="firearm",
            confidence=0.20,    # below 0.40 threshold
            bbox=(0, 0, 100, 100),
            concurrent_detections=[],
        )
        assert result.priority == AlertEngine.PRIORITY_NORMAL

    def test_firearm_at_exact_threshold_is_high(self, engine):
        # Confidence exactly equal to threshold should trigger high-priority
        result = engine.evaluate(
            class_name="firearm",
            confidence=0.40,
            bbox=(0, 0, 100, 100),
            concurrent_detections=[],
        )
        assert result.priority == AlertEngine.PRIORITY_HIGH

    def test_firearm_label_contains_review_required(self, engine):
        result = engine.evaluate(
            class_name="firearm",
            confidence=0.80,
            bbox=(0, 0, 100, 100),
            concurrent_detections=[],
        )
        assert "review required" in result.label.lower()
        assert "potential weapon" in result.label.lower()

    def test_firearm_label_not_automatic_conviction(self, engine):
        """Label must NOT say 'confirmed' or 'illegal'."""
        result = engine.evaluate(
            class_name="firearm",
            confidence=0.99,
            bbox=(0, 0, 100, 100),
            concurrent_detections=[],
        )
        assert "confirmed" not in result.label.lower()
        assert "illegal" not in result.label.lower()
        assert "crime" not in result.label.lower()


# ── Person + firearm spatial association ──────────────────────────────────────

class TestPersonFirearmAssociation:

    def _overlapping_person(self) -> Detection:
        """Return a person detection that overlaps heavily with (0,0,100,100)."""
        return make_detection("person", 0.80,
                              bbox=(50.0, 50.0, 150.0, 150.0),
                              track_id=7)

    def _non_overlapping_person(self) -> Detection:
        """Return a person detection far from (0,0,100,100)."""
        return make_detection("person", 0.80,
                              bbox=(500.0, 500.0, 600.0, 600.0),
                              track_id=8)

    def test_firearm_with_overlapping_person_associates(self, engine):
        result = engine.evaluate(
            class_name="firearm",
            confidence=0.85,
            bbox=(0.0, 0.0, 100.0, 100.0),
            concurrent_detections=[self._overlapping_person()],
        )
        assert result.priority == AlertEngine.PRIORITY_HIGH
        assert 7 in result.associated_ids
        assert "proximity" in result.label.lower()

    def test_firearm_with_non_overlapping_person_not_associated(self, engine):
        result = engine.evaluate(
            class_name="firearm",
            confidence=0.85,
            bbox=(0.0, 0.0, 100.0, 100.0),
            concurrent_detections=[self._non_overlapping_person()],
        )
        assert result.priority == AlertEngine.PRIORITY_HIGH
        assert result.associated_ids == []
        # Label should be the generic firearm label, not the proximity label
        assert "proximity" not in result.label.lower()

    def test_association_requires_track_id(self, engine):
        """Person without a track_id should NOT appear in associated_ids."""
        person_no_id = make_detection(
            "person", 0.80,
            bbox=(50.0, 50.0, 150.0, 150.0),
            track_id=None,   # no track ID
        )
        result = engine.evaluate(
            class_name="firearm",
            confidence=0.85,
            bbox=(0.0, 0.0, 100.0, 100.0),
            concurrent_detections=[person_no_id],
        )
        assert result.associated_ids == []

    def test_association_label_not_a_legal_determination(self, engine):
        """Proximity label must not imply confirmed criminal activity."""
        result = engine.evaluate(
            class_name="firearm",
            confidence=0.85,
            bbox=(0.0, 0.0, 100.0, 100.0),
            concurrent_detections=[self._overlapping_person()],
        )
        label_lower = result.label.lower()
        assert "confirmed" not in label_lower
        assert "illegal" not in label_lower
        assert "review required" in label_lower


# ── evaluate_frame ────────────────────────────────────────────────────────────

class TestEvaluateFrame:

    def test_returns_result_for_each_detection(self, engine):
        detections = [
            make_detection("animal",  0.80),
            make_detection("person",  0.70),
            make_detection("firearm", 0.90),
        ]
        results = engine.evaluate_frame(detections)
        assert len(results) == 3
        assert results[0].priority == AlertEngine.PRIORITY_NORMAL  # animal
        assert results[1].priority == AlertEngine.PRIORITY_NORMAL  # person
        assert results[2].priority == AlertEngine.PRIORITY_HIGH    # firearm

    def test_empty_frame(self, engine):
        results = engine.evaluate_frame([])
        assert results == {}


# ── IoU helper ────────────────────────────────────────────────────────────────

class TestIoU:

    def test_identical_boxes_iou_is_one(self):
        iou = AlertEngine._iou((0, 0, 100, 100), (0, 0, 100, 100))
        assert iou == pytest.approx(1.0)

    def test_non_overlapping_boxes_iou_is_zero(self):
        iou = AlertEngine._iou((0, 0, 50, 50), (100, 100, 200, 200))
        assert iou == pytest.approx(0.0)

    def test_partial_overlap(self):
        # Two 100×100 boxes with 50×50 overlap
        iou = AlertEngine._iou((0, 0, 100, 100), (50, 50, 150, 150))
        # intersection = 50*50=2500, union = 2*10000-2500=17500
        expected = 2500 / 17500
        assert iou == pytest.approx(expected, abs=1e-4)

    def test_zero_area_box_returns_zero(self):
        iou = AlertEngine._iou((0, 0, 0, 0), (0, 0, 100, 100))
        assert iou == pytest.approx(0.0)


# ── Configuration validation ──────────────────────────────────────────────────

class TestConfiguration:

    def test_invalid_threshold_raises(self):
        with pytest.raises(ValueError):
            AlertEngine(firearm_conf_threshold=0.0)

    def test_threshold_above_one_raises(self):
        with pytest.raises(ValueError):
            AlertEngine(firearm_conf_threshold=1.5)

    def test_custom_threshold_respected(self):
        engine = AlertEngine(firearm_conf_threshold=0.80)
        # conf=0.75 is below the custom threshold → normal
        result = engine.evaluate(
            class_name="firearm",
            confidence=0.75,
            bbox=(0, 0, 100, 100),
            concurrent_detections=[],
        )
        assert result.priority == AlertEngine.PRIORITY_NORMAL
