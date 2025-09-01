"""
Test review endpoint roundtrip functionality.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_pid():
    return "test_roundtrip"


@pytest.fixture
def sample_takeoff_data():
    """Sample takeoff data for testing."""
    return [
        {
            "id": "takeoff-001",
            "description": "Concrete foundation",
            "qty": 100,
            "unit": "LF",
            "confidence": 0.85
        },
        {
            "id": "takeoff-002",
            "description": "Steel beams",
            "qty": 25,
            "unit": "EA",
            "confidence": 0.92
        }
    ]


@pytest.fixture
def sample_estimate_data():
    """Sample estimate data for testing."""
    return [
        {
            "id": "estimate-001",
            "description": "Concrete foundation",
            "qty": 100,
            "unit": "LF",
            "unit_cost": 45.0,
            "total": 4500.0
        },
        {
            "id": "estimate-002",
            "description": "Steel beams",
            "qty": 25,
            "unit": "EA",
            "unit_cost": 120.0,
            "total": 3000.0
        }
    ]


def test_takeoff_review_roundtrip(client, test_pid, sample_takeoff_data, tmp_path):
    """Test full roundtrip: GET -> PATCH -> GET for takeoff review."""
    
    # Mock the pipeline service to return our sample data
    with patch('app.api.routes_review.latest_stage_rows') as mock_latest, \
         patch('app.api.routes_review.load_overrides') as mock_overrides, \
         patch('app.api.routes_review.save_overrides') as mock_save:
        
        # Initial state: no overrides
        mock_latest.return_value = sample_takeoff_data
        mock_overrides.return_value = []
        mock_save.return_value = True
        
        # Step 1: GET /review/takeoff
        response = client.get(f"/api/projects/{test_pid}/review/takeoff")
        assert response.status_code == 200
        
        data = response.json()
        assert data["project_id"] == test_pid
        assert data["stage"] == "takeoff"
        assert data["total_rows"] == 2
        assert data["overridden_rows"] == 0
        
        # Verify initial row data
        rows = data["rows"]
        assert len(rows) == 2
        
        row1 = rows[0]
        assert row1["id"] == "takeoff-001"
        assert row1["ai"]["qty"] == 100
        assert row1["override"] is None
        assert row1["merged"]["qty"] == 100
        
        # Step 2: PATCH /review/takeoff with qty change
        patch_request = {
            "patches": [
                {
                    "id": "takeoff-001",
                    "fields": {"qty": 150},
                    "by": "test_user",
                    "reason": "field verification"
                }
            ]
        }
        
        response = client.patch(
            f"/api/projects/{test_pid}/review/takeoff",
            json=patch_request
        )
        assert response.status_code == 200
        
        patch_response = response.json()
        assert patch_response["ok"] is True
        assert patch_response["patched"] == 1
        
        # Step 3: GET /review/takeoff again - should show override
        # Mock load_overrides to return our patch
        mock_overrides.return_value = [
            {
                "id": "takeoff-001",
                "fields": {"qty": 150},
                "by": "test_user",
                "reason": "field verification",
                "at": "2025-09-02T12:00:00Z"
            }
        ]
        
        response = client.get(f"/api/projects/{test_pid}/review/takeoff")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_rows"] == 2
        assert data["overridden_rows"] == 1
        
        # Verify the override is applied
        rows = data["rows"]
        row1 = rows[0]
        assert row1["id"] == "takeoff-001"
        assert row1["ai"]["qty"] == 100  # Original unchanged
        assert row1["override"]["qty"] == 150  # Override present
        assert row1["merged"]["qty"] == 150  # Merged shows override
        # Note: override only contains fields, not metadata like 'by'
        
        # Second row should be unchanged
        row2 = rows[1]
        assert row2["id"] == "takeoff-002"
        assert row2["override"] is None
        assert row2["merged"]["qty"] == 25


def test_estimate_review_roundtrip(client, test_pid, sample_estimate_data, tmp_path):
    """Test full roundtrip: GET -> PATCH -> GET for estimate review."""
    
    # Mock the pipeline service to return our sample data
    with patch('app.api.routes_review.latest_stage_rows') as mock_latest, \
         patch('app.api.routes_review.load_overrides') as mock_overrides, \
         patch('app.api.routes_review.save_overrides') as mock_save:
        
        # Initial state: no overrides
        mock_latest.return_value = sample_estimate_data
        mock_overrides.return_value = []
        mock_save.return_value = True
        
        # Step 1: GET /review/estimate
        response = client.get(f"/api/projects/{test_pid}/review/estimate")
        assert response.status_code == 200
        
        data = response.json()
        assert data["project_id"] == test_pid
        assert data["stage"] == "estimate"
        assert data["total_rows"] == 2
        assert data["overridden_rows"] == 0
        
        # Verify initial row data
        rows = data["rows"]
        assert len(rows) == 2
        
        row1 = rows[0]
        assert row1["id"] == "estimate-001"
        assert row1["ai"]["unit_cost"] == 45.0
        assert row1["ai"]["total"] == 4500.0
        assert row1["override"] is None
        assert row1["merged"]["unit_cost"] == 45.0
        
        # Step 2: PATCH /review/estimate with unit_cost and profit changes
        patch_request = {
            "patches": [
                {
                    "id": "estimate-001",
                    "fields": {"unit_cost": 55.0},
                    "by": "reviewer",
                    "reason": "updated market rates"
                },
                {
                    "id": "estimate-002",
                    "fields": {"unit_cost": 130.0, "profit_pct": 8.0},
                    "by": "reviewer",
                    "reason": "premium material pricing"
                }
            ]
        }
        
        response = client.patch(
            f"/api/projects/{test_pid}/review/estimate",
            json=patch_request
        )
        assert response.status_code == 200
        
        patch_response = response.json()
        assert patch_response["ok"] is True
        assert patch_response["patched"] == 2
        
        # Step 3: GET /review/estimate again - should show overrides
        # Mock load_overrides to return our patches
        mock_overrides.return_value = [
            {
                "id": "estimate-001",
                "fields": {"unit_cost": 55.0},
                "by": "reviewer",
                "reason": "updated market rates",
                "at": "2025-09-02T12:00:00Z"
            },
            {
                "id": "estimate-002",
                "fields": {"unit_cost": 130.0, "profit_pct": 8.0},
                "by": "reviewer",
                "reason": "premium material pricing",
                "at": "2025-09-02T12:00:00Z"
            }
        ]
        
        response = client.get(f"/api/projects/{test_pid}/review/estimate")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_rows"] == 2
        assert data["overridden_rows"] == 2
        
        # Verify the overrides are applied
        rows = data["rows"]
        
        # First row override
        row1 = rows[0]
        assert row1["id"] == "estimate-001"
        assert row1["ai"]["unit_cost"] == 45.0  # Original unchanged
        assert row1["override"]["unit_cost"] == 55.0  # Override present
        assert row1["merged"]["unit_cost"] == 55.0  # Merged shows override
        # Note: override only contains fields, not metadata like 'by'
        
        # Second row override
        row2 = rows[1]
        assert row2["id"] == "estimate-002"
        assert row2["ai"]["unit_cost"] == 120.0  # Original unchanged
        assert row2["override"]["unit_cost"] == 130.0  # Override present
        assert row2["override"]["profit_pct"] == 8.0  # Additional field
        assert row2["merged"]["unit_cost"] == 130.0  # Merged shows override
        assert row2["merged"]["profit_pct"] == 8.0  # Merged shows additional field


def test_review_roundtrip_with_real_files(client, test_pid, tmp_path):
    """Test roundtrip with actual file operations (optional integration test)."""
    
    # This test could be used to test with real file operations
    # For now, we'll skip it as it requires more complex setup
    pytest.skip("Integration test with real files - requires more setup")
    
    # TODO: Create actual artifact files and test real roundtrip
    # This would involve:
    # 1. Creating actual JSON files in artifacts/{test_pid}/takeoff/
    # 2. Running the endpoints without mocking
    # 3. Verifying files are created/updated correctly
