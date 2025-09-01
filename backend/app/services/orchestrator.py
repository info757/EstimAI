# backend/app/services/orchestrator.py
import os
import json
import time
import logging
import asyncio
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[3]

from typing import List, Dict, Any

from fastapi import UploadFile, HTTPException


from ..models.schemas import TakeoffOutput, ScopeOutput, LevelingResult, RiskOutput, EstimateItem, EstimateOutput
from ..agents import takeoff_agent, scope_agent, leveler_agent, risk_agent

# Set up logging
logger = logging.getLogger(__name__)


def _artifact_dir() -> Path:
    # Always resolve to <project>/backend/artifacts unless ARTIFACT_DIR is set
    return Path(os.getenv("ARTIFACT_DIR", str(PROJECT_ROOT / "backend" / "artifacts")))


# -------------------------
# Helpers
# -------------------------
def _safe_filename(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in ("-", "_", ".", " ")).strip()

def _read_json(path: Path):
    return json.loads(path.read_text())

def _latest_jsons(dirpath: Path) -> list[Path]:
    if not dirpath.exists():
        return []
    return [p for p in dirpath.glob("*.json") if p.is_file()]

def _gather_takeoff_items(project_dir: Path) -> list[dict]:
    """Merge all items from takeoff/*.json into one list."""
    out: list[dict] = []
    for jf in _latest_jsons(project_dir / "takeoff"):
        try:
            data = _read_json(jf)
            items = data.get("items", [])
            if isinstance(items, list):
                out.extend(items)
        except Exception:
            # Skip unreadable files for MVP
            continue
    return out

def _load_costbook() -> dict[str, float]:
    """Load costbook from COSTBOOK_PATH or fallback to backend/app/data/costbook.json."""
    env_path = os.getenv("COSTBOOK_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return _read_json(p)
    fallback = PROJECT_ROOT / "backend" / "app" / "data" / "costbook.json"
    if fallback.exists():
        return _read_json(fallback)
    return {}


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

    from app.workers.indexer import write_sheet_index  # import
    from app.workers.spec_indexer import write_spec_index 
    
    idx_path = write_sheet_index(pid)
    spec_path = write_spec_index(pid)

    return {
        "project_id": pid,
        "saved_path": str(target),
        "index_path": str(idx_path),
        "spec_index_path": str(spec_path),
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

async def run_estimate(pid: str) -> EstimateOutput:
    """
    Build a costed estimate from takeoff (+leveler later if needed).
    - Reads takeoff items: [{description, qty, unit}, ...] from artifacts/{pid}/takeoff/*.json
    - Looks up unit_cost via description in costbook
    - Computes totals; persists artifact under artifacts/{pid}/estimate/<timestamp>.json
    """
    proj_dir = _artifact_dir() / pid
    proj_dir.mkdir(parents=True, exist_ok=True)

    takeoff_items = _gather_takeoff_items(proj_dir)
    costbook = _load_costbook()

    overhead_pct = float(os.getenv("OVERHEAD_PCT", "10"))
    profit_pct  = float(os.getenv("PROFIT_PCT",  "5"))

    items: list[EstimateItem] = []
    subtotal = 0.0

    for ti in takeoff_items:
        desc = str(ti.get("description", "")).strip()
        qty  = float(ti.get("qty", 0) or 0)
        unit = str(ti.get("unit", "")).strip()
        unit_cost = float(costbook.get(desc, 0.0))
        total = qty * unit_cost
        subtotal += total

        items.append(
            EstimateItem(
                description=desc,
                qty=qty,
                unit=unit,
                unit_cost=unit_cost,
                total=total,
            )
        )

    total_bid = subtotal * (1 + overhead_pct/100.0) * (1 + profit_pct/100.0)

    est = EstimateOutput(
        project_id=pid,
        items=items,
        subtotal=subtotal,
        overhead_pct=overhead_pct,
        profit_pct=profit_pct,
        total_bid=total_bid,
    )

    # Persist artifact alongside your other agents
    await _write_artifact(pid, "estimate", est.model_dump())

    return est

async def run_full_pipeline(pid: str) -> Dict[str, Any]:
    """
    Run all agents in sequence and persist their artifacts under:
      backend/artifacts/<pid>/<agent>/<timestamp>.json
    Returns a summary dict with any errors encountered.
    """
    summary: Dict[str, Any] = {"project_id": pid, "steps": {}, "errors": []}

    # Takeoff
    try:
        to = await run_takeoff(pid)
        summary["steps"]["takeoff"] = {"ok": True, "count": len(getattr(to, "items", []))}
    except Exception as e:
        summary["steps"]["takeoff"] = {"ok": False}
        summary["errors"].append({"takeoff": str(e)})

    # Scope
    try:
        sc = await run_scope(pid)
        summary["steps"]["scope"] = {"ok": True, "inclusions": len(getattr(sc, "inclusions", []) or []),
                                     "exclusions": len(getattr(sc, "exclusions", []) or [])}
    except Exception as e:
        summary["steps"]["scope"] = {"ok": False}
        summary["errors"].append({"scope": str(e)})

    # Leveler
    try:
        lv = await run_leveler(pid)
        summary["steps"]["leveler"] = {"ok": True, "normalized": len(lv or [])}
    except Exception as e:
        summary["steps"]["leveler"] = {"ok": False}
        summary["errors"].append({"leveler": str(e)})

    # Risk
    try:
        rk = await run_risk(pid)
        summary["steps"]["risk"] = {"ok": True, "risks": len(getattr(rk, "risks", []) or [])}
    except Exception as e:
        summary["steps"]["risk"] = {"ok": False}
        summary["errors"].append({"risk": str(e)})

    # Estimate (last, depends on takeoff)
    try:
        est = await run_estimate(pid)
        summary["steps"]["estimate"] = {
            "ok": True,
            "items": len(getattr(est, "items", []) or []),
            "subtotal": getattr(est, "subtotal", 0.0),
            "total_bid": getattr(est, "total_bid", 0.0),
        }
    except Exception as e:
        summary["steps"]["estimate"] = {"ok": False}
        summary["errors"].append({"estimate": str(e)})

    summary["ok"] = len(summary["errors"]) == 0
    return summary


def run_full_pipeline_sync(pid: str) -> Dict[str, Any]:
    """
    Synchronous version of run_full_pipeline for use in background workers.
    Run all agents in sequence: takeoff → scope → leveler → risk → estimate → bid
    Persist artifacts under: backend/artifacts/<pid>/<stage>/<timestamp>.json
    Returns: { "summary": {...}, "pdf_path": "artifacts/<pid>/bid/<file>.pdf" }
    """
    # Run the async function in a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(run_full_pipeline(pid))
    finally:
        loop.close()