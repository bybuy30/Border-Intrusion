"""
src/alert_engine.py
===================
Configurable rule engine that decides alert priority for each detection.

Design principles
-----------------
- A detected person is NOT automatically labelled a trespasser or threat.
- A detected firearm is NOT proof of illegal activity.
- Firearm detections above a configurable confidence threshold generate a
  special-priority alert labelled:
      "Potential weapon detected — review required"
- Person + firearm spatial association uses explicit, documented overlap rules,
  not assumptions.  The association label clearly indicates it is observational,
  not a legal determination.
- All decisions are logged for human review.

Alert priorities
----------------
  "normal"  — detection recorded; no immediate escalation.
  "high"    — requires prompt human review.

Usage
-----
    from src.alert_engine import AlertEngine, AlertResult
    engine = AlertEngine(firearm_conf_threshold=0.40)

    result = engine.evaluate(
        class_name="firearm",
        confidence=0.85,
        bbox=(100, 200, 300, 400),
        concurrent_detections=[],   # other detections in the same frame
    )
    print(result.priority, result.label)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from src.detector import Detection

logger = logging.getLogger(__name__)

# Label constants
_FIREARM_LABEL = "Potential weapon detected — review required"
_PERSON_WITH_FIREARM_LABEL = (
    "Person and potential weapon observed in proximity — review required"
)
_NORMAL_LABEL = ""


@dataclass
class AlertResult:
    """Outcome produced by the alert engine for a single detection."""

    priority: str           # "normal" or "high"
    label: str              # Human-readable description (empty for normal)
    associated_ids: list[int]  # track_ids of spatially associated detections


class AlertEngine:
    """
    Evaluates detection results against configurable alert rules.

    Parameters
    ----------
    firearm_conf_threshold:
        Minimum confidence for a firearm detection to trigger a high-priority
        alert.  Detections below this threshold are still logged at normal
        priority.
    person_firearm_iou_threshold:
        Minimum bounding-box IoU overlap between a person and a firearm
        detection to record them as spatially associated.  The association
        is observational only — it does NOT indicate confirmed illegal activity.
    """

    PRIORITY_NORMAL = "normal"
    PRIORITY_HIGH = "high"

    def __init__(
        self,
        firearm_conf_threshold: float = 0.40,
        person_firearm_iou_threshold: float = 0.05,
    ) -> None:
        if not (0.0 < firearm_conf_threshold <= 1.0):
            raise ValueError(
                f"firearm_conf_threshold must be in (0, 1], "
                f"got {firearm_conf_threshold}"
            )
        self.firearm_conf_threshold = firearm_conf_threshold
        self.person_firearm_iou_threshold = person_firearm_iou_threshold

    # ── Public API ────────────────────────────────────────────────────────────

    def evaluate(
        self,
        *,
        class_name: str,
        confidence: float,
        bbox: tuple[float, float, float, float],
        concurrent_detections: List[Detection],
    ) -> AlertResult:
        """
        Evaluate a single detection and return an AlertResult.

        Parameters
        ----------
        class_name:
            Detected class (``"animal"``, ``"person"``, ``"firearm"``).
        confidence:
            Model confidence for this detection.
        bbox:
            ``(x1, y1, x2, y2)`` bounding box of this detection.
        concurrent_detections:
            All other detections in the same frame, used for spatial rules.

        Returns
        -------
        AlertResult
            Contains priority, label, and any associated track IDs.
        """
        class_name_lower = class_name.lower()

        if class_name_lower == "firearm":
            return self._evaluate_firearm(confidence, bbox, concurrent_detections)

        if class_name_lower == "person":
            return self._evaluate_person(bbox, concurrent_detections)

        # Animal or unknown class — normal priority
        return AlertResult(
            priority=self.PRIORITY_NORMAL,
            label=_NORMAL_LABEL,
            associated_ids=[],
        )

    def evaluate_frame(
        self, detections: List[Detection]
    ) -> dict[int, AlertResult]:
        """
        Evaluate all detections in a frame at once.

        Parameters
        ----------
        detections:
            All Detection objects for one frame.

        Returns
        -------
        dict[int, AlertResult]
            Maps the index of each detection to its AlertResult.
        """
        results: dict[int, AlertResult] = {}
        for idx, det in enumerate(detections):
            others = [d for i, d in enumerate(detections) if i != idx]
            results[idx] = self.evaluate(
                class_name=det.class_name,
                confidence=det.confidence,
                bbox=det.bbox_xyxy,
                concurrent_detections=others,
            )
        return results

    # ── Private rule implementations ──────────────────────────────────────────

    def _evaluate_firearm(
        self,
        confidence: float,
        bbox: tuple[float, float, float, float],
        others: List[Detection],
    ) -> AlertResult:
        """Apply firearm-specific alert rules."""
        if confidence < self.firearm_conf_threshold:
            logger.debug(
                "Firearm below alert threshold (%.2f < %.2f) — normal priority.",
                confidence,
                self.firearm_conf_threshold,
            )
            return AlertResult(
                priority=self.PRIORITY_NORMAL,
                label=_NORMAL_LABEL,
                associated_ids=[],
            )

        # High-priority alert — find nearby persons
        nearby_person_ids: list[int] = []
        for other in others:
            if other.class_name.lower() == "person":
                overlap = self._iou(bbox, other.bbox_xyxy)
                if overlap >= self.person_firearm_iou_threshold:
                    if other.track_id is not None:
                        nearby_person_ids.append(other.track_id)

        label = (
            _PERSON_WITH_FIREARM_LABEL if nearby_person_ids else _FIREARM_LABEL
        )
        logger.warning("High-priority alert: %s", label)
        return AlertResult(
            priority=self.PRIORITY_HIGH,
            label=label,
            associated_ids=nearby_person_ids,
        )

    def _evaluate_person(
        self,
        bbox: tuple[float, float, float, float],
        others: List[Detection],
    ) -> AlertResult:
        """Apply person-specific alert rules (none currently — normal priority)."""
        # A person alone is not escalated.  Future rules (e.g. geofence
        # violation, after-hours detection) can be added here.
        return AlertResult(
            priority=self.PRIORITY_NORMAL,
            label=_NORMAL_LABEL,
            associated_ids=[],
        )

    @staticmethod
    def _iou(
        box_a: tuple[float, float, float, float],
        box_b: tuple[float, float, float, float],
    ) -> float:
        """
        Compute the Intersection over Union (IoU) of two bounding boxes.

        Parameters
        ----------
        box_a, box_b:
            ``(x1, y1, x2, y2)`` bounding boxes.

        Returns
        -------
        float
            IoU in [0.0, 1.0].  Returns 0.0 when either box has zero area.
        """
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)

        inter_w = max(0.0, inter_x2 - inter_x1)
        inter_h = max(0.0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h

        area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
        area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)

        union_area = area_a + area_b - inter_area
        if union_area <= 0:
            return 0.0
        return inter_area / union_area
