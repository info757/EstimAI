from fastapi import APIRouter
import uuid

from ..core.executors import EXECUTOR
from ..models.jobs import JobRecord, JobType
from ..services.jobs import create_job
from ..services.artifacts import collect_project_artifacts
from ..services.orchestrator import run_full_pipeline
from ..workers.run_pipeline import run_pipeline as run_pipeline_job

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


@router.get("/{pid}/artifacts")
def get_project_artifacts(pid: str):
    """
    Return all artifacts (JSON + bid PDFs) for a project.
    The values are relative static paths like 'artifacts/<pid>/bid/<file>.pdf'
    or 'projects/<pid>/artifacts/*.json' depending on where files live.
    """
    return {"project_id": pid, "artifacts": collect_project_artifacts(pid)}
