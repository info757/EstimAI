"""
Tests for the SQLite database service (PR 14).
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from backend.app.services.db import (
    get_conn, create_job, update_job, get_job, 
    list_jobs, delete_job, get_job_count
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    # Mock the artifacts directory to use our temp file
    with patch('app.services.db.jobs_db_path') as mock_path:
        mock_path.return_value = Path(db_path)
        
        # Create the database and tables
        conn = get_conn()
        conn.close()
        
        yield db_path
        
        # Cleanup
        os.unlink(db_path)


def test_create_job(temp_db):
    """Test creating a new job."""
    with patch('app.services.db.jobs_db_path') as mock_path:
        mock_path.return_value = Path(temp_db)
        
        create_job("test-job-1", "test-project", "queued", "2025-01-01T00:00:00Z")
        
        # Verify job was created
        job = get_job("test-job-1")
        assert job is not None
        assert job['id'] == "test-job-1"
        assert job['pid'] == "test-project"
        assert job['status'] == "queued"
        assert job['created_at'] == "2025-01-01T00:00:00Z"
        assert job['updated_at'] == "2025-01-01T00:00:00Z"


def test_update_job(temp_db):
    """Test updating an existing job."""
    with patch('app.services.db.jobs_db_path') as mock_path:
        mock_path.return_value = Path(temp_db)
        
        # Create a job first
        create_job("test-job-2", "test-project", "queued", "2025-01-01T00:00:00Z")
        
        # Update the job
        update_job(
            "test-job-2", 
            "running", 
            "2025-01-01T01:00:00Z",
            result_json='{"status": "processing"}',
            error_text=None
        )
        
        # Verify job was updated
        job = get_job("test-job-2")
        assert job is not None
        assert job['status'] == "running"
        assert job['updated_at'] == "2025-01-01T01:00:00Z"
        assert job['result'] == {"status": "processing"}
        assert job['error_text'] is None


def test_get_job_not_found(temp_db):
    """Test getting a non-existent job."""
    with patch('app.services.db.jobs_db_path') as mock_path:
        mock_path.return_value = Path(temp_db)
        
        job = get_job("non-existent-job")
        assert job is None


def test_list_jobs(temp_db):
    """Test listing jobs."""
    with patch('app.services.db.jobs_db_path') as mock_path:
        mock_path.return_value = Path(temp_db)
        
        # Create multiple jobs
        create_job("job-1", "project-A", "queued", "2025-01-01T00:00:00Z")
        create_job("job-2", "project-A", "running", "2025-01-01T01:00:00Z")
        create_job("job-3", "project-B", "completed", "2025-01-01T02:00:00Z")
        
        # List all jobs
        all_jobs = list_jobs()
        assert len(all_jobs) == 3
        
        # List jobs for specific project
        project_a_jobs = list_jobs("project-A")
        assert len(project_a_jobs) == 2
        assert all(job['pid'] == "project-A" for job in project_a_jobs)


def test_delete_job(temp_db):
    """Test deleting a job."""
    with patch('app.services.db.jobs_db_path') as mock_path:
        mock_path.return_value = Path(temp_db)
        
        # Create a job
        create_job("job-to-delete", "test-project", "queued", "2025-01-01T00:00:00Z")
        
        # Verify it exists
        assert get_job("job-to-delete") is not None
        
        # Delete it
        deleted = delete_job("job-to-delete")
        assert deleted is True
        
        # Verify it's gone
        assert get_job("job-to-delete") is None
        
        # Try to delete non-existent job
        deleted = delete_job("non-existent")
        assert deleted is False


def test_get_job_count(temp_db):
    """Test getting job counts."""
    with patch('app.services.db.jobs_db_path') as mock_path:
        mock_path.return_value = Path(temp_db)
        
        # Initially no jobs
        assert get_job_count() == 0
        assert get_job_count("project-A") == 0
        
        # Create some jobs
        create_job("job-1", "project-A", "queued", "2025-01-01T00:00:00Z")
        create_job("job-2", "project-A", "running", "2025-01-01T01:00:00Z")
        create_job("job-3", "project-B", "completed", "2025-01-01T02:00:00Z")
        
        # Check counts
        assert get_job_count() == 3
        assert get_job_count("project-A") == 2
        assert get_job_count("project-B") == 1


def test_database_connection_configuration(temp_db):
    """Test that database connection is properly configured."""
    with patch('app.services.db.jobs_db_path') as mock_path:
        mock_path.return_value = Path(temp_db)
        
        conn = get_conn()
        
        # Check WAL mode is enabled
        cursor = conn.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        assert journal_mode == "wal"
        
        # Check synchronous mode
        cursor = conn.execute("PRAGMA synchronous")
        synchronous = cursor.fetchone()[0]
        assert synchronous == 1  # NORMAL mode
        
        # Check foreign keys are enabled
        cursor = conn.execute("PRAGMA foreign_keys")
        foreign_keys = cursor.fetchone()[0]
        assert foreign_keys == 1
        
        conn.close()


def test_job_with_error(temp_db):
    """Test job with error text."""
    with patch('app.services.db.jobs_db_path') as mock_path:
        mock_path.return_value = Path(temp_db)
        
        create_job("error-job", "test-project", "failed", "2025-01-01T00:00:00Z")
        
        update_job(
            "error-job",
            "failed",
            "2025-01-01T01:00:00Z",
            result_json=None,
            error_text="Something went wrong during processing"
        )
        
        job = get_job("error-job")
        assert job is not None
        assert job['status'] == "failed"
        assert job['error_text'] == "Something went wrong during processing"
        assert job['result'] is None
