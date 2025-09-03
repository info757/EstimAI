"""
Tests for authentication routes.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_login_success():
    """Test successful login with valid credentials."""
    response = client.post(
        "/api/auth/login",
        json={"username": "demo@example.com", "password": "demo123"}
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert "token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "demo@example.com"
    assert data["user"]["name"] == "Demo User"
    
    # Verify token is a valid JWT
    token = data["token"]
    assert len(token) > 0
    assert token.count('.') == 2  # JWT has 3 parts separated by dots


def test_login_invalid_username():
    """Test login with invalid username."""
    response = client.post(
        "/api/auth/login",
        json={"username": "nonexistent@example.com", "password": "demo123"}
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "Incorrect username or password" in data["detail"]


def test_login_invalid_password():
    """Test login with invalid password."""
    response = client.post(
        "/api/auth/login",
        json={"username": "demo@example.com", "password": "wrongpassword"}
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "Incorrect username or password" in data["detail"]


def test_login_missing_fields():
    """Test login with missing fields."""
    response = client.post(
        "/api/auth/login",
        json={"username": "demo@example.com"}
    )
    
    assert response.status_code == 422  # Validation error


def test_protected_endpoint_without_token():
    """Test that protected endpoints require authentication."""
    response = client.post("/api/projects/test-pid/pipeline_async")
    
    assert response.status_code == 403  # FastAPI returns 403 Forbidden for missing auth
    data = response.json()
    assert "detail" in data
    assert "Not authenticated" in data["detail"]


def test_protected_endpoint_with_valid_token():
    """Test that protected endpoints work with valid token."""
    # First get a token
    login_response = client.post(
        "/api/auth/login",
        json={"username": "demo@example.com", "password": "demo123"}
    )
    assert login_response.status_code == 200
    
    token = login_response.json()["token"]
    
    # Use token to access protected endpoint
    response = client.post(
        "/api/projects/test-pid/pipeline_async",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data


def test_health_endpoint_public():
    """Test that health endpoint remains public."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"
