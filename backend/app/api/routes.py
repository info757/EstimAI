# backend/app/api/routes.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends  # ← add File
from typing import List
from ..services import orchestrator
from ..models.schemas import TakeoffOutput, ScopeOutput, LevelingResult, RiskOutput
from app.services import orchestrator  # you already have this pattern
from app.models.schemas import EstimateOutput  # add if not present
from app.services.bid import build_bid_pdf
from ..core.auth import get_current_user
from pathlib import Path
from .routes_projects import router as projects_router
from .routes_jobs import router as jobs_router
from .routes_review import router as review_router
from .routes_auth import router as auth_router
import os

r = APIRouter()
r.include_router(auth_router)
r.include_router(projects_router)
r.include_router(jobs_router)
r.include_router(review_router)

@r.post("/projects/{pid}/ingest", tags=["projects"])
async def ingest(pid: str, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """
    Upload a file (PDF, etc.) for project processing.
    Returns browser-openable paths for uploaded files and generated indexes.
    """
    # Call orchestrator directly and return browser-openable paths
    try:
        result = await orchestrator.ingest(pid, file)
        
        # Convert absolute paths to browser-openable paths
        from pathlib import Path
        
        # Convert saved_path to relative path under /artifacts
        if "saved_path" in result:
            abs_path = Path(result["saved_path"])
            rel_path = abs_path.relative_to(Path(os.getenv("ARTIFACT_DIR", str(Path(__file__).resolve().parent.parent / "artifacts"))))
            result["pdf_path"] = f"artifacts/{rel_path}"
            del result["saved_path"]  # Remove absolute path
        
        # Convert index_path to relative path under /artifacts
        if "index_path" in result:
            abs_path = Path(result["index_path"])
            artifact_dir = Path(os.getenv("ARTIFACT_DIR", str(Path(__file__).resolve().parent.parent / "artifacts")))
            rel_path = abs_path.relative_to(artifact_dir)
            result["index_path"] = f"artifacts/{rel_path}"
        
        # Convert spec_index_path to relative path under /artifacts
        if "spec_index_path" in result:
            abs_path = Path(result["spec_index_path"])
            artifact_dir = Path(os.getenv("ARTIFACT_DIR", str(Path(__file__).resolve().parent.parent / "artifacts")))
            rel_path = abs_path.relative_to(artifact_dir)
            result["spec_index_path"] = f"artifacts/{rel_path}"
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {e}")


@r.post("/projects/{pid}/ingest_async", tags=["projects"])
async def ingest_async(pid: str, files: List[UploadFile] = File(...), current_user: dict = Depends(get_current_user)):
    """
    Upload multiple files asynchronously for project processing.
    Returns a job ID that can be used to track progress.
    """
    from ..services.jobs import create_ingest_job
    from ..services.ingest import ingest_files
    
    try:
        # Create ingest job
        job_id = create_ingest_job(pid)
        
        # Enqueue the ingest job (for now, run it synchronously)
        # In a real implementation, this would be queued to a background worker
        from ..services.jobs import run_ingest_job
        
        # Run the job synchronously for now
        result = run_ingest_job(job_id, pid, files, ingest_files)
        
        return {"job_id": job_id, "summary": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {e}")


@r.get("/projects/{pid}/ingest", tags=["projects"])
async def list_ingest(pid: str, current_user: dict = Depends(get_current_user)):
    """
    List ingested files for a project.
    Returns a list of ingested files with metadata.
    """
    # For PR 17, return empty list as noted in requirements
    # This will be implemented in PR 18
    return {"files": []}

@r.post("/projects/{pid}/agents/takeoff", response_model=TakeoffOutput, tags=["agents"])
async def run_takeoff(pid: str, current_user: dict = Depends(get_current_user)):
    """
    Run takeoff analysis on project documents.
    Returns structured takeoff data with measurements and confidence scores.
    """
    return await orchestrator.run_takeoff(pid)

@r.post("/projects/{pid}/agents/scope", response_model=ScopeOutput, tags=["agents"])
async def run_scope(pid: str, current_user: dict = Depends(get_current_user)):
    """
    Run scope analysis on project specifications.
    Returns structured scope of work items.
    """
    return await orchestrator.run_scope(pid)

@r.post("/projects/{pid}/agents/level", response_model=list[LevelingResult], tags=["agents"])
async def run_leveler(pid: str, current_user: dict = Depends(get_current_user)):
    """
    Run leveling analysis on takeoff data.
    Returns leveled takeoff items with standardized descriptions.
    """
    return await orchestrator.run_leveler(pid)

@r.post("/projects/{pid}/agents/risk", response_model=RiskOutput, tags=["agents"])
async def run_risk(pid: str, current_user: dict = Depends(get_current_user)):
    """
    Run risk analysis on project data.
    Returns identified risks and mitigation strategies.
    """
    return await orchestrator.run_risk(pid)

@r.post("/projects/{pid}/agents/estimate", response_model=EstimateOutput, tags=["agents"])
async def run_estimate(pid: str, current_user: dict = Depends(get_current_user)):
    """
    Generate cost estimate from takeoff and leveling data.
    Returns detailed estimate with line items and totals.
    """
    est = await orchestrator.run_estimate(pid)
    return est

@r.post("/projects/{pid}/bid", tags=["projects"])
@r.get("/projects/{pid}/bid", tags=["projects"])
async def create_bid(pid: str, current_user: dict = Depends(get_current_user)):
    """
    Generate a bid PDF from project data.
    Returns browser-openable path to the generated PDF.
    """
    pdf_abs = build_bid_pdf(pid)                 # e.g. /.../backend/artifacts/<pid>/bid/xxxx.pdf
    name = Path(pdf_abs).name
    pdf_rel = f"artifacts/{pid}/bid/{name}"      # ← URL path under /artifacts mount
    return {"project_id": pid, "pdf_path": pdf_rel}