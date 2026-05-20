"""Reusable core services for the Real Estate CRM."""

from .paths import APP_ROOT, DB_PATH, OUTPUT_DIR
from .intelligence import AI_LIBS_AVAILABLE, IntelligenceService
from .reports import ReportResult, ReportService

__all__ = [
    "AI_LIBS_AVAILABLE",
    "APP_ROOT",
    "DB_PATH",
    "IntelligenceService",
    "OUTPUT_DIR",
    "ReportResult",
    "ReportService",
]
