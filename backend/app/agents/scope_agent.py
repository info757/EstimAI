# backend/app/agents/scope_agent.py
import os
import json
from pathlib import Path
from typing import Any, Dict, List

from ..models.schemas import ScopeOutput
from ..core.llm import llm_call_json

# Resolve project root so paths work whether you run from estimai/ or backend/
PROJECT_ROOT = Path(__file__).resolve().parents[3]

def _artifact_dir() -> Path:
    # Default to <project>/backend/artifacts unless ARTIFACT_DIR is set
    default = PROJECT_ROOT / "backend" / "artifacts"
    return Path(os.getenv("ARTIFACT_DIR", str(default)))

def _load_spec_index(project_id: str) -> List[Dict[str, Any]]:
    """Read backend/artifacts/<pid>/spec_index.json and return a list of chunks."""
    idx_file = _artifact_dir() / project_id / "spec_index.json"
    if not idx_file.exists():
        return []
    try:
        data = json.loads(idx_file.read_text())
        chunks = data.get("specs", [])
        return chunks if isinstance(chunks, list) else []
    except Exception:
        return []

async def run(project_id: str) -> ScopeOutput:
    # 1) Build context from real spec chunks (may be empty)
    specs = _load_spec_index(project_id)
    ctx: Dict[str, Any] = {"project_id": project_id, "specs": specs}

    # 2) Prompt + schema (absolute path so it works in tests and dev)
    prompt_path = PROJECT_ROOT / "prompts" / "scope" / "system.md"
    prompt = prompt_path.read_text(encoding="utf-8")
    schema = ScopeOutput.model_json_schema()

    # 3) LLM call (JSON mode)
    raw = await llm_call_json(prompt=prompt, context=ctx, schema=schema)

    # 4) Safety: normalize to a valid ScopeOutput
    if not isinstance(raw, dict):
        raw = {}
    if not isinstance(raw.get("scopes"), list):
        raw["scopes"] = []
    raw.setdefault("project_id", project_id)

    return ScopeOutput(**raw)


