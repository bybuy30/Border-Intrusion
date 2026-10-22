"""
src/detector.py
===============
Reusable YOLOv8 detection wrapper.

Responsibilities
----------------
- Load a trained YOLOv8 model (nano or any other size).
- Accept a single image (NumPy array or file path), a video file path, or a
  raw video frame.
- Return structured detection results (bounding boxes, class IDs, names,
  confidence scores).
- Run on CPU when no compatible GPU is available.
- Raise clear, informative exceptions for invalid inputs.

Usage
-----
    from src.detector import Detector
    detector = Detector("models/best.pt", conf=0.35, iou=0.45)

    # Single image
    results = detector.detect_image("frame.jpg")
    for r in results:
        print(r)

    # Video file — yields per-frame result lists
    for frame_results in detector.detect_video("clip.mp4"):
        print(frame_results)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, List

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """A single object detection result."""

    bbox_xyxy: tuple[float, float, float, float]   # x1, y1, x2, y2 (pixels)
    class_id: int
    class_name: str
    confidence: float
    track_id: int | None = None                     # Populated by Tracker

    def __repr__(self) -> str:
        tid = f" track={self.track_id}" if self.track_id is not None else ""
        x1, y1, x2, y2 = self.bbox_xyxy
        return (
            f"Detection(class={self.class_name!r}, conf={self.confidence:.2f}, "
            f"bbox=[{x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}]{tid})"
        )


class ModelNotFoundError(FileNotFoundError):
    """Raised when the model weights file does not exist."""


class Detector:
    """
    Thin wrapper around an Ultralytics YOLOv8 model.

    Parameters
    ----------
    model_path:
        Path to the .pt weights file.  Must exist on disk.
    conf:
        Minimum confidence score to keep a detection (0.0–1.0).
    iou:
        IoU threshold used during non-maximum suppression (0.0–1.0).
    device:
        PyTorch device string, e.g. ``"cpu"``, ``"cuda:0"``.
        Pass ``None`` to let Ultralytics choose automatically.
    verbose:
        Whether to print per-inference Ultralytics logs.
    """

    def __init__(
        self,
        model_path: str | Path,
        conf: float = 0.35,
        iou: float = 0.45,
        device: str | None = None,
        verbose: bool = False,
    ) -> None:
        self._model_path = Path(model_path)
        self.conf = conf
        self.iou = iou
        self.device = device
        self.verbose = verbose
        self._model = self._load_model()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_model(self):
        """Load the YOLO model, raising a clear error when not found."""
        if not self._model_path.exists():
            raise ModelNotFoundError(
                f"Model weights not found: {self._model_path}\n"
                "Train the model in the Colab notebook and copy best.pt to models/."
            )
        try:
            from ultralytics import YOLO  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "ultralytics is not installed. Run: pip install ultralytics"
            ) from exc

        logger.info("Loading model from %s", self._model_path)
        model = YOLO(str(self._model_path))
        return model

    def _parse_results(self, ultralytics_results) -> List[Detection]:
        """Convert an Ultralytics Results object into a list of Detection."""
        detections: List[Detection] = []
        for result in ultralytics_results:
            if result.boxes is None:
                continue
            boxes = result.boxes
            names: dict[int, str] = result.names  # {id: name}
            for i in range(len(boxes)):
                xyxy = boxes.xyxy[i].cpu().numpy().tolist()   # [x1,y1,x2,y2]
                cls_id = int(boxes.cls[i].cpu().item())
                conf = float(boxes.conf[i].cpu().item())
                cls_name = names.get(cls_id, str(cls_id))
                detections.append(
                    Detection(
                        bbox_xyxy=(xyxy[0], xyxy[1], xyxy[2], xyxy[3]),
                        class_id=cls_id,
                        class_name=cls_name,
                        confidence=conf,
                    )
                )
        return detections

    # ── Public API ────────────────────────────────────────────────────────────

    def detect_image(
        self, source: str | Path | np.ndarray
    ) -> List[Detection]:
        """
        Run detection on a single image.

        Parameters
        ----------
        source:
            File path (str or Path) or a BGR NumPy array (as returned by
            ``cv2.imread``).

        Returns
        -------
        List[Detection]
            All detections above the configured confidence threshold.
        """
        if isinstance(source, (str, Path)):
            path = Path(source)
            if not path.exists():
                raise FileNotFoundError(f"Image not found: {path}")
            source = str(path)

        kwargs: dict = dict(
            source=source,
            conf=self.conf,
            iou=self.iou,
            verbose=self.verbose,
        )
        if self.device is not None:
            kwargs["device"] = self.device

        results = self._model.predict(**kwargs)
        return self._parse_results(results)

    def detect_video(
        self, video_path: str | Path
    ) -> Generator[List[Detection], None, None]:
        """
        Run detection on every frame of a video file.

        Yields per-frame detection lists. The caller is responsible for
        combining these with tracking information if required.

        Parameters
        ----------
        video_path:
            Path to a video file supported by OpenCV (mp4, avi, mov, …).

        Yields
        ------
        List[Detection]
            Detections for one frame (may be empty).
        """
        if cv2 is None:
            raise ImportError(
                "opencv-python is required for video detection. "
                "Run: pip install opencv-python"
            )
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"OpenCV could not open video: {video_path}")

        frame_idx = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                detections = self.detect_image(frame)
                yield detections
                frame_idx += 1
        finally:
            cap.release()

        logger.info("Processed %d frames from %s", frame_idx, video_path)

    @property
    def class_names(self) -> dict[int, str]:
        """Return the class name mapping from the loaded model."""
        return self._model.names  # type: ignore[return-value]
