# backend/app/agents/takeoff_agent.py
import os
import json
from pathlib import Path
from typing import Any, Dict, List

from ..models.schemas import TakeoffOutput
from ..core.llm import llm_call_json


def _load_sheet_index(project_id: str) -> List[Dict[str, Any]]:
    """Read backend/artifacts/<pid>/sheet_index.json and return sheets[]."""
    artifact_dir = Path(os.getenv("ARTIFACT_DIR", "backend/artifacts"))
    idx_file = artifact_dir / project_id / "sheet_index.json"
    if not idx_file.exists():
        # fallback stub so the agent always has context
        return [{"sheet_id": "A1.1", "discipline": "Architectural", "title": "Stub"}]
    try:
        data = json.loads(idx_file.read_text())
        sheets = data.get("sheets", [])
        # basic sanity filter
        if not isinstance(sheets, list):
            return [{"sheet_id": "A1.1", "discipline": "Architectural", "title": "Stub"}]
        return sheets
    except Exception:
        return [{"sheet_id": "A1.1", "discipline": "Architectural", "title": "Stub"}]


def _load_spec_index(project_id: str) -> List[Dict[str, Any]]:
    """Read backend/artifacts/<pid>/spec_index.json and return specs[]."""
    artifact_dir = Path(os.getenv("ARTIFACT_DIR", "backend/artifacts"))
    idx_file = artifact_dir / project_id / "spec_index.json"
    if not idx_file.exists():
        return []
    try:
        data = json.loads(idx_file.read_text())
        specs = data.get("specs", [])
        return specs if isinstance(specs, list) else []
    except Exception:
        return []


def _load_geometry_index(project_id: str) -> List[Dict[str, Any]]:
    """Read backend/artifacts/<pid>/geometry_index.json and return geometries[]."""
    artifact_dir = Path(os.getenv("ARTIFACT_DIR", "backend/artifacts"))
    idx_file = artifact_dir / project_id / "geometry_index.json"
    if not idx_file.exists():
        return []
    try:
        data = json.loads(idx_file.read_text())
        geometries = data.get("geometries", [])
        return geometries if isinstance(geometries, list) else []
    except Exception:
        return []


async def run(project_id: str) -> TakeoffOutput:
    # 1) Load real context from sheet, spec, and geometry indices
    sheets = _load_sheet_index(project_id)
    specs = _load_spec_index(project_id)
    geometries = _load_geometry_index(project_id)

    # 2) Build prompt + schema
    # Get the project root directory (3 levels up from this file)
    project_root = Path(__file__).resolve().parents[3]
    prompt_file = project_root / "prompts" / "takeoff" / "system.md"
    prompt = prompt_file.read_text(encoding="utf-8")
    schema = TakeoffOutput.model_json_schema()

    # 3) Call the LLM in JSON mode
    context = {
        "project_id": project_id,
        "sheets": sheets,  # drawing/sheet information
        "specs": specs,    # specification text that may contain quantities
        "geometries": geometries,  # vector geometry data (lines, polygons, measurements)
        # (optional) add hints you care about; schema enforces actual output
        "assemblies_hint": [
            {"assembly_id": "03-300", "measure_type": "LF", "unit": "LF"},
            {"assembly_id": "09-290", "measure_type": "SF", "unit": "SF"},
        ],
    }
    
    # Call LLM with schema validation to ensure project_id is included
    from ..core.llm import llm_call_json
    raw = await llm_call_json(prompt=prompt, context=context, schema=schema)
    
    # 4) Safety: normalize to a valid TakeoffOutput
    if not isinstance(raw, dict):
        raw = {}
    if not isinstance(raw.get("items"), list):
        raw["items"] = []
    raw.setdefault("project_id", project_id)
    
    # Fix field name mismatches and data types
    for item in raw.get("items", []):
        if "quantity" in item:
            # Convert quantity array to number (take first value or 0)
            qty = item.pop("quantity")
            if isinstance(qty, list) and len(qty) > 0:
                item["qty"] = float(qty[0]) if isinstance(qty[0], (int, float)) else 0.0
            else:
                item["qty"] = 0.0
        # Ensure required fields exist
        item.setdefault("unit", "EA")
        item.setdefault("confidence", 0.5)

    return TakeoffOutput(**raw)
