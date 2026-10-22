"""
scripts/download_datasets.py
============================
Dataset acquisition guide and optional automated helpers.

This script does NOT scrape websites or fabricate download URLs.
It explains exactly where to obtain legally usable datasets and provides
helper utilities for datasets that support direct programmatic download.

Datasets with download APIs
----------------------------
1. Roboflow Universe — public datasets with "CC BY 4.0" or similar licences.
   Requires a free Roboflow account and API key.
   URL: https://universe.roboflow.com/

2. LILA BC (Labeled Information Library of Alexandria: Biology and Conservation)
   Provides camera-trap wildlife images.  Requires manual browsing of the
   data catalogue and acceptance of individual dataset terms.
   URL: https://lila.science/

Datasets requiring manual download
------------------------------------
3. Open Images v7 (Google)
   Subset with "Person" and potentially firearm categories.
   Download with the official ``fiftyone`` library or the OID downloader.
   URL: https://storage.googleapis.com/openimages/web/index.html
   Licence: Creative Commons Attribution 4.0 International

4. OpenImagesWeapons (Research use)
   Some firearm subsets exist in Open Images under "Firearm" or "Handgun".
   Check individual image licences before use.

Usage
-----
    # List available datasets and their download instructions
    python scripts/download_datasets.py --list

    # Download a Roboflow dataset (requires API key in .env)
    python scripts/download_datasets.py --roboflow --workspace <name> --project <slug>

    # Show manual download instructions
    python scripts/download_datasets.py --manual

Environment variables
---------------------
    ROBOFLOW_API_KEY  — required for automated Roboflow download
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Allow running from project root or from scripts/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass  # Optional during bootstrap

DATASETS_DIR = PROJECT_ROOT / "datasets" / "forest"

# ── Dataset metadata ──────────────────────────────────────────────────────────

DATASETS: list[dict] = [
    {
        "name": "iWildCam (LILA BC)",
        "url": "https://lila.science/datasets/iwildcam-wilds",
        "classes": ["animal"],
        "licence": "CC BY 4.0 (check individual datasets)",
        "download_type": "manual",
        "instructions": (
            "1. Visit https://lila.science/datasets/\n"
            "2. Find the iWildCam or similar camera-trap dataset.\n"
            "3. Accept the licence and download the images + COCO annotations.\n"
            "4. Place images in datasets/forest/images/ and run prepare_dataset.py."
        ),
    },
    {
        "name": "Roboflow — Forest Wildlife (example project)",
        "url": "https://universe.roboflow.com/",
        "classes": ["animal", "person"],
        "licence": "Varies per project — check before use",
        "download_type": "roboflow_api",
        "instructions": (
            "1. Create a free account at https://roboflow.com/\n"
            "2. Find a project with animal / person annotations.\n"
            "3. Copy the API key from Settings → API.\n"
            "4. Add ROBOFLOW_API_KEY=<key> to your .env file.\n"
            "5. Run: python scripts/download_datasets.py --roboflow "
            "--workspace <workspace> --project <project-slug>"
        ),
    },
    {
        "name": "Open Images v7 (Google) — Person & Firearms",
        "url": "https://storage.googleapis.com/openimages/web/index.html",
        "classes": ["person", "firearm"],
        "licence": "CC BY 4.0",
        "download_type": "manual_fiftyone",
        "instructions": (
            "1. Install FiftyOne: pip install fiftyone\n"
            "2. Run the helper in this script with --open-images, or manually:\n"
            "   import fiftyone.zoo as foz\n"
            "   dataset = foz.load_zoo_dataset(\n"
            "       'open-images-v7',\n"
            "       split='train',\n"
            "       label_types=['detections'],\n"
            "       classes=['Person', 'Handgun', 'Rifle'],\n"
            "       max_samples=2000,\n"
            "   )\n"
            "3. Export annotations in YOLO format and place under datasets/forest/."
        ),
    },
]


# ── CLI helpers ───────────────────────────────────────────────────────────────

def list_datasets() -> None:
    """Print available dataset information."""
    print("\n=== Available Datasets ===\n")
    for ds in DATASETS:
        print(f"  Name    : {ds['name']}")
        print(f"  URL     : {ds['url']}")
        print(f"  Classes : {', '.join(ds['classes'])}")
        print(f"  Licence : {ds['licence']}")
        print(f"  Method  : {ds['download_type']}")
        print()


def show_manual_instructions() -> None:
    """Print step-by-step instructions for each dataset."""
    print("\n=== Manual Download Instructions ===\n")
    for ds in DATASETS:
        print(f"--- {ds['name']} ---")
        print(ds["instructions"])
        print()


def download_roboflow(workspace: str, project: str, version: int = 1) -> None:
    """
    Download a Roboflow dataset using the Roboflow Python SDK.

    Requires:
        pip install roboflow
        ROBOFLOW_API_KEY set in .env or environment.
    """
    try:
        from roboflow import Roboflow  # type: ignore[import]
    except ImportError:
        print(
            "ERROR: roboflow package not installed.\n"
            "Run: pip install roboflow"
        )
        sys.exit(1)

    api_key = os.getenv("ROBOFLOW_API_KEY")
    if not api_key:
        print(
            "ERROR: ROBOFLOW_API_KEY not found.\n"
            "Add it to your .env file: ROBOFLOW_API_KEY=your_key_here"
        )
        sys.exit(1)

    print(f"Connecting to Roboflow — workspace={workspace}, project={project}")
    rf = Roboflow(api_key=api_key)
    proj = rf.workspace(workspace).project(project)
    dataset = proj.version(version).download(
        "yolov8",
        location=str(DATASETS_DIR),
    )
    print(f"Dataset downloaded to: {dataset.location}")
    print(
        "\nIMPORTANT: Check the licence for this dataset at:\n"
        f"  https://universe.roboflow.com/{workspace}/{project}\n"
        "Ensure it is compatible with your intended use."
    )


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dataset acquisition helper for Forest Intrusion Detection"
    )
    parser.add_argument("--list", action="store_true", help="List available datasets")
    parser.add_argument(
        "--manual", action="store_true", help="Show manual download instructions"
    )
    parser.add_argument(
        "--roboflow", action="store_true", help="Download from Roboflow"
    )
    parser.add_argument("--workspace", help="Roboflow workspace name")
    parser.add_argument("--project", help="Roboflow project slug")
    parser.add_argument(
        "--version", type=int, default=1, help="Roboflow dataset version (default: 1)"
    )
    args = parser.parse_args()

    if args.list:
        list_datasets()
    elif args.manual:
        show_manual_instructions()
    elif args.roboflow:
        if not args.workspace or not args.project:
            print("ERROR: --workspace and --project are required for --roboflow")
            sys.exit(1)
        download_roboflow(args.workspace, args.project, args.version)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
