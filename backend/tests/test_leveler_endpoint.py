import os
import json
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app  # expects backend/app/main.py exposing FastAPI app

client = TestClient(app)


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def test_leveler_returns_array(tmp_path, monkeypatch):
    """
    Expectation:
    - Endpoint exists at POST /api/projects/{pid}/agents/level
    - Response is always a JSON array (list)
    - Empty project should return []
    """
    pid = "L1"
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))

    proj = Path(tmp_path) / pid
    _write_json(proj / "docs" / "dummy.pdf", {"stub": True})  # placeholder to simulate project

    res = client.post(f"/api/projects/{pid}/agents/level")
    assert res.status_code == 200, res.text
    data = res.json()
    assert isinstance(data, list)  # top-level must be an array

