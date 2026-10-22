# 🌲 Forest Intrusion Detection System

A lightweight, modular computer vision system built on **YOLOv8n** that detects wildlife, people, and firearms in forest surveillance footage. Training is designed for **Google Colab** (GPU); local inference and the Streamlit UI run on **CPU**.

---

## Table of contents

1. [Project architecture](#project-architecture)
2. [Prerequisites](#prerequisites)
3. [Local environment setup](#local-environment-setup)
4. [Dataset acquisition and preparation](#dataset-acquisition-and-preparation)
5. [Colab notebook execution](#colab-notebook-execution)
6. [Training and evaluation](#training-and-evaluation)
7. [Running image / video inference](#running-image--video-inference)
8. [Viewing events and evidence](#viewing-events-and-evidence)
9. [Troubleshooting](#troubleshooting)
10. [Limitations and responsible use](#limitations-and-responsible-use)

---

## Project architecture

```
forest-intrusion/
├── app.py                    Streamlit UI (upload → detect → log)
├── configs/
│   ├── data.yaml             YOLO dataset descriptor (3 classes)
│   └── training.yaml         Training hyper-parameters
├── notebooks/
│   └── forest_yolo_training.ipynb   Full Colab training notebook
├── datasets/forest/          Images and YOLO labels (not committed)
├── scripts/
│   ├── download_datasets.py  Dataset acquisition guide + Roboflow helper
│   ├── inspect_dataset.py    Count images, visualise samples
│   ├── validate_dataset.py   Validate labels, detect corruption
│   ├── prepare_dataset.py    Class remapping, COCO→YOLO, train/val/test split
│   ├── train.py              CLI training launcher
│   ├── evaluate.py           Test-set evaluation + metrics JSON
│   └── export_model.py       Copy / export / send to Google Drive
├── src/
│   ├── config.py             Centralised Settings (reads .env)
│   ├── detector.py           YOLOv8 detection wrapper
│   ├── tracker.py            ByteTrack / BoT-SORT wrapper
│   ├── alert_engine.py       Priority rules (firearm alerts, spatial association)
│   ├── event_logger.py       SQLite event storage
│   └── evidence_store.py     JPEG evidence image writer
├── storage/
│   ├── events/               SQLite database files
│   └── evidence/             Evidence crop images
├── models/                   Place trained best.pt here
├── runs/                     Training and evaluation output directories
├── test_videos/              Short clips for local testing
└── tests/                    pytest unit tests
```

**Data flow:**  
video / image → `Detector` → `AlertEngine` → `EventLogger` + `EvidenceStore` → Streamlit UI / dashboard

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.10 or 3.11 |
| pip | 23+ |
| Google account | For Colab training |

No NVIDIA GPU is required locally. Training on CPU is supported but extremely slow — use Colab.

---

## Local environment setup

### Windows PowerShell

```powershell
# 1. Clone or download the project
cd forest-intrusion

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Copy the example environment file
Copy-Item .env.example .env
# Edit .env if you want to change camera IDs or thresholds

# 5. Verify the installation
python -c "from ultralytics import YOLO; print('ultralytics OK')"
python -c "import streamlit; print('streamlit OK')"
```

### macOS / Linux (bash)

```bash
cd forest-intrusion
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

---

## Dataset acquisition and preparation

Training requires real images and YOLO-format annotations.

```powershell
# See available sources and download instructions
python scripts/download_datasets.py --list
python scripts/download_datasets.py --manual
```

### Quick start with Roboflow

1. Create a free account at <https://roboflow.com/>.
2. Find a project with `animal` / `person` annotations (check the licence).
3. Add `ROBOFLOW_API_KEY=<your_key>` to `.env`.
4. Run:

```powershell
pip install roboflow
python scripts/download_datasets.py --roboflow --workspace <name> --project <slug>
```

### After downloading

```powershell
# 1. Create configs/class_map.json (see datasets/forest/README.md for format)

# 2. Remap labels to the three target classes
python scripts/prepare_dataset.py --remap --mapping configs/class_map.json

# 3. If images are in a flat directory, create the split
python scripts/prepare_dataset.py --split --images-dir datasets/raw/images --update-yaml

# 4. Validate the result
python scripts/inspect_dataset.py
python scripts/validate_dataset.py
```

---

## Colab notebook execution

### First time

1. Open Google Drive.
2. Upload the entire `forest-intrusion/` project folder to your Drive
   (or clone the repo directly from Colab using `!git clone ...`).
3. Open `notebooks/forest_yolo_training.ipynb` in **Google Colab**
   (right-click → Open with → Google Colaboratory).
4. Set the runtime to **GPU**: Runtime → Change runtime type → T4 GPU.
5. Run cells from top to bottom.

### Cell-by-cell guide

| Section | What to do |
|---------|-----------|
| Environment setup | Run as-is; installs packages automatically |
| GPU check | Verify a GPU is shown; if not, change runtime |
| Mount Drive | Run to persist datasets and weights across sessions |
| Dataset instructions | Follow the printed instructions; add images manually |
| Dataset inspection | Run after adding images to verify class distribution |
| Training | Runs 20 epochs; adjust batch size if OOM errors appear |
| Evaluation | Runs automatically after training |
| Inference | Upload a test image when prompted |
| Export | Saves `best.pt` to Google Drive |

### After training — copy weights locally

In Colab, after training completes:

```python
# In a Colab cell:
from google.colab import files
files.download('/content/runs/train/forest_v1/weights/best.pt')
```

Then, locally:

```powershell
# Place the downloaded file in models/
Copy-Item ~\Downloads\best.pt forest-intrusion\models\best.pt
```

---

## Training and evaluation

### Training from the command line (CPU or Colab terminal)

```powershell
# Basic run (uses configs/training.yaml)
python scripts/train.py

# Override epochs and batch
python scripts/train.py --epochs 50 --batch 4

# Resume interrupted training
python scripts/train.py --resume runs/train/forest_v1/weights/last.pt
```

### Evaluation on the test set

```powershell
# Evaluate best.pt on the held-out test set
python scripts/evaluate.py --weights models/best.pt --split test

# Results saved to runs/evaluate/<timestamp>/metrics.json
```

### Export for deployment

```powershell
# Copy best.pt from a training run
python scripts/export_model.py --copy runs/train/forest_v1/weights/best.pt

# Export to ONNX for CPU deployment
python scripts/export_model.py --export --format onnx

# Save to Google Drive (from Colab)
python scripts/export_model.py --gdrive /content/drive/MyDrive/models
```

---

## Running image / video inference

### Streamlit app

```powershell
streamlit run app.py
```

Open <http://localhost:8501> in your browser. Upload an image or video, then click
through the Detect tab to see annotated results and logged events.

### Python API

```python
from src.detector import Detector

detector = Detector("models/best.pt", conf=0.35)

# Single image
detections = detector.detect_image("path/to/image.jpg")
for d in detections:
    print(d)

# Video — yields per-frame lists
for frame_dets in detector.detect_video("test_videos/clip.mp4"):
    print(frame_dets)
```

---

## Viewing events and evidence

Events are stored in `storage/events/events.db` (SQLite).

```python
from src.event_logger import EventLogger
from src.config import Settings

cfg = Settings()
with EventLogger(cfg.database_path, cfg.evidence_dir) as el:
    # Recent events
    for event in el.get_recent_events(limit=20):
        print(event)

    # High-priority alerts only
    for event in el.get_high_priority_events():
        print(event["alert_label"], event["server_ts"])

    # Mark an event as reviewed
    el.update_review_status(event_id, "reviewed", notes="Confirmed ranger patrol")
```

Evidence images are saved to `storage/evidence/` as JPEG files.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModelNotFoundError` | Copy `best.pt` to `models/` after training |
| `No training images found` | Run `scripts/prepare_dataset.py` first |
| `CUDA out of memory` | Reduce `batch` in `configs/training.yaml` to 4 or 2 |
| `Workers` errors on Windows | Set `workers: 0` in `configs/training.yaml` |
| Streamlit blank page | Check that `streamlit run app.py` is running without errors |
| `roboflow` not found | `pip install roboflow` separately (not in core requirements) |
| PowerShell execution policy | Run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |

---

## Limitations and responsible use

- **Detection is not identification.** A detected person is not evidence of trespass.
- **Firearm alerts require human review.** The label "Potential weapon detected — review required" is an automated observation, not a legal determination.
- **No facial recognition** is implemented or intended.
- **Tracking IDs are temporary** session identifiers and do not identify real individuals across sessions.
- **Accuracy depends entirely on training data.** Performance on new camera placements or lighting conditions may be poor without additional fine-tuning.
- **Do not use this system** as the sole basis for restricting access, detaining individuals, or initiating law enforcement action.
- Keep datasets, model weights, and event logs secure. Do not expose the SQLite database or evidence images publicly.
