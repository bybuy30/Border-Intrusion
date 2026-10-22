"""
forest_intrusion.src
====================
Core library modules for the Forest Intrusion Detection System.

Import order (no circular dependencies):
    config → detector → tracker → event_logger → evidence_store → alert_engine
"""

from src.config import Settings  # noqa: F401 – re-export for convenience
