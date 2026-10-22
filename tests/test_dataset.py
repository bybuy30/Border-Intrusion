"""
tests/test_dataset.py
=====================
Unit tests for dataset class mapping and annotation validation utilities.

These tests do NOT require a real dataset or model weights.
They validate the logic in scripts/prepare_dataset.py and
scripts/validate_dataset.py using temporary directories and synthetic data.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

# ── Import targets ────────────────────────────────────────────────────────────
# Add project root to sys.path so imports work from the tests/ directory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.prepare_dataset import remap_label_file, convert_coco_to_yolo


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_label(tmp_path: Path):
    """Write a YOLO label file with three classes: 0, 1, 2."""
    lbl = tmp_path / "img001.txt"
    lbl.write_text(
        "0 0.5 0.5 0.2 0.3\n"   # class 0 → "deer" in source
        "1 0.3 0.4 0.1 0.1\n"   # class 1 → "human"
        "2 0.7 0.6 0.05 0.08\n" # class 2 → "gun"
    )
    return lbl


@pytest.fixture()
def class_map():
    return {
        "deer":  "animal",
        "bear":  "animal",
        "human": "person",
        "gun":   "firearm",
    }


@pytest.fixture()
def source_id_to_name():
    return {0: "deer", 1: "human", 2: "gun"}


# ── remap_label_file tests ────────────────────────────────────────────────────

class TestRemapLabelFile:

    def test_remaps_all_classes(
        self, tmp_path, tmp_label, class_map, source_id_to_name
    ):
        """All three source classes should be remapped correctly."""
        out = tmp_path / "out.txt"
        count = remap_label_file(tmp_label, source_id_to_name, class_map, out)
        assert count == 3
        lines = out.read_text().strip().splitlines()
        assert lines[0].startswith("0 ")   # deer → animal (ID 0)
        assert lines[1].startswith("1 ")   # human → person (ID 1)
        assert lines[2].startswith("2 ")   # gun → firearm (ID 2)

    def test_skips_unmapped_class(self, tmp_path, class_map, source_id_to_name):
        """A source class not in the map should be silently dropped."""
        lbl = tmp_path / "img.txt"
        lbl.write_text("3 0.5 0.5 0.1 0.1\n")  # class 3 has no name in source_id_to_name
        out = tmp_path / "out.txt"
        count = remap_label_file(lbl, source_id_to_name, class_map, out)
        assert count == 0
        assert out.read_text().strip() == ""

    def test_skips_class_not_in_map(self, tmp_path, class_map):
        """Source class name not in class_map should be dropped."""
        lbl = tmp_path / "img.txt"
        lbl.write_text("0 0.5 0.5 0.1 0.1\n")
        # source_id_to_name maps 0 → "cat", which is not in class_map
        count = remap_label_file(lbl, {0: "cat"}, class_map, tmp_path / "out.txt")
        assert count == 0

    def test_preserves_bbox_values(
        self, tmp_path, tmp_label, class_map, source_id_to_name
    ):
        """Bounding box coordinates must not be altered during remapping."""
        out = tmp_path / "out.txt"
        remap_label_file(tmp_label, source_id_to_name, class_map, out)
        lines = out.read_text().strip().splitlines()
        # First line: deer → animal — check bbox unchanged
        parts = lines[0].split()
        assert parts[1:] == ["0.5", "0.5", "0.2", "0.3"]

    def test_handles_empty_label_file(self, tmp_path, class_map, source_id_to_name):
        """An empty label file should produce an empty output without error."""
        lbl = tmp_path / "empty.txt"
        lbl.write_text("")
        out = tmp_path / "out.txt"
        count = remap_label_file(lbl, source_id_to_name, class_map, out)
        assert count == 0

    def test_handles_malformed_line(self, tmp_path, class_map, source_id_to_name):
        """A line with too few fields should be skipped without raising."""
        lbl = tmp_path / "bad.txt"
        lbl.write_text("0 0.5\n")  # only 2 fields instead of 5
        out = tmp_path / "out.txt"
        count = remap_label_file(lbl, source_id_to_name, class_map, out)
        assert count == 0


# ── convert_coco_to_yolo tests ────────────────────────────────────────────────

class TestConvertCocoToYolo:

    def _make_coco_json(self, tmp_path: Path) -> tuple[Path, Path]:
        """Create a minimal COCO JSON and a matching dummy image directory."""
        coco = {
            "images": [
                {"id": 1, "file_name": "img001.jpg", "width": 640, "height": 480},
            ],
            "categories": [
                {"id": 1, "name": "deer"},
                {"id": 2, "name": "human"},
            ],
            "annotations": [
                {
                    "id": 1, "image_id": 1, "category_id": 1,
                    "bbox": [100, 80, 200, 160],  # x, y, w, h
                },
                {
                    "id": 2, "image_id": 1, "category_id": 2,
                    "bbox": [400, 200, 50, 80],
                },
            ],
        }
        json_path = tmp_path / "annotations.json"
        json_path.write_text(json.dumps(coco))

        img_dir = tmp_path / "images"
        img_dir.mkdir()
        # Create a placeholder image file so the converter can find it
        (img_dir / "img001.jpg").write_bytes(b"FAKEJPEG")

        return json_path, img_dir

    def test_converts_known_classes(self, tmp_path):
        """Known source classes should produce valid YOLO label files."""
        coco_json, img_dir = self._make_coco_json(tmp_path)
        class_map = {"deer": "animal", "human": "person"}

        count = convert_coco_to_yolo(coco_json, img_dir, class_map)
        assert count == 2

        lbl = img_dir / "img001.txt"
        assert lbl.exists()
        lines = lbl.read_text().strip().splitlines()
        assert len(lines) == 2

    def test_skips_unknown_classes(self, tmp_path):
        """Annotations whose category is not in class_map should be skipped."""
        coco_json, img_dir = self._make_coco_json(tmp_path)
        class_map = {"deer": "animal"}  # "human" not mapped

        count = convert_coco_to_yolo(coco_json, img_dir, class_map)
        assert count == 1   # Only deer annotation

    def test_bbox_normalisation(self, tmp_path):
        """Bounding box values in the YOLO label must be in [0, 1]."""
        coco_json, img_dir = self._make_coco_json(tmp_path)
        class_map = {"deer": "animal", "human": "person"}
        convert_coco_to_yolo(coco_json, img_dir, class_map)

        lbl = img_dir / "img001.txt"
        for line in lbl.read_text().strip().splitlines():
            parts = line.split()
            assert len(parts) == 5
            cx, cy, bw, bh = map(float, parts[1:])
            assert 0.0 <= cx <= 1.0, f"cx={cx} out of range"
            assert 0.0 <= cy <= 1.0, f"cy={cy} out of range"
            assert 0.0 < bw <= 1.0,  f"bw={bw} out of range"
            assert 0.0 < bh <= 1.0,  f"bh={bh} out of range"

    def test_missing_image_file_skipped(self, tmp_path):
        """An annotation referencing a non-existent image should be skipped."""
        coco = {
            "images": [
                {"id": 99, "file_name": "ghost.jpg", "width": 640, "height": 480},
            ],
            "categories": [{"id": 1, "name": "deer"}],
            "annotations": [
                {"id": 1, "image_id": 99, "category_id": 1,
                 "bbox": [10, 10, 100, 100]},
            ],
        }
        json_path = tmp_path / "a.json"
        json_path.write_text(json.dumps(coco))
        img_dir = tmp_path / "imgs"
        img_dir.mkdir()
        # ghost.jpg does NOT exist

        count = convert_coco_to_yolo(json_path, img_dir, {"deer": "animal"})
        assert count == 0
