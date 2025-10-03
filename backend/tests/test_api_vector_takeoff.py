from fastapi.testclient import TestClient
from pathlib import Path
from backend.app.main import app

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "tests" / "assets" / "site_plan_warehouse_100k.pdf"

def test_vector_endpoint_ok():
    if not PDF.exists():
        return
    with PDF.open("rb") as f:
        r = client.post("/api/takeoff/vector?page_index=1", files={"file": ("plan.pdf", f, "application/pdf")})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    q = data["quantities"]
    assert q["building_area_sf"] > 0
    assert q["curb_length_lf"] > 0

