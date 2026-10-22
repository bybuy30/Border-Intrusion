"""
app.py
======
Streamlit prototype for the Forest Intrusion Detection System.

Features
--------
- Upload an image or video and run YOLOv8 detection.
- Display annotated results with bounding boxes, class names, and confidence.
- Save detection events to MongoDB via EventLogger.
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
from src.live_monitor import LiveMonitor, discover_cameras

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
def load_event_logger(uri: str, database: str, evidence_dir: str) -> EventLogger:
    return EventLogger(evidence_dir=evidence_dir, uri=uri, database_name=database)


@st.cache_resource
def load_evidence_store(evidence_dir: str) -> EvidenceStore:
    return EvidenceStore(evidence_dir=evidence_dir)


@st.cache_resource
def load_alert_engine(threshold: float) -> AlertEngine:
    return AlertEngine(firearm_conf_threshold=threshold)


@st.cache_resource
def load_live_monitor(_cfg: Settings, _detector: Detector, _event_logger: EventLogger, _alert_engine: AlertEngine) -> LiveMonitor:
    return LiveMonitor(_cfg, _detector, _event_logger, _alert_engine)


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
            f"Model weights not found at `{cfg.model_weights}`."
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
        "YOLO model predictions for operator review. "
        "All firearm alerts require human review."
    )

    try:
        event_logger = load_event_logger(cfg.mongodb_uri, cfg.mongodb_database, str(cfg.evidence_dir))
    except Exception as exc:
        st.error(f"MongoDB connection error: {exc}. Configure MONGODB_URI in .env and restart the app.")
        return

    conf, iou, firearm_thresh = render_sidebar(cfg)

    detector = load_detector(str(cfg.model_weights), conf=conf, iou=iou)
    evidence_store = load_evidence_store(str(cfg.evidence_dir))
    alert_engine   = load_alert_engine(firearm_thresh)

    st.subheader("Live Camera Feed")
    if detector is None:
        st.error(f"Model weights not found: {cfg.model_weights}")
        return
    cfg.class_names = {int(k): str(v) for k, v in detector.class_names.items()}
    st.caption("Checkpoint classes: " + ", ".join(f"{k}: {v}" for k, v in cfg.class_names.items()))
    monitor = load_live_monitor(cfg, detector, event_logger, alert_engine)
    cameras = discover_cameras(max_index=max(4, cfg.camera_index + 1), dshow=(sys.platform == "win32"))
    available = [x["camera_index"] for x in cameras]
    camera_index = st.selectbox("Camera index", sorted(set(available + [cfg.camera_index])),
                                index=(sorted(set(available + [cfg.camera_index])).index(cfg.camera_index)))
    c1, c2, c3 = st.columns(3)
    if c1.button("Start Monitoring", type="primary", disabled=monitor.status()["running"]):
        monitor.start(camera_index)
    if c2.button("Stop Monitoring", disabled=not monitor.status()["running"]):
        monitor.stop()
    state = monitor.status()
    c3.metric("Camera status", "Online" if state["connected"] else ("Connecting" if state["running"] else "Offline"))
    st.caption(f"Camera ID: {state['camera_id']} · Index: {state['camera_index']} · {state['message']}")
    if state.get("error"):
        st.error(f"Live monitor error: {state['error']}")

    @st.fragment(run_every=1)
    def render_live_frame():
        live_frame = monitor.latest_frame()
        if live_frame is not None:
            st.image(cv2.cvtColor(live_frame, cv2.COLOR_BGR2RGB), caption="Live model predictions", use_container_width=True)
        else:
            st.info("Start monitoring to view the selected camera.")
    render_live_frame()

    st.subheader("Pole Monitoring")
    poles = event_logger.get_poles()
    pole = next((p for p in poles if p.get("pole_id") == cfg.pole_id), None)
    if pole:
        st.dataframe([{"Pole ID": pole.get("pole_id"), "Pole name": pole.get("pole_name", cfg.pole_name),
                       "Location": pole.get("location", cfg.pole_location), "Camera ID": pole.get("camera_id"),
                       "Status": pole.get("status", "unconfigured"), "Last heartbeat": pole.get("last_heartbeat"),
                       "Latest alert": pole.get("latest_alert_status")}], use_container_width=True)
    else:
        st.info(f"Pole {cfg.pole_id} is unconfigured. It will report status after camera heartbeat.")

    events_now = event_logger.get_recent_events(limit=200)
    total_count = event_logger.count_events()
    people_count = event_logger.count_events({"class_name": "person"})
    high_count = event_logger.count_events({"alert_priority": {"$in": ["high", "critical"]}})
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total events", total_count); m2.metric("People detected", people_count)
    m3.metric("High-priority alerts", high_count); m4.metric("Camera", "Online" if state["connected"] else "Offline")

    st.subheader("Recent Alerts")
    if events_now:
        selected_event = st.selectbox("Select an event", events_now, format_func=lambda e: f"{e['event_id']} · {e['server_ts']} · {e['class_name']} {e['confidence']:.2f} · {e['alert_priority']} · {e.get('image_count', 0)} images")
        st.dataframe([{"Event ID": e["event_id"], "Timestamp": e["server_ts"], "Class": e["class_name"],
                       "Confidence": e["confidence"], "Priority": e["alert_priority"], "Pole": e["pole_id"],
                       "Images": e.get("image_count", 0)} for e in events_now[:20]], use_container_width=True)
        st.subheader("Burst Evidence Gallery")
        images = event_logger.get_event_images(selected_event["event_id"])
        if images:
            cols = st.columns(3)
            for i, image in enumerate(images):
                with cols[i % 3]:
                    if Path(image["local_path"]).is_file():
                        st.image(str(image["local_path"]), caption=f"Image {image['sequence']} · {image['capture_timestamp']}", use_container_width=True)
        else:
            st.info("No burst image records are available for this event.")
        st.caption(f"First detection: {selected_event.get('first_detection_time')} · Last detection: {selected_event.get('last_detection_time')} · Estimated duration: {selected_event.get('intrusion_duration_seconds') if selected_event.get('intrusion_duration_seconds') is not None else 'Unavailable (no reliable object association)'}")
    st.subheader("Event History")
    f1, f2, f3, f4 = st.columns(4)
    date_range = f1.date_input("Date range", value=())
    pole_options = ["All"] + [p.get("pole_id", "") for p in poles]
    pole_filter = f2.selectbox("Pole ID", pole_options)
    class_filter = f3.selectbox("Detected class", ["All", *sorted({e["class_name"] for e in events_now})])
    priority_filter = f4.selectbox("Priority", ["All", "normal", "high", "critical"])
    start_date = date_range[0].isoformat() + "T00:00:00+00:00" if len(date_range) > 0 else None
    end_date = date_range[-1].isoformat() + "T23:59:59+00:00" if len(date_range) > 1 else None
    history = event_logger.query_events(start=start_date, end=end_date,
        pole_id=None if pole_filter == "All" else pole_filter,
        class_name=None if class_filter == "All" else class_filter,
        priority=None if priority_filter == "All" else priority_filter, limit=500)
    st.dataframe([{"Event ID": e["event_id"], "Timestamp": e["server_ts"], "Class": e["class_name"],
                   "Confidence": e["confidence"], "Priority": e["alert_priority"],
                   "Pole ID": e["pole_id"], "Images": e.get("image_count", 0)} for e in history],
                 use_container_width=True)

    file_detection = st.expander("Optional image and video detection", expanded=False)

    # ── Detect tab ────────────────────────────────────────────────────────────
    with file_detection:
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
