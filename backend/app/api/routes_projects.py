from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from typing import List
import uuid

from ..core.executors import EXECUTOR
from ..models.jobs import JobRecord, JobType
from ..services.jobs import create_job
from ..services.artifacts import collect_project_artifacts
from ..services.orchestrator import run_full_pipeline, ingest
from ..workers.run_pipeline import run_pipeline as run_pipeline_job
from ..core.auth import get_current_user

# All routes here will be /api/projects/...
router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/{pid}/pipeline_async")
def pipeline_async(pid: str):
    """
    Kick off the full pipeline (takeoff → scope → leveler → risk → estimate → bid)
    as a background job. Returns {job_id} immediately.
    
    Use GET /api/jobs/{job_id} to check the status of the background job.
    """
    # Create job in database using the new create_job function
    job_id = create_job(pid, "pipeline")
    # Submit background job (defined in backend/app/workers/run_pipeline.py)
    EXECUTOR.submit(run_pipeline_job, job_id, pid)
    return {"job_id": job_id}


@router.post("/{pid}/pipeline_sync")
async def pipeline_sync(pid: str):
    """
    Synchronously run the full pipeline: takeoff → scope → leveler → risk → estimate → bid.
    Returns a compact JSON response with summary and browser-openable pdf_path.
    
    This endpoint runs the full pipeline in the foreground and may take some time.
    Each stage output is saved to artifacts/{pid}/{stage}/ with timestamped names.
    """
    result = await run_full_pipeline(pid)
    return result


@router.post("/{pid}/ingest")
async def ingest_files(
    pid: str, 
    files: List[UploadFile] = File(...)
    # Removed auth requirement for MVP
):
    """
    Ingest PDF files for a project. 
    Saves files and creates indices for the pipeline to process.
    """
    try:
        results = []
        for file in files:
            result = await ingest(pid, file)
            results.append(result)
        
        return {
            "ok": True,
            "files_count": len(results),
            "files": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {str(e)}")


@router.get("/{pid}/ingest")
def get_ingest_manifest(pid: str):
    """Get the ingest manifest for a project."""
    import json
    from pathlib import Path
    from ..core.config import settings
    
    try:
        manifest_path = Path(settings.ARTIFACT_DIR) / pid / "ingest" / "ingest_manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            return manifest
        else:
            # Return empty manifest if none exists
            return {"files": [], "project_id": pid}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Manifest not found: {str(e)}")


@router.get("/{pid}/artifacts")
def get_project_artifacts(pid: str):
    """
    Return all artifacts (JSON + bid PDFs) for a project.
    The values are relative static paths like 'artifacts/<pid>/bid/<file>.pdf'
    or 'projects/<pid>/artifacts/*.json' depending on where files live.
    """
    return {"project_id": pid, "artifacts": collect_project_artifacts(pid)}
