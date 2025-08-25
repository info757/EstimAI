# backend/app/services/orchestrator.py
import os
import json
import time
from pathlib import Path
from typing import List

from fastapi import UploadFile, HTTPException

from ..models.schemas import TakeoffOutput, ScopeOutput, LevelingResult, RiskOutput
from ..agents import takeoff_agent, scope_agent, leveler_agent, risk_agent

def _artifact_dir() -> Path:
    return Path(os.getenv("ARTIFACT_DIR", "backend/artifacts"))

# -------------------------
# Helpers
# -------------------------
def _safe_filename(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in ("-", "_", ".", " ")).strip()

async def _write_artifact(project_id: str, agent: str, payload: dict) -> None:
    ts = int(time.time())
    out = _artifact_dir() / project_id / agent   # 👈 add ()
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{ts}.json").write_text(json.dumps(payload, indent=2))

def write_index(pid: str) -> Path:
    """
    Dummy 'OCR' indexer:
    Scan backend/artifacts/<pid>/docs/*.pdf and emit sheet_index.json with stub sheet IDs.
    Replace with real OCR/parsing later.
    """
    proj_dir = _artifact_dir() / pid             # 👈 add ()
    docs_dir = proj_dir / "docs"
    sheets = []
    if docs_dir.exists():
        for i, p in enumerate(sorted(docs_dir.glob("*.pdf"))):
            sheets.append({
                "sheet_id": f"A1.{i+1}",
                "file": str(p),
                "discipline": "Architectural",
                "title": p.stem[:60],
            })
    if not sheets:
        sheets = [{"sheet_id": "A1.1", "file": "", "discipline": "Architectural", "title": "Stub"}]

    out = proj_dir / "sheet_index.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"project_id": pid, "sheets": sheets}, indent=2))
    return out

# -------------------------
# API-facing functions
# -------------------------
async def ingest(pid: str, file: UploadFile):
    """
    Save an uploaded file to backend/artifacts/<pid>/docs/<filename>
    and refresh a simple sheet index for the project.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    filename = _safe_filename(file.filename)
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    proj_docs = _artifact_dir() / pid / "docs"   # 👈 add ()
    proj_docs.mkdir(parents=True, exist_ok=True)

    target = proj_docs / filename
    if target.exists():
        ts = int(time.time())
        target = proj_docs / f"{target.stem}_{ts}{target.suffix}"

    # Stream upload to disk (handles large PDFs)
    CHUNK = 1024 * 1024  # 1 MB
    with target.open("wb") as out:
        while True:
            chunk = await file.read(CHUNK)
            if not chunk:
                break
            out.write(chunk)

    # Build/refresh simple sheet index
    idx_path = write_index(pid)

    return {
        "project_id": pid,
        "saved_path": str(target),
        "index_path": str(idx_path),
        "original_filename": file.filename,
        "content_type": file.content_type,
        "bytes": target.stat().st_size,
        "status": "saved",
    }

async def run_takeoff(pid: str) -> TakeoffOutput:
    result = await takeoff_agent.run(pid)
    await _write_artifact(pid, "takeoff", result.model_dump())
    return result

async def run_scope(pid: str) -> ScopeOutput:
    result = await scope_agent.run(pid)
    await _write_artifact(pid, "scope", result.model_dump())
    return result

async def run_leveler(pid: str) -> List[LevelingResult]:
    results = await leveler_agent.run(pid)
    for res in results:
        await _write_artifact(pid, "leveler", res.model_dump())
    return results

async def run_risk(pid: str) -> RiskOutput:
    result = await risk_agent.run(pid)
    await _write_artifact(pid, "risk", result.model_dump())
    return result

