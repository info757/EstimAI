# backend/app/services/jobs.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from ..models.jobs import JobRecord, JobStatus
from ..core.logging import json_logger, log_job_transition
from .db import create_job as db_create_job, update_job as db_update_job, get_job as db_get_job, list_jobs as db_list_jobs
import json

# Logger for this module
logger = json_logger(__name__)


def _utcnow() -> str:
    """Get current UTC time as ISO8601 string."""
    return datetime.now(timezone.utc).isoformat()


def create_job(project_id: str, job_type: str = 'pipeline') -> str:
    """
    Create a new job record in the database.
    
    Args:
        project_id: Project identifier
        job_type: Type of job (default: 'pipeline')
        
    Returns:
        str: Generated job ID
    """
    job_id = str(uuid.uuid4())
    created_at = _utcnow()
    
    # Create job in database
    db_create_job(
        job_id=job_id,
        pid=project_id,
        status=JobStatus.queued.value,
        created_at=created_at
    )
    
    logger.info("Job created", extra={
        'job_id': job_id,
        'project_id': project_id,
        'job_type': job_type,
        'status': JobStatus.queued.value,
        'db_operation': 'create'
    })
    
    return job_id


def save_job(job: JobRecord) -> None:
    """Save a job record to the database."""
    # Convert datetime to ISO8601 string if needed
    created_at = job.created_at.isoformat() if hasattr(job.created_at, 'isoformat') else str(job.created_at)
    updated_at = job.updated_at.isoformat() if hasattr(job.updated_at, 'isoformat') else str(job.updated_at)
    
    # Check if job exists
    existing_job = db_get_job(job.job_id)
    
    if existing_job:
        # Update existing job
        result_json = None
        error_text = None
        
        # Handle result, artifacts, and meta fields
        if hasattr(job, 'result') and job.result:
            result_json = json.dumps(job.result)
        else:
            # Combine artifacts and meta into a single result
            combined_result = {}
            if hasattr(job, 'artifacts') and job.artifacts:
                combined_result.update(job.artifacts)
            if hasattr(job, 'meta') and job.meta:
                combined_result.update(job.meta)
            
            if combined_result:
                result_json = json.dumps(combined_result)
            else:
                result_json = None
        
        if hasattr(job, 'error') and job.error:
            error_text = str(job.error)
        
        db_update_job(
            job_id=job.job_id,
            status=job.status.value,
            updated_at=updated_at,
            result_json=result_json,
            error_text=error_text
        )
    else:
        # Create new job
        db_create_job(
            job_id=job.job_id,
            pid=job.project_id,
            status=job.status.value,
            created_at=created_at
        )
    
    # Log job state change
    log_job_transition(
        logger=logger,
        job_id=job.job_id,
        project_id=job.project_id,
        from_state="unknown",  # We don't track previous state here
        to_state=job.status.value,
        result={"saved": True, "db_operation": "save"}
    )


