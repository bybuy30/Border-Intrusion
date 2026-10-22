"""
app.py
======
Streamlit prototype for the Forest Intrusion Detection System.

Features
--------
- Upload an image or video and run YOLOv8 detection.
- Display annotated results with bounding boxes, class names, and confidence.
- Save detection events to SQLite via EventLogger.
- Save evidence crops via EvidenceStore.
- Review recent detection events in a table.
- High-priority (firearm) alerts are highlighted in red.

Run
---
    streamlit run app.py

The detector and event-processing logic live entirely in src/ — this file
is just the UI layer and can be replaced by a React frontend later.

Limitations
-----------
- No live camera feed is provided. Upload a file or use a sample video.
- The model weights (models/best.pt) must exist before detection can run.
  Train in Colab and copy best.pt to models/ first.
- CPU inference is supported but slow for large videos.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import List

import cv2
import numpy as np

# ── Path setup ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from src.alert_engine import AlertEngine
from src.config import Settings
from src.detector import Detection, Detector, ModelNotFoundError
from src.event_logger import EventLogger
from src.evidence_store import EvidenceStore

# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Forest Intrusion Detection",
    page_icon="🌲",
    layout="wide",
)


# ── Cached resource loaders ───────────────────────────────────────────────────

@st.cache_resource
def load_settings() -> Settings:
    return Settings()


@st.cache_resource
def load_detector(weights: str, conf: float, iou: float) -> Detector | None:
    try:
        return Detector(weights, conf=conf, iou=iou)
    except ModelNotFoundError as e:
        return None


@st.cache_resource
def load_event_logger(db_path: str, evidence_dir: str) -> EventLogger:
    return EventLogger(db_path=db_path, evidence_dir=evidence_dir)


@st.cache_resource
def load_evidence_store(evidence_dir: str) -> EvidenceStore:
    return EvidenceStore(evidence_dir=evidence_dir)


@st.cache_resource
def load_alert_engine(threshold: float) -> AlertEngine:
    return AlertEngine(firearm_conf_threshold=threshold)


# ── Drawing helpers ───────────────────────────────────────────────────────────

CLASS_COLOURS: dict[str, tuple[int, int, int]] = {
    "animal":  (0, 200, 0),
    "person":  (0, 140, 255),
    "firearm": (0, 0, 220),
}
DEFAULT_COLOUR = (180, 180, 180)


def draw_detections(frame: np.ndarray, detections: List[Detection]) -> np.ndarray:
    """Return a copy of frame with bounding boxes and labels drawn."""
    out = frame.copy()
    for det in detections:
        x1, y1, x2, y2 = map(int, det.bbox_xyxy)
        colour = CLASS_COLOURS.get(det.class_name, DEFAULT_COLOUR)
        cv2.rectangle(out, (x1, y1), (x2, y2), colour, 2)
        label = f"{det.class_name} {det.confidence:.2f}"
        if det.track_id is not None:
            label += f" #{det.track_id}"
        cv2.putText(
            out, label, (x1, max(y1 - 6, 10)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, colour, 2,
        )
    return out


# ── Detection processing ──────────────────────────────────────────────────────

def process_detections(
    frame: np.ndarray,
    detections: List[Detection],
    cfg: Settings,
    event_logger: EventLogger,
    evidence_store: EvidenceStore,
    alert_engine: AlertEngine,
) -> list[dict]:
    """Log each detection as an event and save evidence. Return event summaries."""
    summaries = []
    alert_results = alert_engine.evaluate_frame(detections)

    for idx, det in enumerate(detections):
        alert = alert_results[idx]
        # Save evidence crop
        try:
            ev_path = evidence_store.save_crop(
                frame=frame,
                bbox=det.bbox_xyxy,
                class_name=det.class_name,
                event_id="preview",
            )
        except Exception:
            ev_path = None

        eid = event_logger.log_event(
            class_name=det.class_name,
            confidence=det.confidence,
            camera_id=cfg.camera_id,
            pole_id=cfg.pole_id,
            bbox=det.bbox_xyxy,
            track_id=det.track_id,
            alert_priority=alert.priority,
            alert_label=alert.label or None,
            evidence_path=ev_path,
        )
        summaries.append({
            "event_id":  eid,
            "class":     det.class_name,
            "conf":      f"{det.confidence:.2f}",
            "priority":  alert.priority,
            "alert":     alert.label or "—",
        })
    return summaries


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar(cfg: Settings) -> tuple[float, float, float]:
    st.sidebar.header("⚙️ Settings")

    conf = st.sidebar.slider(
        "Confidence threshold",
        min_value=0.10, max_value=0.95,
        value=float(cfg.confidence_threshold), step=0.05,
    )
    iou = st.sidebar.slider(
        "IoU (NMS) threshold",
        min_value=0.10, max_value=0.95,
        value=float(cfg.iou_threshold), step=0.05,
    )
    firearm_thresh = st.sidebar.slider(
        "Firearm alert threshold",
        min_value=0.10, max_value=0.95,
        value=float(cfg.firearm_alert_threshold), step=0.05,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "**Model weights**\n\n"
        f"`{cfg.model_weights}`"
    )
    if not cfg.model_weights.exists():
        st.sidebar.warning(
            "⚠️ Model weights not found.\n\n"
            "Train in Google Colab and copy `best.pt` to `models/`."
        )

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "**Responsible use**\n\n"
        "Detection results are for review only. A detected person or firearm "
        "is not evidence of illegal activity. All firearm alerts require human "
        "review before any action is taken."
    )
    return conf, iou, firearm_thresh


# ── Main UI ───────────────────────────────────────────────────────────────────

def main() -> None:
    cfg = load_settings()

    st.title("🌲 Forest Intrusion Detection System")
    st.caption(
        "YOLOv8n · Classes: animal · person · firearm  |  "
        "All firearm alerts require human review."
    )

    conf, iou, firearm_thresh = render_sidebar(cfg)

    detector = load_detector(str(cfg.model_weights), conf=conf, iou=iou)
    event_logger = load_event_logger(
        str(cfg.database_path), str(cfg.evidence_dir)
    )
    evidence_store = load_evidence_store(str(cfg.evidence_dir))
    alert_engine   = load_alert_engine(firearm_thresh)

    tab_detect, tab_events = st.tabs(["🔍 Detect", "📋 Recent Events"])

    # ── Detect tab ────────────────────────────────────────────────────────────
    with tab_detect:
        if detector is None:
            st.error(
                "Model weights not found at `models/best.pt`.\n\n"
                "1. Open `notebooks/forest_yolo_training.ipynb` in Google Colab.\n"
                "2. Train the model.\n"
                "3. Download `best.pt` and place it in `models/`."
            )
            return

        upload_type = st.radio(
            "Input type", ["Image", "Video"], horizontal=True
        )

        if upload_type == "Image":
            uploaded = st.file_uploader(
                "Upload an image", type=["jpg", "jpeg", "png", "bmp", "webp"]
            )
            if uploaded:
                file_bytes = np.frombuffer(uploaded.read(), np.uint8)
                frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                if frame is None:
                    st.error("Could not decode image.")
                    return

                with st.spinner("Running detection…"):
                    detections = detector.detect_image(frame)

                annotated = draw_detections(frame, detections)
                col1, col2 = st.columns(2)
                with col1:
                    st.image(
                        cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                        caption="Original", use_container_width=True,
                    )
                with col2:
                    st.image(
                        cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB),
                        caption=f"Detections ({len(detections)} found)",
                        use_container_width=True,
                    )

                if detections:
                    summaries = process_detections(
                        frame, detections, cfg,
                        event_logger, evidence_store, alert_engine,
                    )
                    _render_detection_table(summaries)
                else:
                    st.info("No objects detected above the confidence threshold.")

        else:  # Video
            uploaded = st.file_uploader(
                "Upload a video", type=["mp4", "avi", "mov", "mkv"]
            )
            if uploaded:
                with tempfile.NamedTemporaryFile(
                    suffix=Path(uploaded.name).suffix, delete=False
                ) as tmp:
                    tmp.write(uploaded.read())
                    tmp_path = Path(tmp.name)

                st.info(
                    "Processing video frame by frame. For long videos this "
                    "may take a while on CPU."
                )
                progress = st.progress(0)
                status_text = st.empty()

                cap = cv2.VideoCapture(str(tmp_path))
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
                cap.release()

                all_summaries: list[dict] = []
                preview_frame: np.ndarray | None = None
                preview_annotated: np.ndarray | None = None

                frame_idx = 0
                for frame_dets in detector.detect_video(tmp_path):
                    # Read raw frame for evidence
                    if preview_frame is None and frame_idx == 0:
                        cap2 = cv2.VideoCapture(str(tmp_path))
                        ok, f = cap2.read()
                        if ok:
                            preview_frame = f
                            preview_annotated = draw_detections(f, frame_dets)
                        cap2.release()

                    if frame_dets:
                        frame_cap = cv2.VideoCapture(str(tmp_path))
                        frame_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                        ok, fr = frame_cap.read()
                        frame_cap.release()
                        if ok:
                            summaries = process_detections(
                                fr, frame_dets, cfg,
                                event_logger, evidence_store, alert_engine,
                            )
                            all_summaries.extend(summaries)

                    frame_idx += 1
                    progress.progress(min(frame_idx / total_frames, 1.0))
                    status_text.text(f"Frame {frame_idx}/{total_frames}")

                progress.empty()
                status_text.empty()
                tmp_path.unlink(missing_ok=True)

                if preview_frame is not None:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.image(
                            cv2.cvtColor(preview_frame, cv2.COLOR_BGR2RGB),
                            caption="First frame (original)",
                            use_container_width=True,
                        )
                    with col2:
                        st.image(
                            cv2.cvtColor(preview_annotated, cv2.COLOR_BGR2RGB),
                            caption="First frame (annotated)",
                            use_container_width=True,
                        )

                if all_summaries:
                    st.success(
                        f"Processed {frame_idx} frames — "
                        f"{len(all_summaries)} detection events logged."
                    )
                    _render_detection_table(all_summaries)
                else:
                    st.info("No detections found in the video.")

    # ── Events tab ────────────────────────────────────────────────────────────
    with tab_events:
        st.subheader("Recent Detection Events")
        events = event_logger.get_recent_events(limit=100)
        if not events:
            st.info("No events logged yet. Run detection on an image or video.")
        else:
            counts = event_logger.count_by_class()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total events",  sum(counts.values()))
            c2.metric("Animals",       counts.get("animal",  0))
            c3.metric("Persons",       counts.get("person",  0))
            c4.metric("Firearm alerts", counts.get("firearm", 0))

            display = [
                {
                    "Time (UTC)": e["server_ts"][:19],
                    "Camera":     e["camera_id"],
                    "Class":      e["class_name"],
                    "Conf":       f"{e['confidence']:.2f}",
                    "Priority":   e["alert_priority"],
                    "Alert":      (e["alert_label"] or "—")[:60],
                    "Status":     e["review_status"],
                }
                for e in events
            ]
            st.dataframe(display, use_container_width=True)

            high_priority = [e for e in events if e["alert_priority"] == "high"]
            if high_priority:
                st.error(
                    f"⚠️ {len(high_priority)} high-priority alert(s) pending review. "
                    "A trained operator must review these events before any action is taken."
                )


def _render_detection_table(summaries: list[dict]) -> None:
    if not summaries:
        return
    st.subheader("Detection Results")
    firearm_events = [s for s in summaries if s["class"] == "firearm"]
    if firearm_events:
        st.error(
            "⚠️ **Potential weapon detected — review required.**  "
            "This is an automated observation only. Do not treat this as "
            "confirmed evidence of illegal activity."
        )
    st.dataframe(summaries, use_container_width=True)


if __name__ == "__main__":
    main()
