# backend/app/api/routes_jobs.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..services.jobs import load_job, list_jobs
from ..models.jobs import JobRecord

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobRecord)
def get_job(job_id: str):
    """
    Get details of a single job by ID.
    
    Returns the current status and any results from background job processing.
    """
    try:
        return load_job(job_id)
    except FileNotFoundError:
        raise HTTPException(404, detail=f"Job {job_id} not found")


@router.get("", response_model=list[JobRecord])
def get_jobs(project_id: str | None = Query(None)):
    """
    List jobs, optionally filtered by project_id.
    
    Returns all jobs or jobs for a specific project if project_id is provided.
    """
    return list_jobs(project_id)
