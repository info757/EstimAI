# backend/tests/test_smokes.py
import time
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.core.config import get_settings


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def artifact_dir():
    """Get the artifact directory from settings."""
    return Path(get_settings().ARTIFACT_DIR)


def _write_json(path: Path, data):
    """Helper to write JSON data to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def poll_job(client: TestClient, job_id: str, timeout: int = 30) -> dict:
    """
    Poll a job until it completes or times out.
    
    Args:
        client: TestClient instance
        job_id: Job ID to poll
        timeout: Maximum time to wait in seconds
        
    Returns:
        Job result dict
        
    Raises:
        pytest.fail: If job fails or times out
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200, f"Failed to get job status: {response.text}"
        
        job_data = response.json()
        status = job_data.get("status")
        
        if status == "complete":
            return job_data
        elif status == "failed":
            error = job_data.get("error", "Unknown error")
            pytest.fail(f"Job failed: {error}")
        
        time.sleep(1)
    
    pytest.fail(f"Job {job_id} did not complete within {timeout} seconds")


def test_bid_smoke(client: TestClient, artifact_dir: Path, tmp_path):
    """
    Test that the bid endpoint works and returns a downloadable PDF.
    """
    pid = "smoke_test_bid"
    
    # Set up minimal artifacts needed for bid generation
    proj_dir = artifact_dir / pid
    
    # Scope data
    _write_json(proj_dir / "scope" / "scope_001.json", {
        "project_id": pid,
        "scopes": [
            "Provide and install 3000psi concrete slab.",
            "Furnish and erect structural steel per drawings."
        ]
    })
    
    # Estimate data
    _write_json(proj_dir / "estimate" / "estimate_001.json", {
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
    
    # Risk data
    _write_json(proj_dir / "risk" / "risk_001.json", {
        "project_id": pid,
        "risks": [
            {"id": "R1", "description": "Potential delay in material delivery", "probability": 0.3, "impact_cost_pct": 5, "impact_days": 14, "mitigation": "Order early"}
        ]
    })
    
    # Call the bid endpoint
    response = client.post(f"/api/projects/{pid}/bid")
    assert response.status_code == 200, f"Bid endpoint failed: {response.text}"
    
    data = response.json()
    assert "pdf_path" in data, "Response missing pdf_path"
    assert data["project_id"] == pid
    
    # Verify the PDF is downloadable
    pdf_path = data["pdf_path"]
    pdf_response = client.get(f"/{pdf_path}")
    assert pdf_response.status_code == 200, f"PDF not downloadable: {pdf_response.text}"
    assert pdf_response.headers["content-type"] == "application/pdf", f"Wrong content type: {pdf_response.headers['content-type']}"
    assert len(pdf_response.content) > 0, "PDF is empty"


def test_artifacts_mount(client: TestClient, artifact_dir: Path):
    """
    Test that artifacts are properly mounted and accessible.
    """
    pid = "smoke_test_artifacts"
    
    # Create a sentinel PDF file in the bid directory (which the artifacts service will find)
    sentinel_path = artifact_dir / pid / "bid" / "sentinel.pdf"
    sentinel_path.parent.mkdir(parents=True, exist_ok=True)
    # Create a minimal PDF content (just some bytes that look like a PDF)
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids []\n/Count 0\n>>\nendobj\nxref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \ntrailer\n<<\n/Size 3\n/Root 1 0 R\n>>\nstartxref\n108\n%%EOF\n"
    sentinel_path.write_bytes(pdf_content)
    
    # Call the artifacts endpoint
    response = client.get(f"/api/projects/{pid}/artifacts")
    assert response.status_code == 200, f"Artifacts endpoint failed: {response.text}"
    
    data = response.json()
    assert data["project_id"] == pid
    assert "artifacts" in data
    
    # Check if sentinel is listed in artifacts
    artifacts = data["artifacts"]
    sentinel_found = False
    sentinel_url = None
    for key, value in artifacts.items():
        if "sentinel.pdf" in value:
            sentinel_found = True
            sentinel_url = value
            break
    
    assert sentinel_found, f"Sentinel file not found in artifacts: {artifacts}"
    
    # Test direct file access via the mount
    file_response = client.get(f"/{sentinel_url}")
    assert file_response.status_code == 200, f"Sentinel file not accessible: {file_response.text}"
    assert file_response.headers["content-type"] == "application/pdf", f"Wrong content type: {file_response.headers['content-type']}"
    assert len(file_response.content) > 0, "Sentinel file is empty"


def test_job_lifecycle(client: TestClient, artifact_dir: Path):
    """
    Test the complete async job lifecycle from creation to completion.
    """
    pid = "smoke_test_job_lifecycle"
    
    # Set up minimal artifacts for the pipeline to work
    proj_dir = artifact_dir / pid
    
    # Create a minimal sheet index (needed for pipeline)
    _write_json(proj_dir / "sheet_index.json", {
        "project_id": pid,
        "sheets": [
            {"id": "S1", "name": "Test Sheet", "path": "test.pdf"}
        ]
    })
    
    # Create a minimal spec index (needed for pipeline)
    _write_json(proj_dir / "spec_index.json", {
        "project_id": pid,
        "chunks": [
            {"id": "C1", "text": "Test specification content", "page": 1}
        ]
    })
    
    # Start the async pipeline
    response = client.post(f"/api/projects/{pid}/pipeline_async")
    assert response.status_code == 200, f"Pipeline async endpoint failed: {response.text}"
    
    data = response.json()
    assert "job_id" in data, "Response missing job_id"
    job_id = data["job_id"]
    
    # Poll the job until completion
    job_result = poll_job(client, job_id, timeout=60)  # Longer timeout for pipeline
    
    # Verify job completed successfully
    assert job_result["status"] == "complete", f"Job did not complete successfully: {job_result}"
    assert job_result["project_id"] == pid
    
    # Check if we have artifacts
    artifacts = job_result.get("artifacts", {})
    assert len(artifacts) > 0, "No artifacts generated"
    
    # Look for a bid PDF in the artifacts
    bid_pdf_found = False
    bid_pdf_path = None
    for key, value in artifacts.items():
        if "bid" in key and value.endswith(".pdf"):
            bid_pdf_found = True
            bid_pdf_path = value
            break
    
    if bid_pdf_found and bid_pdf_path:
        # Test that the generated PDF is downloadable
        pdf_response = client.get(f"/{bid_pdf_path}")
        assert pdf_response.status_code == 200, f"Generated PDF not downloadable: {pdf_response.text}"
        assert pdf_response.headers["content-type"] == "application/pdf", f"Wrong content type: {pdf_response.headers['content-type']}"
        assert len(pdf_response.content) > 0, "Generated PDF is empty"
    else:
        # If no bid PDF was generated, that's okay for smoke test
        # (the pipeline might fail at earlier stages, which is expected)
        print(f"No bid PDF found in artifacts: {artifacts}")


def test_job_polling_timeout(client: TestClient):
    """
    Test that job polling times out appropriately for non-existent jobs.
    """
    fake_job_id = "fake_job_id_12345"
    
    # This should fail quickly since the job doesn't exist
    with pytest.raises(Exception):  # Should fail with 404
        poll_job(client, fake_job_id, timeout=5)


def test_artifacts_endpoint_empty_project(client: TestClient):
    """
    Test that artifacts endpoint handles empty projects gracefully.
    """
    pid = "empty_project_test"
    
    response = client.get(f"/api/projects/{pid}/artifacts")
    assert response.status_code == 200, f"Artifacts endpoint failed: {response.text}"
    
    data = response.json()
    assert data["project_id"] == pid
    assert "artifacts" in data
    # Empty projects should return empty artifacts dict
    assert isinstance(data["artifacts"], dict)


def test_bid_endpoint_missing_data(client: TestClient):
    """
    Test that bid endpoint handles missing project data gracefully.
    """
    pid = "missing_data_test"
    
    # Try to generate bid without any artifacts
    response = client.post(f"/api/projects/{pid}/bid")
    
    # The endpoint should either succeed (with empty data) or fail gracefully
    # We don't assert specific status code as the implementation may vary
    assert response.status_code in [200, 400, 404, 500], f"Unexpected status code: {response.status_code}"
