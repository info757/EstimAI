"""
Tests for the health endpoint.
"""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_ok():
    """Test GET /health returns 200 with expected JSON structure."""
    response = client.get("/health")
    
    # Check status code
    assert response.status_code == 200
    
    # Parse JSON response
    data = response.json()
    
    # Check required keys exist
    assert "status" in data
    assert "uptime_seconds" in data
    assert "version" in data
    
    # Check status is "ok"
    assert data["status"] == "ok"
    
    # Check uptime_seconds is a non-negative float
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["uptime_seconds"] >= 0
    
    # Check version is a string
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0


def test_health_response_structure():
    """Test health response has exactly the expected structure."""
    response = client.get("/health")
    data = response.json()
    
    # Should have exactly 3 fields
    expected_keys = {"status", "uptime_seconds", "version"}
    assert set(data.keys()) == expected_keys
    
    # No extra fields
    assert len(data) == 3


def test_health_uptime_increases():
    """Test that uptime increases between requests."""
    response1 = client.get("/health")
    data1 = response1.json()
    
    # Small delay
    import time
    time.sleep(0.1)
    
    response2 = client.get("/health")
    data2 = response2.json()
    
    # Uptime should increase
    assert data2["uptime_seconds"] > data1["uptime_seconds"]
