# backend/app/workers/run_pipeline.py
from __future__ import annotations

import time
import traceback
from typing import Callable

from ..models.jobs import JobStatus
from ..services.jobs import update_job
from ..services.artifacts import collect_project_artifacts

# Import the orchestrator with the run_full_pipeline_sync function
from ..services import orchestrator


def run_pipeline(job_id: str, project_id: str) -> None:
    """
    Full pipeline: takeoff → scope → leveler → risk → estimate → bid
    Updates JobRecord throughout and attaches artifacts on success.
    On failure, captures and persists traceback message.
    """
    try:
        update_job(job_id, status=JobStatus.running, message="Starting pipeline…", progress=0.02)

        # Run the full pipeline using the synchronous orchestrator function
        result = orchestrator.run_full_pipeline_sync(project_id)
        
        # Extract summary and pdf_path from the result
        summary = result.get("summary", {})
        pdf_path = result.get("pdf_path")
        
        # Collect all artifacts
        arts = collect_project_artifacts(project_id)
        
        # If we have a pdf_path, add it to artifacts
        if pdf_path:
            arts["bid_pdf"] = pdf_path

        # Update job with success info
        update_job(
            job_id,
            status=JobStatus.complete,
            progress=1.0,
            message="Pipeline complete",
            artifacts=arts,
            meta={
                "summary": summary,
                "pdf_path": pdf_path,
                "completed_at": time.time()
            }
        )

    except Exception as e:
        # Capture full traceback for debugging
        error_traceback = traceback.format_exc()
        
        # Update job with failure info
        update_job(
            job_id, 
            status=JobStatus.failed, 
            message="Pipeline failed", 
            error=error_traceback,
            meta={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "failed_at": time.time()
            }
        )
        
        # Re-raise so errors surface in logs
        raise
