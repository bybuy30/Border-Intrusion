"""
src/evidence_store.py
=====================
Saves cropped evidence images to disk with unique, collision-resistant filenames.

Design decisions
----------------
- One image per detection event (the bounding-box crop).
- Filename format: ``{timestamp}_{class_name}_{event_id[:8]}.jpg``
  Example: ``2026-10-21T14-32-05_firearm_a3f1b9c2.jpg``
- Images are written as JPEG with configurable quality to balance file size
  and evidential detail.
- Full-frame images can optionally be saved alongside crops.
- No entire videos are saved here; the caller is responsible for keeping
  video paths separate.
- Paths are validated against the evidence directory to prevent path traversal.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class EvidenceStore:
    """
    Saves and manages evidence images for detection events.

    Parameters
    ----------
    evidence_dir:
        Root directory for evidence images.  Created automatically.
    jpeg_quality:
        JPEG encoding quality (1–100).  Default 90 gives good quality at a
        reasonable file size.
    """

    def __init__(
        self,
        evidence_dir: str | Path,
        jpeg_quality: int = 90,
    ) -> None:
        self.evidence_dir = Path(evidence_dir).resolve()
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.jpeg_quality = max(1, min(100, jpeg_quality))

    # ── Public API ────────────────────────────────────────────────────────────

    def save_crop(
        self,
        frame: np.ndarray,
        bbox: tuple[float, float, float, float],
        class_name: str,
        event_id: str,
        padding_px: int = 10,
    ) -> Path:
        """
        Save a cropped region from a frame as JPEG evidence.

        Parameters
        ----------
        frame:
            Full BGR frame (as returned by OpenCV).
        bbox:
            Bounding box ``(x1, y1, x2, y2)`` in pixel coordinates.
        class_name:
            Detected class name used in the filename.
        event_id:
            UUID of the associated event (first 8 characters used in filename).
        padding_px:
            Extra pixels to include around the bounding box for context.

        Returns
        -------
        Path
            Absolute path to the saved image.

        Raises
        ------
        ValueError
            If the bounding box is entirely outside the frame boundaries.
        """
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = bbox
        # Apply padding and clamp to frame bounds
        x1_crop = max(0, int(x1) - padding_px)
        y1_crop = max(0, int(y1) - padding_px)
        x2_crop = min(w, int(x2) + padding_px)
        y2_crop = min(h, int(y2) + padding_px)

        if x2_crop <= x1_crop or y2_crop <= y1_crop:
            raise ValueError(
                f"Bounding box {bbox} produces an empty crop for a "
                f"{w}×{h} frame."
            )

        crop = frame[y1_crop:y2_crop, x1_crop:x2_crop]
        filename = self._make_filename(class_name, event_id)
        dest = self.evidence_dir / filename
        self._write_jpeg(crop, dest)
        logger.info("Evidence saved: %s", dest)
        return dest

    def save_full_frame(
        self,
        frame: np.ndarray,
        class_name: str,
        event_id: str,
    ) -> Path:
        """
        Save the entire frame as JPEG evidence (useful for context).

        Parameters
        ----------
        frame:
            Full BGR frame.
        class_name, event_id:
            Used in the filename.

        Returns
        -------
        Path
            Absolute path to the saved image.
        """
        filename = self._make_filename(f"{class_name}_full", event_id)
        dest = self.evidence_dir / filename
        self._write_jpeg(frame, dest)
        logger.info("Full-frame evidence saved: %s", dest)
        return dest

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_filename(self, class_name: str, event_id: str) -> str:
        """Generate a collision-resistant filename."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
        safe_class = class_name.replace(" ", "_").lower()
        short_id = event_id[:8] if len(event_id) >= 8 else event_id
        return f"{ts}_{safe_class}_{short_id}.jpg"

    def _write_jpeg(self, image: np.ndarray, dest: Path) -> None:
        """Encode and write a JPEG, raising on failure."""
        ok = cv2.imwrite(
            str(dest),
            image,
            [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality],
        )
        if not ok:
            raise OSError(f"Failed to write evidence image to {dest}")
