"""
scripts/train.py
================
Command-line training launcher for YOLOv8n on the forest dataset.

This script reads configs/training.yaml, optionally overrides individual
values from CLI arguments, checks that the dataset exists, and launches
a training run via the Ultralytics API.

It is designed to be run in Google Colab (GPU) but will fall back to CPU
if no compatible GPU is detected — note that CPU training is extremely slow
for anything beyond a toy test run.

Usage
-----
    # Basic run using configs/training.yaml defaults
    python scripts/train.py

    # Override epochs and batch size
    python scripts/train.py --epochs 50 --batch 16

    # Resume an interrupted run
    python scripts/train.py --resume runs/train/forest_v1/weights/last.pt

    # CPU-only explicit override
    python scripts/train.py --device cpu
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_PATH  = PROJECT_ROOT / "configs" / "training.yaml"
DATA_YAML    = PROJECT_ROOT / "configs" / "data.yaml"


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_training_config() -> dict:
    """Load configs/training.yaml and resolve relative paths."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Training config not found: {CONFIG_PATH}\n"
            "Ensure configs/training.yaml exists in the project root."
        )
    with CONFIG_PATH.open() as f:
        cfg = yaml.safe_load(f)
    return cfg


def check_dataset(data_yaml: Path) -> None:
    """Verify that the dataset config and at least a few images exist."""
    if not data_yaml.exists():
        raise FileNotFoundError(
            f"Dataset config not found: {data_yaml}\n"
            "Run scripts/prepare_dataset.py first."
        )
    with data_yaml.open() as f:
        ds_cfg = yaml.safe_load(f)

    dataset_root = Path(ds_cfg.get("path", "datasets/forest"))
    if not dataset_root.is_absolute():
        dataset_root = PROJECT_ROOT / dataset_root

    train_dir = dataset_root / ds_cfg.get("train", "images/train")
    images = list(train_dir.glob("*.jpg")) + list(train_dir.glob("*.png"))
    if not train_dir.exists() or not images:
        raise RuntimeError(
            f"No training images found in {train_dir}.\n"
            "Download and prepare a dataset first:\n"
            "  python scripts/download_datasets.py --manual\n"
            "  python scripts/prepare_dataset.py --help"
        )
    print(f"✓ Training images found: {len(images)} in {train_dir}")


def detect_device() -> str:
    """Return 'cuda:0' if a CUDA GPU is available, else 'cpu'."""
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            print(f"✓ GPU detected: {name}")
            return "cuda:0"
    except ImportError:
        pass
    print("⚠ No CUDA GPU detected — training will use CPU (very slow).")
    return "cpu"


# ── Training ──────────────────────────────────────────────────────────────────

def run_training(cfg: dict) -> None:
    """Launch a YOLOv8 training run with the given configuration dict."""
    try:
        from ultralytics import YOLO
    except ImportError:
        raise ImportError(
            "ultralytics is not installed.\n"
            "Run: pip install ultralytics"
        )

    # Resolve the data.yaml path to absolute so it works from any cwd
    data_path = cfg.get("data", "configs/data.yaml")
    if not Path(data_path).is_absolute():
        data_path = str(PROJECT_ROOT / data_path)
    cfg["data"] = data_path

    model_name = cfg.pop("model", "yolov8n.pt")
    print(f"\n{'=' * 60}")
    print(f"  Starting YOLOv8 training")
    print(f"  Model   : {model_name}")
    print(f"  Data    : {cfg['data']}")
    print(f"  Epochs  : {cfg.get('epochs', 20)}")
    print(f"  Batch   : {cfg.get('batch', 8)}")
    print(f"  Device  : {cfg.get('device', 'auto')}")
    print(f"{'=' * 60}\n")

    model = YOLO(model_name)   # Downloads yolov8n.pt on first run
    results = model.train(**cfg)

    best_weights = Path(results.save_dir) / "weights" / "best.pt"
    print(f"\n{'=' * 60}")
    print(f"  Training complete.")
    print(f"  Best weights : {best_weights}")
    print(f"  Copy to models/best.pt for inference:")
    print(f"    cp {best_weights} {PROJECT_ROOT / 'models' / 'best.pt'}")
    print(f"{'=' * 60}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train YOLOv8n on the forest intrusion dataset",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--epochs",  type=int,   help="Override number of epochs")
    parser.add_argument("--batch",   type=int,   help="Override batch size")
    parser.add_argument("--imgsz",   type=int,   help="Override image size")
    parser.add_argument("--device",  type=str,   help="Override device (cpu / cuda:0)")
    parser.add_argument("--workers", type=int,   help="Override DataLoader workers")
    parser.add_argument("--name",    type=str,   help="Override run name")
    parser.add_argument(
        "--resume",
        type=str,
        help="Path to last.pt to resume an interrupted run",
    )
    parser.add_argument(
        "--no-dataset-check",
        action="store_true",
        help="Skip dataset existence check (use when called from Colab)",
    )
    args = parser.parse_args()

    cfg = load_training_config()

    # Apply CLI overrides
    overrides = {
        "epochs":  args.epochs,
        "batch":   args.batch,
        "imgsz":   args.imgsz,
        "device":  args.device,
        "workers": args.workers,
        "name":    args.name,
    }
    for key, val in overrides.items():
        if val is not None:
            cfg[key] = val

    # Handle resume
    if args.resume:
        resume_path = Path(args.resume)
        if not resume_path.exists():
            print(f"ERROR: Resume weights not found: {resume_path}")
            sys.exit(1)
        cfg["resume"] = str(resume_path)
        print(f"Resuming training from {resume_path}")

    # Auto-detect device if not explicitly set
    if cfg.get("device") is None:
        cfg["device"] = detect_device()

    if not args.no_dataset_check:
        check_dataset(DATA_YAML)

    run_training(cfg)


if __name__ == "__main__":
    main()