def load_job(job_id: str) -> JobRecord:
    """Load a job record from the database."""
    job_dict = db_get_job(job_id)
    if not job_dict:
        raise FileNotFoundError(f"Job {job_id} not found")
    
    # Convert database record to JobRecord
    # Parse timestamps back to datetime objects
    try:
        created_at = datetime.fromisoformat(job_dict['created_at'].replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        created_at = datetime.now(timezone.utc)
    
    try:
        updated_at = datetime.fromisoformat(job_dict['updated_at'].replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        updated_at = datetime.now(timezone.utc)
    
    # Create JobRecord with available data
    # Separate result back into artifacts and meta
    result_data = job_dict.get('result', {}) if job_dict.get('result') else {}
    artifacts = {}
    meta = {}
    
    if result_data:
        # Try to separate artifacts (file paths) from meta (other data)
        for key, value in result_data.items():
            if isinstance(value, str) and (value.startswith('/') or value.startswith('artifacts/')):
                # This looks like a file path, so it's an artifact
                artifacts[key] = value
            else:
                # This is other data, so it's meta
                meta[key] = value
    
    return JobRecord(
        job_id=job_dict['id'],
        project_id=job_dict['pid'],
        job_type='pipeline',  # Default to pipeline for backward compatibility
        status=JobStatus(job_dict['status']),
        created_at=created_at,
        updated_at=updated_at,
        error=job_dict.get('error_text'),
        artifacts=artifacts,
        meta=meta
    )


def update_job(job_id: str, **fields) -> JobRecord:
    """Update fields on a job record and save it."""
    job = load_job(job_id)
    old_status = job.status.value
    
    for k, v in fields.items():
        setattr(job, k, v)
    
    # Log status transition if status changed
    if 'status' in fields and old_status != job.status.value:
        log_job_transition(
            logger=logger,
            job_id=job.job_id,
            project_id=job.project_id,
            from_state=old_status,
            to_state=job.status.value,
            result={"updated_fields": list(fields.keys())}
        )
    
    save_job(job)
    return job


def list_jobs(project_id: str | None = None) -> List[JobRecord]:
    """Return all jobs, optionally filtered by project_id."""
    job_dicts = db_list_jobs(project_id)
    out: List[JobRecord] = []
    
    for job_dict in job_dicts:
        try:
            # Parse timestamps back to datetime objects
            try:
                created_at = datetime.fromisoformat(job_dict['created_at'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                created_at = datetime.now(timezone.utc)
            
            try:
                updated_at = datetime.fromisoformat(job_dict['updated_at'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                updated_at = datetime.now(timezone.utc)
            
            # Create JobRecord with available data
            # Separate result back into artifacts and meta
            result_data = job_dict.get('result', {}) if job_dict.get('result') else {}
            artifacts = {}
            meta = {}
            
            if result_data:
                # Try to separate artifacts (file paths) from meta (other data)
                for key, value in result_data.items():
                    if isinstance(value, str) and (value.startswith('/') or value.startswith('artifacts/')):
                        # This looks like a file path, so it's an artifact
                        artifacts[key] = value
                    else:
                        # This is other data, so it's meta
                        meta[key] = value
            
            job_record = JobRecord(
                job_id=job_dict['id'],
                project_id=job_dict['pid'],
                job_type='pipeline',  # Default to pipeline for backward compatibility
                status=JobStatus(job_dict['status']),
                created_at=created_at,
                updated_at=updated_at,
                error=job_dict.get('error_text'),
                artifacts=artifacts,
                meta=meta
            )
            out.append(job_record)
        except Exception as e:
            logger.warning("Failed to parse job record", extra={
                'job_id': job_dict.get('id'),
                'error': str(e),
                'db_operation': 'list_parse'
            })
            continue
    
    return out


def create_ingest_job(project_id: str) -> str:
    """
    Create a new ingest job record in the database.
    
    Args:
        project_id: Project identifier
        
    Returns:
        str: Generated job ID
    """
    return create_job(project_id, job_type='ingest')


def run_ingest_job(job_id: str, pid: str, files, ingest_func) -> Dict[str, Any]:
    """
    Run an ingest job with the provided files and ingest function.
    
    Args:
        job_id: Job ID
        pid: Project ID
        files: List of uploaded files
        ingest_func: Function to call for ingestion
        
    Returns:
        Dict: Job result with summary
    """
    try:
        # Update job status to running
        update_job(job_id, status=JobStatus.running)
        
        # Run the ingest function
        result = ingest_func(pid, files, job_id)
        
        # Update job status to complete with result
        update_job(job_id, status=JobStatus.complete, meta=result)
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        logger.error("Ingest job failed", extra={
            'job_id': job_id,
            'project_id': pid,
            'error': error_msg
        })
        
        # Update job status to failed with error
        update_job(job_id, status=JobStatus.failed, error=error_msg)
        
        raise
