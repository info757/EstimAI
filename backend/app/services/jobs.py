# backend/app/services/jobs.py
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from ..models.jobs import JobRecord, JobStatus

# Directory for persisted job metadata
JOBS_DIR = Path(__file__).resolve().parents[2] / "data" / "jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)


def _job_path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"


def save_job(job: JobRecord) -> None:
    """Write a job record to disk."""
    job.updated_at = job.updated_at or job.created_at
    _job_path(job.job_id).write_text(job.model_dump_json(indent=2))


def load_job(job_id: str) -> JobRecord:
    """Load a job record from disk."""
    path = _job_path(job_id)
    if not path.exists():
        raise FileNotFoundError(f"Job {job_id} not found")
    return JobRecord.model_validate_json(path.read_text())


def update_job(job_id: str, **fields) -> JobRecord:
    """Update fields on a job record and save it."""
    job = load_job(job_id)
    for k, v in fields.items():
        setattr(job, k, v)
    save_job(job)
    return job


def list_jobs(project_id: str | None = None) -> List[JobRecord]:
    """Return all jobs, optionally filtered by project_id."""
    out: List[JobRecord] = []
    for p in sorted(JOBS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            jr = JobRecord.model_validate_json(p.read_text())
            if (project_id and jr.project_id == project_id) or not project_id:
                out.append(jr)
        except Exception:
            continue
    return out
