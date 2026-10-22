"""
src/config.py
=============
Centralised configuration loaded from environment variables and .env files.

Usage
-----
    from src.config import Settings
    cfg = Settings()
    print(cfg.model_weights)

All values can be overridden by setting environment variables before importing,
or by editing the .env file in the project root.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file: src/ → root/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=False)


@dataclass
class Settings:
    """Runtime configuration for the Forest Intrusion Detection System."""

    # ── Identity ──────────────────────────────────────────────────────────────
    camera_id: str = field(
        default_factory=lambda: os.getenv("CAMERA_ID", "camera_01")
    )
    pole_id: str = field(
        default_factory=lambda: os.getenv("POLE_ID", "pole_01")
    )

    # ── Model ─────────────────────────────────────────────────────────────────
    model_weights: Path = field(
        default_factory=lambda: Path(
            os.getenv("MODEL_WEIGHTS", "models/best.pt")
        )
    )

    # ── Detection thresholds ──────────────────────────────────────────────────
    confidence_threshold: float = field(
        default_factory=lambda: float(
            os.getenv("CONFIDENCE_THRESHOLD", "0.35")
        )
    )
    iou_threshold: float = field(
        default_factory=lambda: float(
            os.getenv("IOU_THRESHOLD", "0.45")
        )
    )

    # ── Alert thresholds ──────────────────────────────────────────────────────
    firearm_alert_threshold: float = field(
        default_factory=lambda: float(
            os.getenv("FIREARM_ALERT_THRESHOLD", "0.40")
        )
    )

    # ── Storage ───────────────────────────────────────────────────────────────
    database_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("DATABASE_PATH", "storage/events/events.db")
        )
    )
    evidence_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("EVIDENCE_DIR", "storage/evidence")
        )
    )

    # ── Class names (must match configs/data.yaml) ───────────────────────────
    class_names: dict[int, str] = field(
        default_factory=lambda: {0: "animal", 1: "person", 2: "firearm"}
    )

    def __post_init__(self) -> None:
        """Resolve paths relative to the project root and create directories."""
        root = _PROJECT_ROOT

        if not self.model_weights.is_absolute():
            self.model_weights = root / self.model_weights

        if not self.database_path.is_absolute():
            self.database_path = root / self.database_path

        if not self.evidence_dir.is_absolute():
            self.evidence_dir = root / self.evidence_dir

        # Ensure storage directories exist
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    @property
    def project_root(self) -> Path:
        """Absolute path to the forest-intrusion project root."""
        return _PROJECT_ROOT
