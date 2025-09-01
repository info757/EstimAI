from fastapi import APIRouter
import uuid

from ..core.executors import EXECUTOR
from ..models.jobs import JobRecord, JobType
from ..services.jobs import save_job
from ..services.artifacts import collect_project_artifacts
from ..services.orchestrator import run_full_pipeline
from ..workers.run_pipeline import run_pipeline as run_pipeline_job

# All routes here will be /api/projects/...
router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/{pid}/pipeline_async", response_model=JobRecord)
def pipeline_async(pid: str):
    """
    Kick off the full pipeline (takeoff -> scope -> leveler -> risk -> estimate -> bid_pdf)
    as a background job. Returns a JobRecord immediately.
    
    Use GET /api/jobs/{job_id} to check the status of the background job.
    """
    job_id = uuid.uuid4().hex
    job = JobRecord(job_id=job_id, project_id=pid, job_type=JobType.pipeline)
    save_job(job)
    # Submit background job (defined in backend/app/workers/run_pipeline.py)
    EXECUTOR.submit(run_pipeline_job, job_id, pid)
    return job


@router.post("/{pid}/pipeline_sync")
async def pipeline_sync(pid: str):
    """
    Synchronously run takeoff -> scope -> leveler -> risk -> estimate.
    Returns a summary payload and writes JSON artifacts to the artifacts dir.
    
    This endpoint runs the full pipeline in the foreground and may take some time.
    """
    result = await run_full_pipeline(pid)
    return {"project_id": pid, "status": "complete", "result": result}


@router.get("/{pid}/artifacts")
def get_project_artifacts(pid: str):
    """
    Return all artifacts (JSON + bid PDFs) for a project.
    The values are relative static paths like 'artifacts/<pid>/bid/<file>.pdf'
    or 'projects/<pid>/artifacts/*.json' depending on where files live.
    
    These paths can be used directly in browser URLs to access the files.
    """
    return {"project_id": pid, "artifacts": collect_project_artifacts(pid)}
