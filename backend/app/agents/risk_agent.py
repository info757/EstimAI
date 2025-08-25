from ..models.schemas import RiskOutput
from ..core.llm import llm_call_json
async def run(project_id: str) -> RiskOutput:
    ctx = {"project_id": project_id, "wbs": []}
    prompt = open("prompts/risk/system.md").read()
    schema = RiskOutput.model_json_schema()
    raw = await llm_call_json(prompt=prompt, context=ctx, schema=schema)
    return RiskOutput(**raw)
