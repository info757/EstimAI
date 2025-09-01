# backend/app/models/jobs.py
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    failed = "failed"
    complete = "complete"


class JobType(str, Enum):
    pipeline = "pipeline"   # full: ingest -> agents -> bid pdf
    ingest = "ingest"
    agents = "agents"
    bid_pdf = "bid_pdf"


class JobRecord(BaseModel):
    """
    Persisted job metadata for async processing.
    Stored as JSON at backend/app/data/jobs/{job_id}.json
    """
    job_id: str
    project_id: str
    job_type: JobType

    status: JobStatus = JobStatus.queued
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    # 0.0 .. 1.0
    progress: float = 0.0

    # human-readable status line for the UI
    message: Optional[str] = None

    # full error string (shown when status == failed)
    error: Optional[str] = None

    # logical name -> relative filesystem path (served by FastAPI static)
    artifacts: Dict[str, str] = Field(default_factory=dict)

    # free-form metrics/context (durations, counts, etc.)
    meta: Dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "json_encoders": {
            datetime: lambda dt: dt.isoformat(),
        }
    }
