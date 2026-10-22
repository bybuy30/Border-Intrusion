"""
scripts/export_model.py
=======================
Export or copy a trained YOLOv8 model for deployment.

Operations
----------
1. copy    — Copy best.pt from a training run into models/best.pt for local
             inference (the simplest option).
2. export  — Convert best.pt to a portable format (ONNX, TorchScript, etc.)
             using Ultralytics' built-in export pipeline.
3. gdrive  — Copy or export the weights to a Google Drive mount path (for
             use at the end of a Colab session).

Supported export formats
------------------------
    onnx          ONNX (recommended for CPU deployment)
    torchscript   TorchScript
    openvino      OpenVINO IR (Intel CPU optimised)
    tflite        TensorFlow Lite (edge devices)
    coreml        Core ML (Apple Silicon)

    See https://docs.ultralytics.com/modes/export/ for the full list.

Usage
-----
    # Copy best.pt from a training run to models/
    python scripts/export_model.py --copy runs/train/forest_v1/weights/best.pt

    # Export to ONNX
    python scripts/export_model.py --export --format onnx

    # Export to ONNX with a custom weights path
    python scripts/export_model.py --export --weights models/best.pt --format onnx

    # Copy to Google Drive (Colab)
    python scripts/export_model.py --gdrive /content/drive/MyDrive/forest-intrusion/models
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MODELS_DIR = PROJECT_ROOT / "models"

SUPPORTED_FORMATS = {
    "onnx", "torchscript", "openvino", "tflite", "coreml",
    "engine",  # TensorRT — requires NVIDIA GPU
    "pb",      # TensorFlow SavedModel
    "saved_model",
}


# ── Copy ──────────────────────────────────────────────────────────────────────

def copy_weights(source: Path, dest: Path | None = None) -> Path:
    """
    Copy a .pt checkpoint into models/best.pt (or a specified destination).

    Parameters
    ----------
    source:
        Path to the source .pt file (e.g. from a Colab training run).
    dest:
        Destination path.  Defaults to models/best.pt.

    Returns
    -------
    Path
        The destination path.
    """
    if not source.exists():
        raise FileNotFoundError(
            f"Source weights not found: {source}\n"
            "Ensure training completed successfully and the file exists."
        )

    dest = dest or (MODELS_DIR / "best.pt")
    dest.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(source, dest)
    print(f"✓ Weights copied: {source} → {dest}")
    return dest


# ── Export ────────────────────────────────────────────────────────────────────

def export_model(
    weights: Path,
    fmt: str,
    imgsz: int = 640,
    device: str = "cpu",
    simplify: bool = True,
) -> Path:
    """
    Export a YOLOv8 model to the specified format.

    Parameters
    ----------
    weights:
        Path to the .pt weights file.
    fmt:
        Export format string (e.g. ``"onnx"``).
    imgsz:
        Input image size for the exported model.
    device:
        Device to use for the export trace.
    simplify:
        Simplify the ONNX graph (only applies to ONNX export).

    Returns
    -------
    Path
        Path to the exported file.
    """
    fmt = fmt.lower()
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported format {fmt!r}. "
            f"Supported: {sorted(SUPPORTED_FORMATS)}"
        )

    if not weights.exists():
        raise FileNotFoundError(f"Weights not found: {weights}")

    try:
        from ultralytics import YOLO
    except ImportError:
        raise ImportError("ultralytics not installed. Run: pip install ultralytics")

    print(f"\nExporting {weights.name} → {fmt.upper()}")
    print(f"  Image size : {imgsz}")
    print(f"  Device     : {device}")

    model = YOLO(str(weights))
    export_kwargs = dict(format=fmt, imgsz=imgsz, device=device)
    if fmt == "onnx":
        export_kwargs["simplify"] = simplify

    exported_path = model.export(**export_kwargs)
    print(f"✓ Exported to: {exported_path}")
    return Path(exported_path)


# ── Google Drive copy ─────────────────────────────────────────────────────────

def copy_to_gdrive(
    weights: Path,
    gdrive_dir: str | Path,
    also_export: str | None = None,
) -> None:
    """
    Copy weights (and optionally an exported format) to Google Drive.

    Intended for use at the end of a Colab session to preserve results.

    Parameters
    ----------
    weights:
        Path to best.pt.
    gdrive_dir:
        Path to the target directory inside the Drive mount
        (e.g. /content/drive/MyDrive/forest-intrusion/models).
    also_export:
        If set (e.g. ``"onnx"``), also export and copy.
    """
    gdrive_path = Path(gdrive_dir)
    if not gdrive_path.exists():
        gdrive_path.mkdir(parents=True, exist_ok=True)
        print(f"Created Drive directory: {gdrive_path}")

    dest_pt = gdrive_path / "best.pt"
    shutil.copy2(weights, dest_pt)
    print(f"✓ best.pt → {dest_pt}")

    if also_export:
        exported = export_model(weights, fmt=also_export)
        dest_exp = gdrive_path / Path(exported).name
        shutil.copy2(exported, dest_exp)
        print(f"✓ {Path(exported).name} → {dest_exp}")

    # Write a provenance file
    ts = datetime.now(timezone.utc).isoformat()
    provenance = gdrive_path / "export_info.txt"
    provenance.write_text(
        f"Exported at : {ts}\n"
        f"Source      : {weights}\n"
        f"Format      : {also_export or 'pt only'}\n"
    )
    print(f"✓ Provenance written to {provenance}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export or copy trained YOLOv8 weights",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--copy",
        metavar="SOURCE_PT",
        help="Copy SOURCE_PT to models/best.pt",
    )
    group.add_argument(
        "--export",
        action="store_true",
        help="Export weights to a portable format",
    )
    group.add_argument(
        "--gdrive",
        metavar="GDRIVE_DIR",
        help="Copy weights to a Google Drive directory (Colab)",
    )

    parser.add_argument(
        "--weights",
        default="models/best.pt",
        help="Weights file used by --export or --gdrive",
    )
    parser.add_argument(
        "--format",
        default="onnx",
        choices=sorted(SUPPORTED_FORMATS),
        help="Export format (used with --export or --gdrive --also-export)",
    )
    parser.add_argument("--imgsz",  type=int, default=640)
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--also-export",
        metavar="FORMAT",
        help="Also export to this format when using --gdrive",
    )
    args = parser.parse_args()

    if args.copy:
        src = Path(args.copy)
        if not src.is_absolute():
            src = PROJECT_ROOT / src
        copy_weights(src)

    elif args.export:
        weights = Path(args.weights)
        if not weights.is_absolute():
            weights = PROJECT_ROOT / weights
        export_model(
            weights=weights,
            fmt=args.format,
            imgsz=args.imgsz,
            device=args.device,
        )

    elif args.gdrive:
        weights = Path(args.weights)
        if not weights.is_absolute():
            weights = PROJECT_ROOT / weights
        copy_to_gdrive(
            weights=weights,
            gdrive_dir=args.gdrive,
            also_export=args.also_export,
        )


if __name__ == "__main__":
    main()
