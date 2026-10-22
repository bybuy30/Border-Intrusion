"""
scripts/evaluate.py
===================
Evaluate a trained YOLOv8 model on the held-out test set and report metrics.

Outputs
-------
- Precision, Recall, mAP50, mAP50-95 per class and overall.
- Confusion matrix (saved to runs/evaluate/<name>/).
- Per-class F1 scores.
- Saves a JSON summary to runs/evaluate/<name>/metrics.json.

The test set is kept strictly separate from training and validation — this
script must only be run after the model is fully trained and the final
architecture is frozen. Do not tune hyperparameters based on test-set metrics.

Usage
-----
    # Evaluate using the default weights path from .env / config
    python scripts/evaluate.py

    # Specify weights explicitly
    python scripts/evaluate.py --weights models/best.pt

    # Evaluate on the validation set instead of test
    python scripts/evaluate.py --split val

    # Override confidence threshold
    python scripts/evaluate.py --conf 0.25
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATA_YAML   = PROJECT_ROOT / "configs" / "data.yaml"
RESULTS_DIR = PROJECT_ROOT / "runs" / "evaluate"


# ── Helpers ───────────────────────────────────────────────────────────────────

def check_weights(weights_path: Path) -> None:
    if not weights_path.exists():
        raise FileNotFoundError(
            f"Model weights not found: {weights_path}\n"
            "Train the model first and ensure best.pt is in models/ .\n"
            "In Colab: copy from /content/runs/train/.../weights/best.pt"
        )


def check_test_split(data_yaml: Path, split: str) -> None:
    """Verify that test images actually exist before evaluation."""
    with data_yaml.open() as f:
        cfg = yaml.safe_load(f)

    root = Path(cfg.get("path", "datasets/forest"))
    if not root.is_absolute():
        root = PROJECT_ROOT / root

    split_key = "val" if split == "val" else "test"
    img_dir = root / cfg.get(split_key, f"images/{split_key}")
    images = list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png"))

    if not images:
        raise RuntimeError(
            f"No images found for split='{split}' in {img_dir}.\n"
            "Ensure the dataset is prepared with train/val/test splits."
        )
    print(f"✓ {len(images)} images in {split} split.")


# ── Evaluation ────────────────────────────────────────────────────────────────

def run_evaluation(
    weights: Path,
    data_yaml: Path,
    split: str,
    conf: float,
    iou: float,
    imgsz: int,
    device: str,
    run_name: str,
) -> dict:
    """Run model.val() and return a metrics summary dictionary."""
    try:
        from ultralytics import YOLO
    except ImportError:
        raise ImportError("ultralytics not installed. Run: pip install ultralytics")

    out_dir = RESULTS_DIR / run_name
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"  Evaluating model")
    print(f"  Weights : {weights}")
    print(f"  Split   : {split}")
    print(f"  Conf    : {conf}")
    print(f"  Device  : {device}")
    print(f"{'=' * 60}\n")

    model = YOLO(str(weights))

    metrics = model.val(
        data=str(data_yaml.resolve()),
        split=split,
        conf=conf,
        iou=iou,
        imgsz=imgsz,
        device=device,
        plots=True,
        save_json=True,
        project=str(RESULTS_DIR),
        name=run_name,
        exist_ok=True,
    )

    # Extract scalar metrics
    summary = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "weights": str(weights),
        "split": split,
        "conf_threshold": conf,
        "iou_threshold": iou,
        "imgsz": imgsz,
        "metrics": {
            "precision":   float(metrics.box.mp),     # mean precision
            "recall":      float(metrics.box.mr),     # mean recall
            "mAP50":       float(metrics.box.map50),  # mAP @ IoU=0.50
            "mAP50_95":    float(metrics.box.map),    # mAP @ IoU=0.50:0.95
            "f1":          float(metrics.box.f1.mean()) if hasattr(metrics.box, "f1") else None,
        },
        "per_class": {},
    }

    # Per-class metrics
    try:
        class_names = model.names
        for i, cls_name in class_names.items():
            summary["per_class"][cls_name] = {
                "precision": float(metrics.box.p[i]) if i < len(metrics.box.p) else None,
                "recall":    float(metrics.box.r[i]) if i < len(metrics.box.r) else None,
                "mAP50":     float(metrics.box.ap50[i]) if i < len(metrics.box.ap50) else None,
                "mAP50_95":  float(metrics.box.ap[i])   if i < len(metrics.box.ap)   else None,
            }
    except Exception as e:
        print(f"  Note: per-class metrics unavailable ({e})")

    # Save JSON
    json_path = out_dir / "metrics.json"
    with json_path.open("w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Metrics saved to: {json_path}")

    # Print table
    _print_metrics_table(summary)

    return summary


def _print_metrics_table(summary: dict) -> None:
    m = summary["metrics"]
    print(f"\n{'=' * 60}")
    print(f"  Evaluation Results — split={summary['split']}")
    print(f"{'=' * 60}")
    print(f"  {'Metric':<20} {'Value':>10}")
    print(f"  {'-' * 32}")
    print(f"  {'Precision':<20} {m['precision']:>10.4f}")
    print(f"  {'Recall':<20} {m['recall']:>10.4f}")
    print(f"  {'mAP50':<20} {m['mAP50']:>10.4f}")
    print(f"  {'mAP50-95':<20} {m['mAP50_95']:>10.4f}")
    if m.get("f1") is not None:
        print(f"  {'F1 (mean)':<20} {m['f1']:>10.4f}")

    if summary.get("per_class"):
        print(f"\n  Per-class mAP50:")
        for cls, vals in summary["per_class"].items():
            ap = vals.get("mAP50")
            ap_str = f"{ap:.4f}" if ap is not None else "N/A"
            print(f"    {cls:<16}: {ap_str}")

    print(f"\n  ⚠  These metrics are only meaningful when trained on a")
    print(f"     representative, properly annotated dataset.")
    print(f"{'=' * 60}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate a trained YOLOv8 model on the forest test set",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--weights",
        default="models/best.pt",
        help="Path to trained .pt weights",
    )
    parser.add_argument(
        "--split",
        choices=["val", "test"],
        default="test",
        help="Dataset split to evaluate on",
    )
    parser.add_argument("--conf",  type=float, default=0.25)
    parser.add_argument("--iou",   type=float, default=0.45)
    parser.add_argument("--imgsz", type=int,   default=640)
    parser.add_argument("--device", default=None, help="cpu or cuda:0")
    parser.add_argument(
        "--name",
        default=None,
        help="Run name for output directory (default: auto-timestamp)",
    )
    args = parser.parse_args()

    weights = Path(args.weights)
    if not weights.is_absolute():
        weights = PROJECT_ROOT / weights

    check_weights(weights)
    check_test_split(DATA_YAML, args.split)

    # Auto-detect device
    device = args.device
    if device is None:
        try:
            import torch
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

    run_name = args.name or f"eval_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"

    run_evaluation(
        weights=weights,
        data_yaml=DATA_YAML,
        split=args.split,
        conf=args.conf,
        iou=args.iou,
        imgsz=args.imgsz,
        device=device,
        run_name=run_name,
    )


if __name__ == "__main__":
    main()
