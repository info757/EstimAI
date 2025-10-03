import os
import json
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def test_bid_pdf_is_created(tmp_path, monkeypatch):
    pid = "B1"
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))

    # Minimal artifacts
    proj = Path(tmp_path) / pid

    # Scope (use the "scopes" array key our builder understands)
    _write_json(proj / "scope" / "s1.json", {
        "project_id": pid,
        "scopes": [
            "Provide and install 3000psi concrete slab.",
            "Furnish and erect structural steel per drawings."
        ]
    })

    # Estimate
    _write_json(proj / "estimate" / "e1.json", {
        "project_id": pid,
        "items": [
            {"description": "Concrete Slab 3000psi", "qty": 1000, "unit": "SF", "unit_cost": 8.5, "total": 8500.0},
            {"description": "Structural Steel (ton)", "qty": 10, "unit": "TON", "unit_cost": 1200.0, "total": 12000.0}
        ],
        "subtotal": 20500.0,
        "overhead_pct": 10.0,
        "profit_pct": 5.0,
        "total_bid": 20500.0 * 1.10 * 1.05
    })

    # Risks
    _write_json(proj / "risk" / "r1.json", {
        "project_id": pid,
        "risks": [
            {"id": "R1", "description": "Potential delay in material delivery", "probability": 0.3, "impact_cost_pct": 5, "impact_days": 14, "mitigation": "Order early"}
        ]
    })

    # Call endpoint
    res = client.post(f"/api/projects/{pid}/bid")
    assert res.status_code == 200, res.text

    data = res.json()
    assert data["project_id"] == pid
    pdf_path = Path(data["pdf_path"])
    assert pdf_path.exists(), f"PDF not found at {pdf_path}"
    assert pdf_path.stat().st_size > 0, "PDF is empty"

