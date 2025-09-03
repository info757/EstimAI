"""
Tests for SQLite-backed job lifecycle functionality.

These tests verify that jobs can be created, updated, and retrieved
through the database layer with proper isolation.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone

from app.services.jobs import create_job, load_job, update_job
from app.services.db import get_job as db_get_job, delete_job
from app.models.jobs import JobStatus


@pytest.fixture
def temp_artifact_dir():
    """Create a temporary artifact directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir).resolve()
        
        # Set the environment variable for the test
        with patch.dict(os.environ, {'ARTIFACT_DIR': str(temp_path)}):
            yield temp_path


@pytest.fixture
def clean_db(temp_artifact_dir):
    """Ensure clean database state for each test."""
    # The database will be created automatically when first accessed
    # Each test gets a fresh temporary directory, so no cleanup needed
    yield


def test_create_and_get_job(clean_db):
    """Test creating a job and then retrieving it."""
    # Create a job
    job_id = create_job("demo")
    assert job_id is not None
    assert isinstance(job_id, str)
    assert len(job_id) > 0
    
    # Retrieve the job
    job = load_job(job_id)
    assert job is not None
    assert job.job_id == job_id
    assert job.project_id == "demo"
    assert job.status == JobStatus.queued
    assert job.job_type == "pipeline"
    
    # Verify timestamps are set
    assert job.created_at is not None
    assert job.updated_at is not None
    assert isinstance(job.created_at, datetime)
    assert isinstance(job.updated_at, datetime)
    
    # Clean up
    delete_job(job_id)


def test_update_success(clean_db):
    """Test updating a job to succeeded status with result."""
    # Create a job
    job_id = create_job("demo")
    
    try:
        # Update to running
        job = update_job(job_id, status=JobStatus.running)
        assert job.status == JobStatus.running
        
        # Update to complete with artifacts and meta
        artifacts_data = {
            "bid_pdf": "/artifacts/demo/bid/generated_bid.pdf"
        }
        meta_data = {
            "summary": {"total_cost": 50000, "line_items": 15}
        }
        
        job = update_job(
            job_id, 
            status=JobStatus.complete,
            artifacts=artifacts_data,
            meta=meta_data
        )
        
        assert job.status == JobStatus.complete
        
        # Verify the result is stored correctly
        db_job = db_get_job(job_id)
        assert db_job is not None
        assert db_job["status"] == "complete"
        # The database stores the combined data in result_json
        expected_result = {**artifacts_data, **meta_data}
        assert db_job["result"] == expected_result
        
        # Verify the result can be retrieved through the service layer
        retrieved_job = load_job(job_id)
        assert retrieved_job.status == JobStatus.complete
        assert retrieved_job.artifacts == artifacts_data
        assert retrieved_job.meta == meta_data
        
    finally:
        # Clean up
        delete_job(job_id)


def test_update_failure(clean_db):
    """Test updating a job to failed status with error."""
    # Create a job
    job_id = create_job("demo")
    
    try:
        # Update to running
        job = update_job(job_id, status=JobStatus.running)
        assert job.status == JobStatus.running
        
        # Update to failed with error
        error_text = "Traceback (most recent call last):\n  File \"pipeline.py\", line 42, in <module>\n    result = run_scope(pid)\nValueError: Invalid project data"
        
        job = update_job(
            job_id, 
            status=JobStatus.failed,
            error=error_text
        )
        
        assert job.status == JobStatus.failed
        assert job.error == error_text
        
        # Verify the error is stored correctly in the database
        db_job = db_get_job(job_id)
        assert db_job is not None
        assert db_job["status"] == "failed"
        assert db_job["error_text"] == error_text
        
        # Verify the error can be retrieved through the service layer
        retrieved_job = load_job(job_id)
        assert retrieved_job.status == JobStatus.failed
        assert retrieved_job.error == error_text
        
    finally:
        # Clean up
        delete_job(job_id)


