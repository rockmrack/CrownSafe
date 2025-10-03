"""
Ingestion schemas for data ingestion runner
"""

from enum import Enum


class IngestionSource(str, Enum):
    """Data ingestion source types"""
    CPSC_RECALL = "cpsc_recall"
    CPSC_NEISS = "cpsc_neiss"
    CPSC_VIOLATION = "cpsc_violation"
    FDA_RECALL = "fda_recall"
    EU_SAFETY_GATE = "eu_safety_gate"
    MANUAL_UPLOAD = "manual_upload"
    API_SYNC = "api_sync"
    SCHEDULED_IMPORT = "scheduled_import"


class IngestionStatus(str, Enum):
    """Ingestion run status"""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    RUNNING = "running"
    COMPLETED = "completed"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"

