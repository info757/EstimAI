"""
Tests for the job routes to ensure they work with the database and maintain API contract.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.services.jobs import create_job

client = TestClient(app)


def test_get_job_route_maintains_contract():
    """Test that GET /jobs/{id} returns the expected JobResponse format."""
    # Create a test job
    job_id = create_job("test-contract-project")
    
    try:
        # Get the job via the API route
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify all required fields are present
        required_fields = [
            "job_id", "project_id", "job_type", "status", 
            "created_at", "updated_at", "progress", "message", 
            "error", "artifacts", "meta"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Verify specific field values
        assert data["job_id"] == job_id
        assert data["project_id"] == "test-contract-project"
        assert data["job_type"] == "pipeline"
        assert data["status"] == "queued"
        assert data["progress"] == 0.0
        assert data["message"] is None
        assert data["error"] is None
        assert data["artifacts"] == {}
        assert data["meta"] == {}
        
    finally:
        # Clean up
        from app.services.db import delete_job
        delete_job(job_id)


def test_list_jobs_route_maintains_contract():
    """Test that GET /jobs returns the expected format for all jobs."""
    # Create test jobs
    job_id_1 = create_job("test-contract-project-1")
    job_id_2 = create_job("test-contract-project-2")
    
    try:
        # Get all jobs via the API route
        response = client.get("/api/jobs")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # Should have at least our test jobs
        
        # Find our test jobs
        test_jobs = [job for job in data if job["job_id"] in [job_id_1, job_id_2]]
        assert len(test_jobs) == 2
        
        # Verify each job has the required format
        for job in test_jobs:
            required_fields = [
                "job_id", "project_id", "job_type", "status", 
                "created_at", "updated_at", "progress", "message", 
                "error", "artifacts", "meta"
            ]
            
            for field in required_fields:
                assert field in job, f"Missing required field: {field}"
        
    finally:
        # Clean up
        from app.services.db import delete_job
        delete_job(job_id_1)
        delete_job(job_id_2)


def test_list_jobs_with_project_filter():
    """Test that GET /jobs?project_id=X filters correctly."""
    # Create test jobs
    job_id_1 = create_job("test-filter-project")
    job_id_2 = create_job("test-filter-project")
    job_id_3 = create_job("other-project")
    
    try:
        # Get jobs for specific project
        response = client.get("/api/jobs?project_id=test-filter-project")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # Should only have jobs from the specified project
        for job in data:
            assert job["project_id"] == "test-filter-project"
        
        # Should have at least our 2 test jobs
        test_job_ids = [job["job_id"] for job in data if job["job_id"] in [job_id_1, job_id_2]]
        assert len(test_job_ids) == 2
        
    finally:
        # Clean up
        from app.services.db import delete_job
        delete_job(job_id_1)
        delete_job(job_id_2)
        delete_job(job_id_3)


def test_get_job_not_found():
    """Test that GET /jobs/{id} returns 404 for non-existent jobs."""
    response = client.get("/api/jobs/non-existent-job-id")
    assert response.status_code == 404
    
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"]


def test_pipeline_async_creates_job():
    """Test that POST /projects/{pid}/pipeline_async creates a job and returns job_id."""
    response = client.post("/api/projects/test-pipeline-project/pipeline_async")
    assert response.status_code == 200
    
    data = response.json()
    assert "job_id" in data
    assert isinstance(data["job_id"], str)
    assert len(data["job_id"]) > 0
    
    # Verify the job was actually created in the database
    job_id = data["job_id"]
    job_response = client.get(f"/api/jobs/{job_id}")
    assert job_response.status_code == 200
    
    job_data = job_response.json()
    assert job_data["job_id"] == job_id
    assert job_data["project_id"] == "test-pipeline-project"
    # The job status might be "queued" or "running" depending on timing
    assert job_data["status"] in ["queued", "running"]
    
    # Clean up
    from app.services.db import delete_job
    delete_job(job_id)
