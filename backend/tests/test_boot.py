"""
Boot test to verify the application can start and respond to health checks.

This test ensures that:
1. The application factory creates a working FastAPI app
2. All imports resolve correctly
3. The health endpoint responds properly
4. No circular import issues exist
"""
from backend.app.app import create_app
from fastapi.testclient import TestClient


def test_boot_and_health():
    """Test that the application boots successfully and health endpoint works."""
    app = create_app()
    client = TestClient(app)
    
    # Test the health endpoint
    r = client.get("/_healthz")
    assert r.status_code == 200
    assert r.json().get("ok") is True
    
    # Test the main health endpoint
    r = client.get("/health")
    assert r.status_code == 200
    health_data = r.json()
    assert health_data.get("status") == "healthy"
    assert health_data.get("service") == "estimai-backend"
    
    # Test the root endpoint
    r = client.get("/")
    assert r.status_code == 200
    root_data = r.json()
    assert "message" in root_data
    assert "version" in root_data


def test_app_creation():
    """Test that the application factory creates a valid FastAPI app."""
    app = create_app()
    
    # Verify it's a FastAPI app
    assert hasattr(app, 'routes')
    assert hasattr(app, 'middleware')
    
    # Verify key routes are registered
    route_paths = [route.path for route in app.routes]
    assert "/_healthz" in route_paths
    assert "/health" in route_paths
    assert "/" in route_paths
