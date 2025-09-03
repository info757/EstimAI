import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import shutil
import os

from app.services.ingest import ingest_files
from app.core.paths import project_ingest_dir, project_ingest_raw_dir, project_ingest_parsed_dir


class TestIngestService:
    """Test the ingest service functionality."""
    
    @pytest.fixture
    def temp_artifacts_dir(self):
        """Create a temporary artifacts directory for testing."""
        temp_dir = tempfile.mkdtemp()
        original_artifacts_dir = os.environ.get('ARTIFACT_DIR')
        os.environ['ARTIFACT_DIR'] = temp_dir
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
        if original_artifacts_dir:
            os.environ['ARTIFACT_DIR'] = original_artifacts_dir
        else:
            del os.environ['ARTIFACT_DIR']
    
    @pytest.fixture
    def mock_upload_file(self):
        """Create a mock upload file for testing."""
        mock_file = Mock()
        mock_file.filename = "test_document.pdf"
        mock_file.content_type = "application/pdf"
        
        # Create a mock file content
        content = b"Test PDF content for ingestion"
        mock_file.file.read.side_effect = [content, b""]  # First read returns content, second returns empty
        
        return mock_file
    
    def test_project_ingest_directories_created(self, temp_artifacts_dir):
        """Test that ingest directories are created correctly."""
        pid = "test-project-123"
        
        # Create directories
        ingest_dir = project_ingest_dir(pid)
        raw_dir = project_ingest_raw_dir(pid)
        parsed_dir = project_ingest_parsed_dir(pid)
        
        # Verify directories exist
        assert ingest_dir.exists()
        assert raw_dir.exists()
        assert parsed_dir.exists()
        
        # Verify paths are correct
        assert str(ingest_dir).endswith(f"test-project-123/ingest")
        assert str(raw_dir).endswith(f"test-project-123/ingest/raw")
        assert str(parsed_dir).endswith(f"test-project-123/ingest/parsed")
    
    def test_ingest_files_basic_functionality(self, temp_artifacts_dir, mock_upload_file):
        """Test basic ingest functionality with a mock file."""
        pid = "test-project-123"
        job_id = "test-job-456"
        
        # Run ingest
        result = ingest_files(pid, [mock_upload_file], job_id)
        
        # Verify result structure
        assert "files_count" in result
        assert "items" in result
        assert result["files_count"] == 1
        assert len(result["items"]) == 1
        
        # Verify item structure
        item = result["items"][0]
        assert "filename" in item
        assert "content_hash" in item
        assert "size" in item
        assert "content_type" in item
        assert "raw_path" in item
        assert "parsed_path" in item
        
        # Verify file was saved
        raw_dir = project_ingest_raw_dir(pid)
        parsed_dir = project_ingest_parsed_dir(pid)
        
        # Check that raw file exists
        raw_files = list(raw_dir.glob("*"))
        assert len(raw_files) == 1
        
        # Check that parsed record exists
        parsed_files = list(parsed_dir.glob("*.json"))
        assert len(parsed_files) == 1
        
        # Verify content hash is correct
        expected_content = b"Test PDF content for ingestion"
        import hashlib
        expected_hash = hashlib.sha256(expected_content).hexdigest()
        assert item["content_hash"] == expected_hash
        
        # Verify file size is correct
        assert item["size"] == len(expected_content)
    
    def test_ingest_files_multiple_files(self, temp_artifacts_dir):
        """Test ingest with multiple files."""
        pid = "test-project-123-multi"
        job_id = "test-job-456"
        
        # Create multiple mock files
        mock_files = []
        for i in range(3):
            mock_file = Mock()
            mock_file.filename = f"document_{i}.pdf"
            mock_file.content_type = "application/pdf"
            content = f"Content for document {i}".encode()
            mock_file.file.read.side_effect = [content, b""]
            mock_files.append(mock_file)
        
        # Run ingest
        result = ingest_files(pid, mock_files, job_id)
        
        # Verify result
        assert result["files_count"] == 3
        assert len(result["items"]) == 3
        
        # Verify all files were processed
        raw_dir = project_ingest_raw_dir(pid)
        raw_files = list(raw_dir.glob("*"))
        assert len(raw_files) == 3
        
        parsed_dir = project_ingest_parsed_dir(pid)
        parsed_files = list(parsed_dir.glob("*.json"))
        assert len(parsed_files) == 3
