"""
Test review endpoints for HITL overrides.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.review import Patch, PatchRequest


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_pid():
    return "test_project"


@pytest.fixture
def sample_takeoff_data():
    return [
        {
            "id": "item_1",
            "description": "Concrete foundation",
            "qty": 100,
            "unit": "LF",
            "confidence": 0.85
        },
        {
            "id": "item_2", 
            "description": "Steel beams",
            "qty": 25,
            "unit": "EA",
            "confidence": 0.92
        }
    ]


@pytest.fixture
def sample_estimate_data():
    return [
        {
            "id": "item_1",
            "description": "Concrete foundation",
            "qty": 100,
            "unit": "LF",
            "unit_cost": 45.0,
            "total": 4500.0
        },
        {
            "id": "item_2",
            "description": "Steel beams", 
            "qty": 25,
            "unit": "EA",
            "unit_cost": 120.0,
            "total": 3000.0
        }
    ]


def test_get_takeoff_review_empty(client, test_pid, tmp_path):
    """Test GET /review/takeoff with no data."""
    with patch('app.services.pipeline.latest_stage_rows') as mock_latest, \
         patch('app.services.overrides.load_overrides') as mock_overrides:
        
        mock_latest.return_value = []
        mock_overrides.return_value = []
        
        response = client.get(f"/api/projects/{test_pid}/review/takeoff")
        
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == test_pid
        assert data["stage"] == "takeoff"
        assert data["total_rows"] == 0
        assert data["overridden_rows"] == 0
        assert data["rows"] == []


def test_get_takeoff_review_with_data(client, test_pid, sample_takeoff_data, tmp_path):
    """Test GET /review/takeoff with sample data."""
    with patch('app.api.routes_review.latest_stage_rows') as mock_latest, \
         patch('app.api.routes_review.load_overrides') as mock_overrides:
        
        mock_latest.return_value = sample_takeoff_data
        mock_overrides.return_value = []
        
        response = client.get(f"/api/projects/{test_pid}/review/takeoff")
        
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == test_pid
        assert data["stage"] == "takeoff"
        assert data["total_rows"] == 2
        assert data["overridden_rows"] == 0
        
        rows = data["rows"]
        assert len(rows) == 2
        
        # Check first row structure
        row1 = rows[0]
        assert row1["id"] == "item_1"
        assert row1["ai"]["description"] == "Concrete foundation"
        assert row1["ai"]["qty"] == 100
        assert row1["override"] is None
        assert row1["merged"]["description"] == "Concrete foundation"
        assert row1["confidence"] == 0.85


def test_get_takeoff_review_with_overrides(client, test_pid, sample_takeoff_data, tmp_path):
    """Test GET /review/takeoff with overrides applied."""
    with patch('app.api.routes_review.latest_stage_rows') as mock_latest, \
         patch('app.api.routes_review.load_overrides') as mock_overrides:
        
        mock_latest.return_value = sample_takeoff_data
        mock_overrides.return_value = [
            {
                "id": "item_1",
                "fields": {"qty": 150, "unit": "LF"},
                "by": "estimator",
                "reason": "Site conditions",
                "at": "2025-09-01T12:00:00Z"
            }
        ]
        
        response = client.get(f"/api/projects/{test_pid}/review/takeoff")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_rows"] == 2
        assert data["overridden_rows"] == 1
        
        rows = data["rows"]
        row1 = rows[0]
        assert row1["id"] == "item_1"
        assert row1["ai"]["qty"] == 100  # Original
        assert row1["override"]["qty"] == 150  # Override
        assert row1["merged"]["qty"] == 150  # Merged
        # Note: override only contains fields, not metadata like 'by'


def test_patch_takeoff_review(client, test_pid, tmp_path):
    """Test PATCH /review/takeoff to apply patches."""
    with patch('app.services.overrides.save_overrides') as mock_save:
        mock_save.return_value = True
        
        patch_request = {
            "patches": [
                {
                    "id": "item_1",
                    "fields": {"qty": 150, "unit": "LF"},
                    "by": "estimator",
                    "reason": "Site conditions"
                }
            ]
        }
        
        response = client.patch(
            f"/api/projects/{test_pid}/review/takeoff",
            json=patch_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["patched"] == 1
        assert data["project_id"] == test_pid
        assert data["stage"] == "takeoff"
        assert "Successfully applied" in data["message"]


def test_get_estimate_review_empty(client, test_pid, tmp_path):
    """Test GET /review/estimate with no data."""
    with patch('app.services.pipeline.latest_stage_rows') as mock_latest, \
         patch('app.services.overrides.load_overrides') as mock_overrides:
        
        mock_latest.return_value = []
        mock_overrides.return_value = []
        
        response = client.get(f"/api/projects/{test_pid}/review/estimate")
        
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == test_pid
        assert data["stage"] == "estimate"
        assert data["total_rows"] == 0
        assert data["overridden_rows"] == 0


def test_get_estimate_review_with_data(client, test_pid, sample_estimate_data, tmp_path):
    """Test GET /review/estimate with sample data."""
    with patch('app.api.routes_review.latest_stage_rows') as mock_latest, \
         patch('app.api.routes_review.load_overrides') as mock_overrides:
        
        mock_latest.return_value = sample_estimate_data
        mock_overrides.return_value = []
        
        response = client.get(f"/api/projects/{test_pid}/review/estimate")
        
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == test_pid
        assert data["stage"] == "estimate"
        assert data["total_rows"] == 2
        assert data["overridden_rows"] == 0
        
        rows = data["rows"]
        assert len(rows) == 2
        
        # Check first row structure
        row1 = rows[0]
        assert row1["id"] == "item_1"
        assert row1["ai"]["unit_cost"] == 45.0
        assert row1["ai"]["total"] == 4500.0
        assert row1["override"] is None
        assert row1["merged"]["unit_cost"] == 45.0


def test_patch_estimate_review(client, test_pid, tmp_path):
    """Test PATCH /review/estimate to apply patches."""
    with patch('app.services.overrides.save_overrides') as mock_save:
        mock_save.return_value = True
        
        patch_request = {
            "patches": [
                {
                    "id": "item_1",
                    "fields": {"unit_cost": 55.0},
                    "by": "reviewer",
                    "reason": "Updated market rates"
                }
            ]
        }
        
        response = client.patch(
            f"/api/projects/{test_pid}/review/estimate",
            json=patch_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["patched"] == 1
        assert data["project_id"] == test_pid
        assert data["stage"] == "estimate"
        assert "Successfully applied" in data["message"]


def test_patch_review_save_failure(client, test_pid, tmp_path):
    """Test PATCH when save_overrides fails."""
    with patch('app.api.routes_review.save_overrides') as mock_save:
        mock_save.return_value = False
        
        patch_request = {
            "patches": [
                {
                    "id": "item_1",
                    "fields": {"qty": 150},
                    "by": "estimator",
                    "reason": "Test"
                }
            ]
        }
        
        response = client.patch(
            f"/api/projects/{test_pid}/review/takeoff",
            json=patch_request
        )
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to save overrides" in data["detail"]


def test_get_review_invalid_project(client, tmp_path):
    """Test GET review with invalid project ID."""
    with patch('app.api.routes_review.latest_stage_rows') as mock_latest:
        mock_latest.side_effect = Exception("Project not found")
        
        response = client.get("/api/projects/invalid/review/takeoff")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to load takeoff review" in data["detail"]


def test_patch_review_invalid_data(client, test_pid):
    """Test PATCH with invalid request data."""
    response = client.patch(
        f"/api/projects/{test_pid}/review/takeoff",
        json={"invalid": "data"}
    )
    
    assert response.status_code == 422  # Validation error
