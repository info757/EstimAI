from fastapi import APIRouter, UploadFile, HTTPException
from ..services import orchestrator
from ..models.schemas import TakeoffOutput, ScopeOutput, LevelingResult, RiskOutput
r = APIRouter()
@r.post("/projects/{pid}/ingest")
async def ingest(pid: str, file: UploadFile):
    ok = await orchestrator.ingest(pid, file)
    if not ok: raise HTTPException(400, "Ingest failed")
    return {"project_id": pid, "status": "queued"}
@r.post("/projects/{pid}/agents/takeoff", response_model=TakeoffOutput)
async def run_takeoff(pid: str): return await orchestrator.run_takeoff(pid)
@r.post("/projects/{pid}/agents/scope", response_model=ScopeOutput)
async def run_scope(pid: str): return await orchestrator.run_scope(pid)
@r.post("/projects/{pid}/agents/level", response_model=list[LevelingResult])
async def run_leveler(pid: str): return await orchestrator.run_leveler(pid)
@r.post("/projects/{pid}/agents/risk", response_model=RiskOutput)
async def run_risk(pid: str): return await orchestrator.run_risk(pid)
