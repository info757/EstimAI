import json
import os
from pathlib import Path
from fastapi.testclient import TestClient

# TODO: If your app import path differs, adjust this import:
from backend.app.main import app  # expects app/main.py exposing FastAPI instance `app`


client = TestClient(app)


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def test_estimate_empty_takeoff_returns_zero(tmp_path, monkeypatch):
    """
    Expectation:
    - Endpoint exists at POST /api/projects/{pid}/agents/estimate
    - With no takeoff items, returns items: [], subtotal=0, total_bid=0
    - Also persists an artifact under artifacts/{pid}/estimate/<timestamp>.json (not asserted here)
    """
    pid = "P1"
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))

    # Create minimal project structure with empty takeoff
    proj = Path(tmp_path) / pid
    _write_json(proj / "takeoff" / "empty.json", {"items": []})
    _write_json(proj / "leveler" / "empty.json", [])

    # Call endpoint (should exist once implemented)
    res = client.post(f"/api/projects/{pid}/agents/estimate")
    assert res.status_code == 200, res.text

    data = res.json()
    assert data["project_id"] == pid
    assert isinstance(data["items"], list)
    assert data["subtotal"] == 0
    assert data["total_bid"] == 0


def test_estimate_happy_path_with_costbook(tmp_path, monkeypatch):
    """
    Expectation:
    - Uses a costbook to price out two items and compute totals with default overhead/profit.
    - For test stability, we assert math relationships, not exact floating point formatting.
    """
    pid = "P2"
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))

    # Create takeoff items that your estimate service can map directly by description
    takeoff_items = {
        "items": [
            {"description": "Concrete Slab 3000psi", "qty": 1000, "unit": "SF"},
            {"description": "Structural Steel (ton)", "qty": 10, "unit": "TON"},
        ]
    }
    proj = Path(tmp_path) / pid
    _write_json(proj / "takeoff" / "t1.json", takeoff_items)

    # Leveler may be unused for MVP; keep present as an empty list to satisfy readers
    _write_json(proj / "leveler" / "l1.json", [])

    # Provide a costbook the implementation can discover.
    # Recommended: your code first checks env COSTBOOK_PATH, then falls back to repo path.
    costbook_path = Path(tmp_path) / "costbook.json"
    _write_json(costbook_path, {
        "Concrete Slab 3000psi": 8.50,
        "Structural Steel (ton)": 1200.00
    })
    monkeypatch.setenv("COSTBOOK_PATH", str(costbook_path))

    res = client.post(f"/api/projects/{pid}/agents/estimate")
    assert res.status_code == 200, res.text

    data = res.json()
    assert data["project_id"] == pid
    items = data["items"]
    assert len(items) == 2

    # Validate each line’s total = qty * unit_cost
    for it in items:
        assert it["total"] == it["qty"] * it["unit_cost"]

    # Validate totals relationship: total_bid = subtotal * (1 + overhead_pct/100) * (1 + profit_pct/100)
    subtotal = data["subtotal"]
    ov = data["overhead_pct"] / 100.0
    pf = data["profit_pct"] / 100.0
    expected_total_bid = subtotal * (1 + ov) * (1 + pf)

    # Allow tiny float drift
    assert abs(data["total_bid"] - expected_total_bid) < 1e-6

