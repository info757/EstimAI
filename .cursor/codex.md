# Intent
Multi-agent estimating app: agents (takeoff, scope, leveler, risk, report). Orchestrator coordinates.
# Contracts
TakeoffOutput(items[assembly_id, measure_type(SF|LF|EA|CY), qty, unit, confidence, evidence_uri, sheet_id]), ScopeOutput, LevelingResult, RiskOutput.
# Conventions
Agents expose `async def run(project_id: str, **kwargs)` returning typed models.
