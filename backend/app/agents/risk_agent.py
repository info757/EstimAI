# backend/app/agents/risk_agent.py
from pathlib import Path
import os

from ..models.schemas import RiskOutput
from ..core.llm import llm_call_json

# Resolve repo root regardless of CWD (…/estimai)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
# Allow override via env if you want: export RISK_PROMPT_PATH=/abs/path/system.md
PROMPT_PATH = Path(os.getenv("RISK_PROMPT_PATH", PROJECT_ROOT / "prompts" / "risk" / "system.md"))

async def run(project_id: str) -> RiskOutput:
    ctx = {"project_id": project_id, "wbs": []}

    try:
        base_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        # Helpful error with absolute path so it’s obvious what’s missing
        raise FileNotFoundError(f"Risk system prompt not found at: {PROMPT_PATH}") from e
 # Enforce that project_id is included at top-level in the JSON
    enforce = f"""
Output constraints (do not ignore):
- Return ONLY valid JSON that matches RiskOutput.
- Top-level MUST include: "project_id": "{project_id}" and "risks": [...].
- If no risks, return exactly: {{ "project_id": "{project_id}", "risks": [] }}.
- No prose or explanations outside the JSON.
""".strip()

    prompt = f"{base_prompt}\n\n{enforce}"
    schema = RiskOutput.model_json_schema()
    raw = await llm_call_json(prompt=prompt, context=ctx, schema=schema)
    return RiskOutput(**raw)
