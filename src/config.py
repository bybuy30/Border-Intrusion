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
            os.getenv("MODEL_WEIGHTS", "runs/detect/forest_finetune_5/weights/best.pt")
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
    mongodb_uri: str = field(default_factory=lambda: os.getenv("MONGODB_URI", ""))
    mongodb_database: str = field(default_factory=lambda: os.getenv("MONGODB_DATABASE", "forest_intrusion"))
    camera_index: int = field(default_factory=lambda: int(os.getenv("CAMERA_INDEX", "0")))
    event_cooldown_seconds: float = field(default_factory=lambda: float(os.getenv("EVENT_COOLDOWN_SECONDS", "10")))
    burst_interval_seconds: float = field(default_factory=lambda: float(os.getenv("BURST_INTERVAL_SECONDS", "0.25")))
    pole_name: str = field(default_factory=lambda: os.getenv("POLE_NAME", "Demo Pole"))
    pole_location: str = field(default_factory=lambda: os.getenv("POLE_LOCATION", ""))
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

        if not self.evidence_dir.is_absolute():
            self.evidence_dir = root / self.evidence_dir

        # Ensure storage directories exist
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    @property
    def project_root(self) -> Path:
        """Absolute path to the forest-intrusion project root."""
        return _PROJECT_ROOT
