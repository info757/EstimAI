# backend/app/api/routes.py
from fastapi import APIRouter, UploadFile, File, HTTPException  # ← add File
from ..services import orchestrator
from ..models.schemas import TakeoffOutput, ScopeOutput, LevelingResult, RiskOutput
from app.services import orchestrator  # you already have this pattern
from app.models.schemas import EstimateOutput  # add if not present
from app.services.bid import build_bid_pdf
from pathlib import Path
from .routes_projects import router as projects_router
from .routes_jobs import router as jobs_router
import os

r = APIRouter()
r.include_router(projects_router)
r.include_router(jobs_router)

@r.post("/projects/{pid}/ingest", tags=["projects"])
async def ingest(pid: str, file: UploadFile = File(...)):
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

@r.post("/projects/{pid}/agents/takeoff", response_model=TakeoffOutput, tags=["agents"])
async def run_takeoff(pid: str):
    """
    Run takeoff analysis on project documents.
    Returns structured takeoff data with measurements and confidence scores.
    """
    return await orchestrator.run_takeoff(pid)

@r.post("/projects/{pid}/agents/scope", response_model=ScopeOutput, tags=["agents"])
async def run_scope(pid: str):
    """
    Run scope analysis on project specifications.
    Returns structured scope of work items.
    """
    return await orchestrator.run_scope(pid)

@r.post("/projects/{pid}/agents/level", response_model=list[LevelingResult], tags=["agents"])
async def run_leveler(pid: str):
    """
    Run leveling analysis on takeoff data.
    Returns leveled takeoff items with standardized descriptions.
    """
    return await orchestrator.run_leveler(pid)

@r.post("/projects/{pid}/agents/risk", response_model=RiskOutput, tags=["agents"])
async def run_risk(pid: str):
    """
    Run risk analysis on project data.
    Returns identified risks and mitigation strategies.
    """
    return await orchestrator.run_risk(pid)

@r.post("/projects/{pid}/agents/estimate", response_model=EstimateOutput, tags=["agents"])
async def run_estimate(pid: str):
    """
    Generate cost estimate from takeoff and leveling data.
    Returns detailed estimate with line items and totals.
    """
    est = await orchestrator.run_estimate(pid)
    return est

@r.post("/projects/{pid}/bid", tags=["projects"])
@r.get("/projects/{pid}/bid", tags=["projects"])
async def create_bid(pid: str):
    """
    Generate a bid PDF from project data.
    Returns browser-openable path to the generated PDF.
    """
    pdf_abs = build_bid_pdf(pid)                 # e.g. /.../backend/artifacts/<pid>/bid/xxxx.pdf
    name = Path(pdf_abs).name
    pdf_rel = f"artifacts/{pid}/bid/{name}"      # ← URL path under /artifacts mount
    return {"project_id": pid, "pdf_path": pdf_rel}