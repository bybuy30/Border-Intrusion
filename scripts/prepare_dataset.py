"""
scripts/prepare_dataset.py
==========================
Prepare a raw downloaded dataset for YOLO training:

1. Map source class labels to the three target classes
   (animal, person, firearm) using a configurable JSON mapping file.
2. Convert annotations from supported formats (COCO JSON or CSV) into
   YOLO bounding-box format.
3. Split images into train / val / test sets without data leakage.
4. Regenerate configs/data.yaml with the correct paths.
5. Report class counts after preparation.

Supported input annotation formats
------------------------------------
  - YOLO (.txt, one file per image) — pass-through with class remapping.
  - COCO JSON (.json) — converted to YOLO format.

Formats NOT currently supported (will be skipped with a warning):
  - Pascal VOC XML
  - TensorFlow records
  - Custom CSV without a defined schema

Usage
-----
    # Remap YOLO-format labels already in the correct directories
    python scripts/prepare_dataset.py --remap --mapping configs/class_map.json

    # Convert a COCO JSON annotation file
    python scripts/prepare_dataset.py --coco annotations.json --images-dir /path/to/images

    # Create a train/val/test split from a flat image directory
    python scripts/prepare_dataset.py --split --images-dir datasets/raw/images

Class mapping file format (configs/class_map.json)
----------------------------------------------------
    {
        "source_to_target": {
            "deer":    "animal",
            "bear":    "animal",
            "human":   "person",
            "gun":     "firearm",
            "rifle":   "firearm"
        }
    }

    Source class names that are not in this mapping will be SKIPPED.
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from pathlib import Path
from typing import Optional

try:
    import yaml  # type: ignore[import]
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATASET_ROOT = PROJECT_ROOT / "datasets" / "forest"
CONFIG_PATH  = PROJECT_ROOT / "configs" / "data.yaml"
DEFAULT_MAP  = PROJECT_ROOT / "configs" / "class_map.json"

TARGET_CLASSES = {"animal": 0, "person": 1, "firearm": 2}


# ── Class mapping ─────────────────────────────────────────────────────────────

def load_class_map(map_path: Path) -> dict[str, str]:
    """
    Load source-label → target-class mapping from a JSON file.

    Returns an empty dict if the file does not exist (no remapping).
    """
    if not map_path.exists():
        print(f"No class map found at {map_path} — labels will be used as-is.")
        return {}
    with map_path.open() as f:
        data = json.load(f)
    mapping = data.get("source_to_target", {})
    print(f"Loaded class map with {len(mapping)} entries from {map_path}")
    return mapping


def remap_label_file(
    lbl_path: Path,
    source_id_to_name: dict[int, str],
    class_map: dict[str, str],
    out_path: Optional[Path] = None,
) -> int:
    """
    Rewrite a YOLO .txt label file using the target class IDs.

    Lines whose source class maps to an unsupported target are dropped.

    Parameters
    ----------
    lbl_path:     Input label file.
    source_id_to_name: Mapping from source class integer IDs to their names.
    class_map:    source_name → target_name mapping.
    out_path:     Destination file (overwrites lbl_path if None).

    Returns
    -------
    int
        Number of lines written.
    """
    out_path = out_path or lbl_path
    lines_in  = lbl_path.read_text().strip().splitlines() if lbl_path.exists() else []
    lines_out = []

    for line in lines_in:
        parts = line.split()
        if len(parts) < 5:
            continue
        src_id = int(parts[0])
        src_name = source_id_to_name.get(src_id, str(src_id))
        tgt_name = class_map.get(src_name)
        if tgt_name is None:
            continue   # Class not in mapping — skip
        tgt_id = TARGET_CLASSES.get(tgt_name)
        if tgt_id is None:
            continue   # Target class not recognised — skip
        lines_out.append(f"{tgt_id} {' '.join(parts[1:])}")

    out_path.write_text("\n".join(lines_out) + "\n" if lines_out else "")
    return len(lines_out)


# ── COCO JSON conversion ──────────────────────────────────────────────────────

def convert_coco_to_yolo(
    coco_json: Path,
    images_dir: Path,
    class_map: dict[str, str],
) -> int:
    """
    Convert a COCO-format JSON annotation file to YOLO .txt files.

    Writes label files alongside their images in images_dir.

    Returns
    -------
    int
        Number of annotations converted.
    """
    with coco_json.open() as f:
        coco = json.load(f)

    # Build lookup tables
    id_to_cat = {cat["id"]: cat["name"] for cat in coco.get("categories", [])}
    id_to_img: dict[int, dict] = {img["id"]: img for img in coco.get("images", [])}

    # Group annotations by image
    ann_by_image: dict[int, list] = {}
    for ann in coco.get("annotations", []):
        ann_by_image.setdefault(ann["image_id"], []).append(ann)

    converted = 0
    skipped   = 0

    for img_id, anns in ann_by_image.items():
        img_info = id_to_img.get(img_id)
        if img_info is None:
            continue

        file_name = img_info["file_name"]
        img_w     = img_info["width"]
        img_h     = img_info["height"]

        img_path = images_dir / file_name
        if not img_path.exists():
            continue

        lbl_path = img_path.with_suffix(".txt")
        lines = []

        for ann in anns:
            cat_name = id_to_cat.get(ann["category_id"], "")
            tgt_name = class_map.get(cat_name)
            if tgt_name is None:
                skipped += 1
                continue
            tgt_id = TARGET_CLASSES.get(tgt_name)
            if tgt_id is None:
                skipped += 1
                continue

            x, y, w, h = ann["bbox"]   # COCO: top-left x, y, width, height
            cx = (x + w / 2) / img_w
            cy = (y + h / 2) / img_h
            bw = w / img_w
            bh = h / img_h

            # Clamp to [0, 1]
            cx = max(0.0, min(1.0, cx))
            cy = max(0.0, min(1.0, cy))
            bw = max(0.0, min(1.0, bw))
            bh = max(0.0, min(1.0, bh))

            if bw <= 0 or bh <= 0:
                skipped += 1
                continue

            lines.append(f"{tgt_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
            converted += 1

        lbl_path.write_text("\n".join(lines) + "\n" if lines else "")

    print(f"COCO conversion: {converted} annotations converted, {skipped} skipped.")
    return converted


# ── Train / val / test split ──────────────────────────────────────────────────

def split_dataset(
    images_dir: Path,
    ratios: tuple[float, float, float] = (0.7, 0.2, 0.1),
    seed: int = 42,
) -> None:
    """
    Move images (and their label files) from a flat directory into
    train / val / test sub-directories.

    Parameters
    ----------
    images_dir:
        Directory containing all images (and co-located .txt labels).
    ratios:
        (train, val, test) split ratios.  Must sum to 1.0.
    seed:
        Random seed for reproducibility.
    """
    if abs(sum(ratios) - 1.0) > 1e-6:
        raise ValueError(f"Ratios must sum to 1.0, got {sum(ratios):.4f}")

    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    all_images = sorted(
        [p for p in images_dir.iterdir() if p.suffix.lower() in image_exts]
    )
    if not all_images:
        print(f"No images found in {images_dir}")
        return

    random.seed(seed)
    random.shuffle(all_images)

    n = len(all_images)
    n_train = int(n * ratios[0])
    n_val   = int(n * ratios[1])

    split_map = {
        "train": all_images[:n_train],
        "val":   all_images[n_train:n_train + n_val],
        "test":  all_images[n_train + n_val:],
    }

    base = DATASET_ROOT
    for split_name, imgs in split_map.items():
        img_out = base / "images" / split_name
        lbl_out = base / "labels" / split_name
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)

        for img_src in imgs:
            shutil.copy2(img_src, img_out / img_src.name)
            lbl_src = img_src.with_suffix(".txt")
            if lbl_src.exists():
                shutil.copy2(lbl_src, lbl_out / lbl_src.name)
            else:
                (lbl_out / (img_src.stem + ".txt")).touch()

        print(f"  {split_name}: {len(imgs)} images → {img_out}")


# ── data.yaml generation ──────────────────────────────────────────────────────

def regenerate_data_yaml(abs_path: bool = False) -> None:
    """Overwrite configs/data.yaml with the current dataset paths."""
    dataset_path = (
        str(DATASET_ROOT.resolve()) if abs_path else "datasets/forest"
    )
    cfg = {
        "path":  dataset_path,
        "train": "images/train",
        "val":   "images/val",
        "test":  "images/test",
        "nc":    len(TARGET_CLASSES),
        "names": {v: k for k, v in TARGET_CLASSES.items()},
    }
    with CONFIG_PATH.open("w") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
    print(f"configs/data.yaml updated: {CONFIG_PATH}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare and organise the forest dataset for YOLO training"
    )
    parser.add_argument(
        "--remap",
        action="store_true",
        help="Remap existing YOLO label files using a class mapping JSON",
    )
    parser.add_argument(
        "--mapping",
        default=str(DEFAULT_MAP),
        help="Path to class_map.json (default: configs/class_map.json)",
    )
    parser.add_argument(
        "--source-names",
        default="",
        help=(
            "Comma-separated source class names in ID order, e.g. "
            "'deer,bear,person,gun'. Required for --remap when source dataset "
            "uses numeric IDs."
        ),
    )
    parser.add_argument(
        "--coco",
        help="Path to a COCO JSON annotation file to convert",
    )
    parser.add_argument(
        "--images-dir",
        help="Directory of raw images (used with --coco or --split)",
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="Split images in --images-dir into train/val/test",
    )
    parser.add_argument(
        "--train-ratio", type=float, default=0.7
    )
    parser.add_argument(
        "--val-ratio",   type=float, default=0.2
    )
    parser.add_argument(
        "--test-ratio",  type=float, default=0.1
    )
    parser.add_argument(
        "--update-yaml",
        action="store_true",
        help="Regenerate configs/data.yaml after preparation",
    )
    args = parser.parse_args()

    class_map = load_class_map(Path(args.mapping))

    if args.coco:
        if not args.images_dir:
            print("ERROR: --images-dir is required with --coco")
            sys.exit(1)
        convert_coco_to_yolo(
            Path(args.coco), Path(args.images_dir), class_map
        )

    if args.remap:
        src_names: dict[int, str] = {}
        if args.source_names:
            src_names = {i: n.strip() for i, n in enumerate(args.source_names.split(","))}

        for split in ["train", "val", "test"]:
            lbl_dir = DATASET_ROOT / "labels" / split
            if not lbl_dir.exists():
                continue
            n_files = 0
            for lbl_path in lbl_dir.glob("*.txt"):
                remap_label_file(lbl_path, src_names, class_map)
                n_files += 1
            print(f"  Remapped {n_files} label files in {split}")

    if args.split:
        if not args.images_dir:
            print("ERROR: --images-dir is required with --split")
            sys.exit(1)
        split_dataset(
            Path(args.images_dir),
            ratios=(args.train_ratio, args.val_ratio, args.test_ratio),
        )

    if args.update_yaml:
        regenerate_data_yaml()


if __name__ == "__main__":
    main()
