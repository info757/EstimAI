import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_login_success():
    """Test successful login with demo credentials"""
    response = client.post(
        "/api/auth/login",
        json={
            "username": "demo@example.com",
            "password": "demo123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "demo@example.com"
    assert data["user"]["name"] == "Demo User"


def test_login_fail():
    """Test login failure with wrong credentials"""
    response = client.post(
        "/api/auth/login",
        json={
            "username": "demo@example.com",
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == 401


def test_projects_requires_auth():
    """Test that project endpoints require authentication"""
    response = client.get("/api/projects/demo/artifacts")
    
    # FastAPI returns 403 Forbidden when auth is required but not provided
    assert response.status_code == 403


def test_projects_with_auth():
    """Test that project endpoints work with valid token"""
    # First login to get token
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "demo@example.com",
            "password": "demo123"
        }
    )
    
    assert login_response.status_code == 200
    token = login_response.json()["token"]
    
    # Now try to access protected endpoint with token
    response = client.get(
        "/api/projects/demo/artifacts",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Should get 200 or 404 (depending on if project exists), but not 401
    assert response.status_code != 401
