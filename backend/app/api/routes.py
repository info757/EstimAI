# backend/app/api/routes.py
from fastapi import APIRouter, UploadFile, File, HTTPException  # ← add File
from ..services import orchestrator
from ..models.schemas import TakeoffOutput, ScopeOutput, LevelingResult, RiskOutput
from app.services import orchestrator  # you already have this pattern
from app.models.schemas import EstimateOutput  # add if not present

r = APIRouter()

@r.post("/projects/{pid}/ingest")
async def ingest(pid: str, file: UploadFile = File(...)):  # ← tell FastAPI to expect a multipart "file" field
    # Call orchestrator directly and return full details (saved_path, index_path, spec_index_path, etc.)
    try:
        return await orchestrator.ingest(pid, file)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {e}")

@r.post("/projects/{pid}/agents/takeoff", response_model=TakeoffOutput)
async def run_takeoff(pid: str):
    return await orchestrator.run_takeoff(pid)

@r.post("/projects/{pid}/agents/scope", response_model=ScopeOutput)
async def run_scope(pid: str):
    return await orchestrator.run_scope(pid)

@r.post("/projects/{pid}/agents/level", response_model=list[LevelingResult])
async def run_leveler(pid: str):
    return await orchestrator.run_leveler(pid)

@r.post("/projects/{pid}/agents/risk", response_model=RiskOutput)
async def run_risk(pid: str):
    return await orchestrator.run_risk(pid)

@r.post("/projects/{pid}/agents/estimate", response_model=EstimateOutput)
async def run_estimate(pid: str):
    est = await orchestrator.run_estimate(pid)
    return est