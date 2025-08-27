import os
import json
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app  # expects backend/app/main.py exposing FastAPI app

client = TestClient(app)


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def test_risk_returns_object_with_risks_array(tmp_path, monkeypatch):
    """
    Expectation:
    - Endpoint exists at POST /api/projects/{pid}/agents/risk
    - Response is always an object with key "risks"
    - "risks" is an array ([] when empty)
    """
    pid = "R1"
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))

    proj = Path(tmp_path) / pid
    _write_json(proj / "docs" / "dummy.pdf", {"stub": True})  # placeholder

    res = client.post(f"/api/projects/{pid}/agents/risk")
    assert res.status_code == 200, res.text
    data = res.json()
    assert isinstance(data, dict)  # top-level must be object
    assert "risks" in data
    assert isinstance(data["risks"], list)  # must always be a list

