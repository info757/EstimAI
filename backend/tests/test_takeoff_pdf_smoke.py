"""
Smoke test for /v1/takeoff/pdf endpoint.

Tests the complete pipeline with bid_test.pdf and validates
that depth analysis results are included in the response.
"""
import pytest
import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.mark.skipif(not pytest.config.getoption("--apryse-enabled"), reason="Apryse not enabled")
def test_takeoff_pdf_smoke():
    """Smoke test for complete takeoff pipeline."""
    client = TestClient(app)
    
    # Load test PDF
    test_pdf_path = Path(__file__).parent.parent / "bid_test.pdf"
    if not test_pdf_path.exists():
        pytest.skip(f"Test PDF not found: {test_pdf_path}")
    
    # Upload PDF and call endpoint
    with open(test_pdf_path, "rb") as f:
        response = client.post(
            "/v1/takeoff/pdf",
            files={"file": ("bid_test.pdf", f, "application/pdf")}
        )
    
    # Validate response
    assert response.status_code == 200
    data = response.json()
    
    # Check basic structure
    assert "sheet_units" in data
    assert "networks" in data
    assert "roadway" in data
    assert "e_sc" in data
    assert "earthwork" in data
    assert "qa_flags" in data
    
    # Check networks structure
    networks = data["networks"]
    assert "storm" in networks
    assert "sanitary" in networks
    assert "water" in networks
    
    # Check for at least one pipe with depth analysis
    found_pipe_with_depth = False
    
    for network_name, network_data in networks.items():
        pipes = network_data.get("pipes", [])
        for pipe in pipes:
            # Check for depth analysis in extra field
            if "extra" in pipe and pipe["extra"]:
                extra = pipe["extra"]
                if "trench_volume_cy" in extra:
                    found_pipe_with_depth = True
                    # Validate depth analysis fields
                    assert "min_depth_ft" in extra
                    assert "max_depth_ft" in extra
                    assert "avg_depth_ft" in extra
                    assert "p95_depth_ft" in extra
                    assert "buckets_lf" in extra
                    assert "trench_volume_cy" in extra
                    assert "cover_ok" in extra
                    assert "deep_excavation" in extra
                    
                    # Validate trench volume is reasonable
                    trench_volume = extra["trench_volume_cy"]
                    assert isinstance(trench_volume, (int, float))
                    assert trench_volume >= 0
                    
                    # Validate depth values are reasonable
                    min_depth = extra["min_depth_ft"]
                    max_depth = extra["max_depth_ft"]
                    avg_depth = extra["avg_depth_ft"]
                    
                    assert isinstance(min_depth, (int, float))
                    assert isinstance(max_depth, (int, float))
                    assert isinstance(avg_depth, (int, float))
                    assert min_depth <= avg_depth <= max_depth
                    
                    break
    
    # Assert that we found at least one pipe with depth analysis
    assert found_pipe_with_depth, "No pipes found with depth analysis (trench_volume_cy)"
    
    # Check QA flags structure
    qa_flags = data["qa_flags"]
    assert isinstance(qa_flags, list)
    
    for flag in qa_flags:
        assert "code" in flag
        assert "message" in flag
        assert isinstance(flag["code"], str)
        assert isinstance(flag["message"], str)
    
    # Check earthwork structure
    earthwork = data["earthwork"]
    assert "cut_cy" in earthwork
    assert "fill_cy" in earthwork
    assert "undercut_cy" in earthwork
    assert "source" in earthwork
    
    # Check roadway structure
    roadway = data["roadway"]
    assert "curb_lf" in roadway
    assert "sidewalk_sf" in roadway
    
    # Check ESC structure
    e_sc = data["e_sc"]
    assert "silt_fence_lf" in e_sc
    assert "inlet_protection_ea" in e_sc


def test_takeoff_pdf_apryse_disabled():
    """Test that endpoint returns 422 when Apryse is disabled."""
    # This test would need to mock settings.APR_USE_APRYSE = False
    # For now, we'll skip it since we can't easily mock settings in this test
    pytest.skip("Requires mocking settings.APR_USE_APRYSE")


def test_takeoff_pdf_invalid_file():
    """Test that endpoint handles invalid files gracefully."""
    client = TestClient(app)
    
    # Test with non-PDF file
    response = client.post(
        "/v1/takeoff/pdf",
        files={"file": ("test.txt", b"not a pdf", "text/plain")}
    )
    
    # Should return 500 for processing error
    assert response.status_code == 500
    assert "Takeoff processing failed" in response.json()["detail"]


def test_takeoff_pdf_empty_file():
    """Test that endpoint handles empty files gracefully."""
    client = TestClient(app)
    
    # Test with empty file
    response = client.post(
        "/v1/takeoff/pdf",
        files={"file": ("empty.pdf", b"", "application/pdf")}
    )
    
    # Should return 500 for processing error
    assert response.status_code == 500
    assert "Takeoff processing failed" in response.json()["detail"]


def test_estimai_result_schema():
    """Test that EstimAIResult schema is properly structured."""
    from backend.app.schemas_estimai import EstimAIResult, StormNetwork, SanitaryNetwork, WaterNetwork
    
    # Create minimal valid result
    result = EstimAIResult(
        sheet_units="ft",
        networks={
            "storm": StormNetwork(),
            "sanitary": SanitaryNetwork(),
            "water": WaterNetwork()
        }
    )
    
    # Validate it can be serialized
    data = result.model_dump()
    assert data["sheet_units"] == "ft"
    assert "networks" in data
    assert "storm" in data["networks"]
    assert "sanitary" in data["networks"]
    assert "water" in data["networks"]
