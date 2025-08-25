# backend/app/agents/scope_agent.py
import os
import json
from pathlib import Path
from typing import Any, Dict, List

from ..models.schemas import ScopeOutput
from ..core.llm import llm_call_json

# NEW: resolve project root so paths work whether you run from estimai/ or backend/
PROJECT_ROOT = Path(__file__).resolve().parents[3]

def _load_spec_index(project_id: str) -> List[Dict[str, Any]]:
    """
    Optional: read spec_index.json if you create one later in ingest/workers.
    For now, return an empty list so the agent still runs.
    """
    # keep using env, but default to backend/artifacts under the project root
    artifact_dir_default = PROJECT_ROOT / "backend" / "artifacts"
    artifact_dir = Path(os.getenv("ARTIFACT_DIR", str(artifact_dir_default)))
    idx_file = artifact_dir / project_id / "spec_index.json"
    if idx_file.exists():
        try:
            data = json.loads(idx_file.read_text())
            chunks = data.get("specs", [])
            return chunks if isinstance(chunks, list) else []
        except Exception:
            return []
    return []

async def run(project_id: str) -> ScopeOutput:
    # 1) Build context (hooks in a future spec_index.json if you add one)
    specs = _load_spec_index(project_id)
    ctx: Dict[str, Any] = {"project_id": project_id, "specs": specs}

    # 2) Prompt + schema  — CHANGED: load via absolute path
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

