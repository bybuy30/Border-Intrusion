"""
scripts/inspect_dataset.py
==========================
Inspect the dataset directory: count images, labels, and class distribution.
Visualise sample images with bounding boxes drawn from YOLO label files.

Usage
-----
    python scripts/inspect_dataset.py
    python scripts/inspect_dataset.py --split train
    python scripts/inspect_dataset.py --visualise --n 8
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATASET_ROOT = PROJECT_ROOT / "datasets" / "forest"
SPLITS = ["train", "val", "test"]

# Class name mapping (must match configs/data.yaml)
CLASS_NAMES = {0: "animal", 1: "person", 2: "firearm"}
# Distinct BGR colours per class
CLASS_COLOURS = {0: (0, 200, 0), 1: (0, 120, 255), 2: (0, 0, 220)}


# ── Inspection ────────────────────────────────────────────────────────────────

def inspect_split(split: str) -> dict:
    """Return image count, label count, and per-class annotation counts."""
    img_dir = DATASET_ROOT / "images" / split
    lbl_dir = DATASET_ROOT / "labels" / split

    if not img_dir.exists():
        return {"split": split, "status": "directory not found", "images": 0}

    images = list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png"))
    labels = list(lbl_dir.glob("*.txt")) if lbl_dir.exists() else []

    class_counts: dict[int, int] = {k: 0 for k in CLASS_NAMES}
    invalid_labels = 0

    for lbl_path in labels:
        try:
            for line in lbl_path.read_text().strip().splitlines():
                parts = line.split()
                if len(parts) < 5:
                    invalid_labels += 1
                    continue
                cls_id = int(parts[0])
                class_counts[cls_id] = class_counts.get(cls_id, 0) + 1
        except Exception:
            invalid_labels += 1

    return {
        "split": split,
        "images": len(images),
        "labels": len(labels),
        "unlabelled_images": len(images) - len(labels),
        "class_counts": {CLASS_NAMES.get(k, str(k)): v for k, v in class_counts.items() if v > 0},
        "invalid_label_lines": invalid_labels,
    }


def print_report(splits: list[str]) -> None:
    """Print a formatted inspection report."""
    total_images = 0
    print("\n" + "=" * 60)
    print(" Forest Dataset Inspection Report")
    print("=" * 60)

    for split in splits:
        info = inspect_split(split)
        print(f"\n  Split : {info['split']}")
        if info.get("status"):
            print(f"  Status: {info['status']}")
            continue
        print(f"  Images           : {info['images']}")
        print(f"  Labels           : {info['labels']}")
        print(f"  Unlabelled images: {info['unlabelled_images']}")
        print(f"  Invalid lines    : {info['invalid_label_lines']}")
        if info["class_counts"]:
            print("  Class distribution:")
            for cls, cnt in sorted(info["class_counts"].items()):
                print(f"    {cls:<12}: {cnt}")
        total_images += info["images"]

    print(f"\n  Total images across splits: {total_images}")
    print("=" * 60 + "\n")


# ── Visualisation ─────────────────────────────────────────────────────────────

def draw_yolo_labels(image: np.ndarray, label_path: Path) -> np.ndarray:
    """Draw YOLO-format bounding boxes onto an image."""
    h, w = image.shape[:2]
    img = image.copy()

    if not label_path.exists():
        return img

    for line in label_path.read_text().strip().splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        cls_id = int(parts[0])
        cx, cy, bw, bh = map(float, parts[1:5])

        x1 = int((cx - bw / 2) * w)
        y1 = int((cy - bh / 2) * h)
        x2 = int((cx + bw / 2) * w)
        y2 = int((cy + bh / 2) * h)

        colour = CLASS_COLOURS.get(cls_id, (200, 200, 200))
        cv2.rectangle(img, (x1, y1), (x2, y2), colour, 2)
        label = CLASS_NAMES.get(cls_id, str(cls_id))
        cv2.putText(
            img, label, (x1, max(y1 - 4, 10)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, colour, 2,
        )
    return img


def visualise_samples(split: str, n: int = 8) -> None:
    """Display n sample images with bounding boxes using matplotlib."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("ERROR: matplotlib not installed. Run: pip install matplotlib")
        return

    img_dir = DATASET_ROOT / "images" / split
    lbl_dir = DATASET_ROOT / "labels" / split

    images = sorted(list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png")))
    if not images:
        print(f"No images found in {img_dir}")
        return

    samples = images[:n]
    cols = min(4, len(samples))
    rows = (len(samples) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 4, rows * 3))
    axes = np.array(axes).flatten() if rows * cols > 1 else [axes]

    for ax, img_path in zip(axes, samples):
        img = cv2.imread(str(img_path))
        if img is None:
            ax.set_title("Could not read")
            ax.axis("off")
            continue
        lbl_path = lbl_dir / (img_path.stem + ".txt")
        img = draw_yolo_labels(img, lbl_path)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        ax.imshow(img_rgb)
        ax.set_title(img_path.name, fontsize=8)
        ax.axis("off")

    for ax in axes[len(samples):]:
        ax.axis("off")

    plt.suptitle(f"Split: {split} — {len(samples)} samples", fontsize=12)
    plt.tight_layout()
    plt.show()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect and visualise the forest dataset"
    )
    parser.add_argument(
        "--split",
        choices=SPLITS + ["all"],
        default="all",
        help="Which split to inspect (default: all)",
    )
    parser.add_argument(
        "--visualise",
        action="store_true",
        help="Show sample images with bounding boxes",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=8,
        help="Number of sample images to visualise (default: 8)",
    )
    args = parser.parse_args()

    splits = SPLITS if args.split == "all" else [args.split]
    print_report(splits)

    if args.visualise:
        for split in splits:
            visualise_samples(split, n=args.n)


if __name__ == "__main__":
    main()