def test_job_lifecycle_complete(clean_db):
    """Test the complete job lifecycle: queued -> running -> succeeded."""
    # Create a job
    job_id = create_job("demo")
    
    try:
        # Initial state: queued
        job = load_job(job_id)
        assert job.status == JobStatus.queued
        
        # Update to running
        job = update_job(job_id, status=JobStatus.running, message="Processing started")
        assert job.status == JobStatus.running
        assert job.message == "Processing started"
        
        # Update to complete with artifacts and meta
        artifacts_data = {
            "bid_pdf": "/artifacts/demo/bid/final_bid.pdf"
        }
        meta_data = {
            "summary": {"status": "completed", "duration_ms": 1500},
            "metadata": {"steps_completed": 5, "errors": 0}
        }
        
        job = update_job(
            job_id, 
            status=JobStatus.complete,
            artifacts=artifacts_data,
            meta=meta_data,
            message="Pipeline completed successfully"
        )
        
        assert job.status == JobStatus.complete
        assert job.message == "Pipeline completed successfully"
        assert job.artifacts == artifacts_data
        assert job.meta == meta_data
        
        # Verify final state in database
        db_job = db_get_job(job_id)
        assert db_job["status"] == "complete"
        # The database stores the combined data in result_json
        expected_result = {**artifacts_data, **meta_data}
        assert db_job["result"] == expected_result
        
        # Verify through service layer
        final_job = load_job(job_id)
        assert final_job.status == JobStatus.complete
        assert final_job.artifacts == artifacts_data
        assert final_job.meta == meta_data
        # Note: message is not stored in database, only in JobRecord object
        
    finally:
        # Clean up
        delete_job(job_id)


def test_job_lifecycle_with_failure(clean_db):
    """Test the complete job lifecycle with failure: queued -> running -> failed."""
    # Create a job
    job_id = create_job("demo")
    
    try:
        # Initial state: queued
        job = load_job(job_id)
        assert job.status == JobStatus.queued
        
        # Update to running
        job = update_job(job_id, status=JobStatus.running, message="Processing started")
        assert job.status == JobStatus.running
        
        # Update to failed with error
        error_text = "Pipeline failed: Invalid input data\nTraceback:\n  File \"pipeline.py\", line 25\n    validate_input(data)\nValueError: Required field 'project_id' missing"
        
        job = update_job(
            job_id, 
            status=JobStatus.failed,
            error=error_text,
            message="Pipeline failed"
        )
        
        assert job.status == JobStatus.failed
        assert job.error == error_text
        assert job.message == "Pipeline failed"
        
        # Verify final state in database
        db_job = db_get_job(job_id)
        assert db_job["status"] == "failed"
        assert db_job["error_text"] == error_text
        
        # Verify through service layer
        final_job = load_job(job_id)
        assert final_job.status == JobStatus.failed
        assert final_job.error == error_text
        # Note: message is not stored in database, only in JobRecord object
        
    finally:
        # Clean up
        delete_job(job_id)


def test_multiple_jobs_isolation(clean_db):
    """Test that multiple jobs can coexist without interference."""
    # Create multiple jobs
    job_id_1 = create_job("project-a")
    job_id_2 = create_job("project-b")
    job_id_3 = create_job("project-c")
    
    try:
        # Update jobs to different states
        update_job(job_id_1, status=JobStatus.running)
        update_job(job_id_2, status=JobStatus.complete, meta={"summary": "Project B completed"})
        update_job(job_id_3, status=JobStatus.failed, error="Project C failed")
        
        # Verify each job maintains its state
        job_1 = load_job(job_id_1)
        job_2 = load_job(job_id_2)
        job_3 = load_job(job_id_3)
        
        assert job_1.status == JobStatus.running
        assert job_1.project_id == "project-a"
        
        assert job_2.status == JobStatus.complete
        assert job_2.project_id == "project-b"
        assert job_2.meta == {"summary": "Project B completed"}
        
        assert job_3.status == JobStatus.failed
        assert job_3.project_id == "project-c"
        assert job_3.error == "Project C failed"
        
    finally:
        # Clean up all jobs
        delete_job(job_id_1)
        delete_job(job_id_2)
        delete_job(job_id_3)


def test_job_timestamps_consistency(clean_db):
    """Test that job timestamps are consistent and properly updated."""
    # Create a job
    job_id = create_job("demo")
    
    try:
        # Get initial timestamps
        initial_job = load_job(job_id)
        initial_created = initial_job.created_at
        initial_updated = initial_job.updated_at
        
        # Verify timestamps are close to current time
        now = datetime.now(timezone.utc)
        assert abs((now - initial_created).total_seconds()) < 5  # Within 5 seconds
        assert abs((now - initial_updated).total_seconds()) < 5
        
        # Update the job
        update_job(job_id, status=JobStatus.running)
        
        # Verify created_at didn't change but updated_at did
        updated_job = load_job(job_id)
        assert updated_job.created_at == initial_created
        assert updated_job.updated_at >= initial_updated  # Use >= since updates can be fast
        
        # Update again
        update_job(job_id, status=JobStatus.complete, meta={"done": True})
        
        # Verify timestamps again
        final_job = load_job(job_id)
        assert final_job.created_at == initial_created
        assert final_job.updated_at >= updated_job.updated_at  # Use >= since updates can be fast
        
    finally:
        # Clean up
        delete_job(job_id)
