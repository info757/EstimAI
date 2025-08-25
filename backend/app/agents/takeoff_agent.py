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


async def run(project_id: str) -> TakeoffOutput:
    # 1) Load real context from index
    sheets = _load_sheet_index(project_id)

    # 2) Build prompt + schema
    prompt = open("prompts/takeoff/system.md", "r", encoding="utf-8").read()
    schema = TakeoffOutput.model_json_schema()

    # 3) Call the LLM in JSON mode
    context = {
        "project_id": project_id,
        "sheets": sheets,  # this is now real data from ingest
        # (optional) add hints you care about; schema enforces actual output
        "assemblies_hint": [
            {"assembly_id": "03-300", "measure_type": "LF", "unit": "LF"},
            {"assembly_id": "09-290", "measure_type": "SF", "unit": "SF"},
        ],
    }
    raw = await llm_call_json(prompt=prompt, context=context, schema=schema)

    # 4) Safety: normalize to a valid TakeoffOutput
    if not isinstance(raw, dict):
        raw = {}
    if not isinstance(raw.get("items"), list):
        raw["items"] = []
    raw.setdefault("project_id", project_id)

    return TakeoffOutput(**raw)
