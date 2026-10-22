"""
scripts/validate_dataset.py
============================
Validate the dataset before training:
- Verify that every label file has a matching image and vice-versa.
- Check that all bounding boxes are within [0, 1] normalised range.
- Detect corrupted or unreadable images.
- Report missing or empty label files.
- Check that all class IDs match configs/data.yaml.
- Warn about potential near-duplicate filenames (same stem, different split).

Does NOT check image-level duplicates via perceptual hashing (that requires
imagehash and would be slow on large datasets). For production use, consider
running a deduplication tool before calling this script.

Usage
-----
    python scripts/validate_dataset.py
    python scripts/validate_dataset.py --split train --fix-missing-labels
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATASET_ROOT = PROJECT_ROOT / "datasets" / "forest"
CONFIG_PATH  = PROJECT_ROOT / "configs" / "data.yaml"
SPLITS = ["train", "val", "test"]


def load_class_names() -> dict[int, str]:
    """Load class names from configs/data.yaml."""
    if not CONFIG_PATH.exists():
        print(f"WARNING: {CONFIG_PATH} not found — using default class names.")
        return {0: "animal", 1: "person", 2: "firearm"}
    with CONFIG_PATH.open() as f:
        cfg = yaml.safe_load(f)
    names = cfg.get("names", {})
    if isinstance(names, list):
        return {i: n for i, n in enumerate(names)}
    return {int(k): v for k, v in names.items()}


def validate_split(
    split: str,
    valid_class_ids: set[int],
    fix_missing: bool = False,
) -> dict:
    """Validate a single dataset split and return an issue report."""
    img_dir = DATASET_ROOT / "images" / split
    lbl_dir = DATASET_ROOT / "labels" / split

    issues: list[str] = []
    stats = {
        "split": split,
        "images": 0,
        "labels": 0,
        "corrupted_images": 0,
        "missing_labels": 0,
        "missing_images": 0,
        "invalid_bbox_lines": 0,
        "unknown_class_ids": 0,
        "empty_labels": 0,
    }

    if not img_dir.exists():
        issues.append(f"Image directory not found: {img_dir}")
        stats["issues"] = issues
        return stats

    image_files = {
        p.stem: p
        for p in img_dir.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    }
    label_files = (
        {p.stem: p for p in lbl_dir.iterdir() if p.suffix == ".txt"}
        if lbl_dir.exists()
        else {}
    )

    stats["images"] = len(image_files)
    stats["labels"] = len(label_files)

    # Check each image
    for stem, img_path in image_files.items():
        img = cv2.imread(str(img_path))
        if img is None:
            issues.append(f"CORRUPTED image: {img_path.name}")
            stats["corrupted_images"] += 1
            continue

        lbl_path = lbl_dir / (stem + ".txt")
        if not lbl_path.exists():
            issues.append(f"Missing label for image: {img_path.name}")
            stats["missing_labels"] += 1
            if fix_missing:
                lbl_dir.mkdir(parents=True, exist_ok=True)
                lbl_path.touch()   # Create empty label (negative sample)
                print(f"  Created empty label: {lbl_path.name}")
            continue

        lines = lbl_path.read_text().strip().splitlines()
        if not lines:
            stats["empty_labels"] += 1   # Negative sample — allowed

        for ln_no, line in enumerate(lines, 1):
            parts = line.split()
            if len(parts) < 5:
                issues.append(
                    f"  {lbl_path.name} line {ln_no}: too few fields ({line!r})"
                )
                stats["invalid_bbox_lines"] += 1
                continue
            try:
                cls_id = int(parts[0])
                cx, cy, bw, bh = map(float, parts[1:5])
            except ValueError:
                issues.append(
                    f"  {lbl_path.name} line {ln_no}: non-numeric values"
                )
                stats["invalid_bbox_lines"] += 1
                continue

            if cls_id not in valid_class_ids:
                issues.append(
                    f"  {lbl_path.name} line {ln_no}: unknown class_id={cls_id}"
                )
                stats["unknown_class_ids"] += 1

            if not (0 <= cx <= 1 and 0 <= cy <= 1 and 0 < bw <= 1 and 0 < bh <= 1):
                issues.append(
                    f"  {lbl_path.name} line {ln_no}: bbox out of range "
                    f"(cx={cx:.3f}, cy={cy:.3f}, w={bw:.3f}, h={bh:.3f})"
                )
                stats["invalid_bbox_lines"] += 1

    # Check for labels without images
    for stem in set(label_files) - set(image_files):
        issues.append(f"Label file has no matching image: {stem}.txt")
        stats["missing_images"] += 1

    stats["issues"] = issues
    return stats


def check_split_leakage(splits: list[str]) -> list[str]:
    """Warn if the same image stem appears in more than one split."""
    stem_to_splits: dict[str, list[str]] = {}
    for split in splits:
        img_dir = DATASET_ROOT / "images" / split
        if not img_dir.exists():
            continue
        for p in img_dir.iterdir():
            if p.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                stem_to_splits.setdefault(p.stem, []).append(split)

    leaks = [
        f"Stem '{stem}' appears in {splits_list}"
        for stem, splits_list in stem_to_splits.items()
        if len(splits_list) > 1
    ]
    return leaks


def print_report(results: list[dict], leakage_warnings: list[str]) -> bool:
    """Print the validation report. Returns True if no critical issues."""
    all_ok = True
    print("\n" + "=" * 60)
    print(" Dataset Validation Report")
    print("=" * 60)

    for stats in results:
        issues = stats.get("issues", [])
        critical = (
            stats["corrupted_images"] +
            stats["invalid_bbox_lines"] +
            stats["unknown_class_ids"] +
            stats.get("missing_images", 0)
        )
        print(f"\n  Split  : {stats['split']}")
        print(f"  Images : {stats['images']}")
        print(f"  Labels : {stats['labels']}")
        print(f"  Missing labels  : {stats['missing_labels']}")
        print(f"  Corrupted images: {stats['corrupted_images']}")
        print(f"  Invalid bbox lines: {stats['invalid_bbox_lines']}")
        print(f"  Unknown class IDs : {stats['unknown_class_ids']}")
        print(f"  Empty labels (neg samples): {stats['empty_labels']}")

        if issues:
            all_ok = False
            print(f"\n  Issues ({len(issues)}):")
            for issue in issues[:20]:
                print(f"    ✗ {issue}")
            if len(issues) > 20:
                print(f"    ... and {len(issues) - 20} more")
        else:
            print("  ✓ No issues found")

    if leakage_warnings:
        all_ok = False
        print(f"\n  Data-leakage warnings ({len(leakage_warnings)}):")
        for w in leakage_warnings[:10]:
            print(f"    ✗ {w}")

    print("\n" + ("=" * 60))
    print(f"  Overall: {'PASS ✓' if all_ok else 'ISSUES FOUND — review above'}")
    print("=" * 60 + "\n")
    return all_ok


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate the forest dataset before training"
    )
    parser.add_argument(
        "--split",
        choices=SPLITS + ["all"],
        default="all",
        help="Split to validate (default: all)",
    )
    parser.add_argument(
        "--fix-missing-labels",
        action="store_true",
        help="Create empty label files for images that have no annotation "
             "(marks them as negative/background samples)",
    )
    args = parser.parse_args()

    class_names = load_class_names()
    valid_class_ids = set(class_names.keys())
    splits = SPLITS if args.split == "all" else [args.split]

    results = [
        validate_split(split, valid_class_ids, fix_missing=args.fix_missing_labels)
        for split in splits
    ]
    leakage = check_split_leakage(splits)
    ok = print_report(results, leakage)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
