# backend/app/api/routes_jobs.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Depends

from ..services.db import get_job as db_get_job, list_jobs as db_list_jobs
from ..models.jobs import JobRecord, JobStatus, JobType
from ..core.auth import get_current_user
from datetime import datetime, timezone

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}")
def get_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get details of a single job by ID.
    
    Returns the current status and any results from background job processing.
    """
    job_dict = db_get_job(job_id)
    if not job_dict:
        raise HTTPException(404, detail=f"Job {job_id} not found")
    
    # Map database row to JobResponse format
    response = {
        "job_id": job_dict["id"],
        "project_id": job_dict["pid"],
        "job_type": "pipeline",  # Default to pipeline for backward compatibility
        "status": job_dict["status"],
        "created_at": job_dict["created_at"],
        "updated_at": job_dict["updated_at"],
        "progress": 0.0,  # Default progress
        "message": None,  # Default message
        "error": job_dict.get("error_text"),
        "artifacts": job_dict.get("result", {}) if job_dict.get("result") else {},
        "meta": {}
    }
    
    # Add result data to meta if present
    if job_dict.get("result"):
        if isinstance(job_dict["result"], dict):
            if "summary" in job_dict["result"]:
                response["meta"]["summary"] = job_dict["result"]["summary"]
            if "pdf_path" in job_dict["result"]:
                response["meta"]["pdf_path"] = job_dict["result"]["pdf_path"]
    
    return response


@router.get("")
def get_jobs(project_id: str | None = Query(None), current_user: dict = Depends(get_current_user)):
    """
    List jobs, optionally filtered by project_id.
    
    Returns all jobs or jobs for a specific project if project_id is provided.
    """
    job_dicts = db_list_jobs(project_id)
    
    # Map database rows to JobResponse format
    jobs = []
    for job_dict in job_dicts:
        job_response = {
            "job_id": job_dict["id"],
            "project_id": job_dict["pid"],
            "job_type": "pipeline",  # Default to pipeline for backward compatibility
            "status": job_dict["status"],
            "created_at": job_dict["created_at"],
            "updated_at": job_dict["updated_at"],
            "progress": 0.0,  # Default progress
            "message": None,  # Default message
            "error": job_dict.get("error_text"),
            "artifacts": job_dict.get("result", {}) if job_dict.get("result") else {},
            "meta": {}
        }
        
        # Add result data to meta if present
        if job_dict.get("result"):
            if isinstance(job_dict["result"], dict):
                if "summary" in job_dict["result"]:
                    job_response["meta"]["summary"] = job_dict["result"]["summary"]
                if "pdf_path" in job_dict["result"]:
                    job_response["meta"]["pdf_path"] = job_dict["result"]["pdf_path"]
        
        jobs.append(job_response)
    
    return jobs
