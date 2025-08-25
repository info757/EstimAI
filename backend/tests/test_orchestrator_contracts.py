import asyncio
from app.services import orchestrator
from app.models.schemas import TakeoffOutput
async def fake_takeoff_run(pid: str):
    return TakeoffOutput(project_id=pid, items=[], notes=None)
def test_orchestrator_writes_artifact(monkeypatch, tmp_path):
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setattr("app.agents.takeoff_agent.run", fake_takeoff_run)
    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(orchestrator.run_takeoff("P1"))
    assert res.project_id == "P1"
    assert list(tmp_path.glob("**/*.json"))
