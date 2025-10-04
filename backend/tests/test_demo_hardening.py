"""
Unit tests for demo hardening and stability features.

Tests database migrations, security middleware, demo mode, and error handling.
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.app.db.migrations import DatabaseMigrator, get_migrator
from backend.app.middleware.security import SecurityMiddleware, RateLimiter, StructuredErrorHandler
from backend.app.core.demo_config import DemoModeManager, SampleFileManager, get_demo_manager
from backend.app.main import app


class TestDatabaseMigrator:
    """Test cases for database migrations."""
    
    def setup_method(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.database_url = f"sqlite:///{self.temp_db.name}"
        self.migrator = DatabaseMigrator(self.database_url)
    
    def teardown_method(self):
        """Clean up test database."""
        Path(self.temp_db.name).unlink(missing_ok=True)
    
    def test_migrator_initialization(self):
        """Test migrator initialization."""
        assert self.migrator.database_url == self.database_url
        assert self.migrator.engine is not None
        assert self.migrator.Session is not None
        assert self.migrator.migrations_dir.exists()
    
    def test_create_indices(self):
        """Test index creation."""
        # Create a simple table first
        with self.migrator.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS countitem (
                    id INTEGER PRIMARY KEY,
                    file TEXT,
                    page INTEGER,
                    type TEXT,
                    status TEXT,
                    confidence REAL
                )
            """))
            conn.commit()
        
        # Create indices
        self.migrator.create_indices()
        
        # Verify indices were created
        with self.migrator.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name LIKE 'idx_%'
            """)).fetchall()
            
            index_names = [row[0] for row in result]
            assert "idx_countitem_file_page" in index_names
            assert "idx_countitem_type" in index_names
            assert "idx_countitem_status" in index_names
    
    def test_optimize_database(self):
        """Test database optimization."""
        # Create a simple table
        with self.migrator.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS test_table (
                    id INTEGER PRIMARY KEY,
                    data TEXT
                )
            """))
            conn.commit()
        
        # Run optimization
        self.migrator.optimize_database()
        
        # Verify pragmas were set
        with self.migrator.engine.connect() as conn:
            result = conn.execute(text("PRAGMA journal_mode")).fetchone()
            assert result[0] == "wal"
    
    def test_create_sample_data(self):
        """Test sample data creation."""
        # Create tables first
        with self.migrator.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS countitem (
                    id INTEGER PRIMARY KEY,
                    file TEXT,
                    page INTEGER,
                    type TEXT,
                    confidence REAL,
                    x_pdf REAL,
                    y_pdf REAL,
                    points_per_foot REAL,
                    status TEXT,
                    name TEXT,
                    subtype TEXT,
                    quantity REAL,
                    unit TEXT,
                    attributes TEXT
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS reviewsession (
                    id TEXT PRIMARY KEY,
                    file TEXT,
                    pages TEXT,
                    points_per_foot REAL,
                    metrics TEXT
                )
            """))
            conn.commit()
        
        # Create sample data
        self.migrator.create_sample_data()
        
        # Verify sample data was created
        with self.migrator.engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM countitem")).fetchone()
            assert result[0] > 0
            
            result = conn.execute(text("SELECT COUNT(*) FROM reviewsession")).fetchone()
            assert result[0] > 0


class TestSecurityMiddleware:
    """Test cases for security middleware."""
    
    def test_security_middleware_initialization(self):
        """Test security middleware initialization."""
        middleware = SecurityMiddleware(app=None, max_request_size=1024)
        assert middleware.max_request_size == 1024
        assert middleware.rate_limiter is not None
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        rate_limiter = RateLimiter()
        assert rate_limiter.limiter is not None
        assert len(rate_limiter.endpoint_limits) > 0
    
    def test_get_limits_for_path(self):
        """Test getting limits for specific paths."""
        rate_limiter = RateLimiter()
        
        # Test specific endpoint limits
        detect_limits = rate_limiter.get_limits_for_path("/v1/detect")
        assert detect_limits == ["10/minute", "100/hour"]
        
        # Test default limits
        unknown_limits = rate_limiter.get_limits_for_path("/v1/unknown")
        assert unknown_limits == rate_limiter.limiter.default_limits


class TestStructuredErrorHandler:
    """Test cases for structured error handling."""
    
    def test_create_error_response(self):
        """Test creating structured error responses."""
        error_response = StructuredErrorHandler.create_error_response(
            "TEST_ERROR",
            "Test error message",
            400,
            {"test": "data"}
        )
        
        assert error_response.status_code == 400
        content = error_response.body.decode()
        assert "TEST_ERROR" in content
        assert "Test error message" in content
        assert "test" in content
    
    def test_handle_validation_error(self):
        """Test handling validation errors."""
        error_response = StructuredErrorHandler.handle_validation_error(
            Exception("Validation failed")
        )
        
        assert error_response.status_code == 422
        content = error_response.body.decode()
        assert "VALIDATION_ERROR" in content
    
    def test_handle_database_error(self):
        """Test handling database errors."""
        error_response = StructuredErrorHandler.handle_database_error(
            Exception("Database connection failed")
        )
        
        assert error_response.status_code == 500
        content = error_response.body.decode()
        assert "DATABASE_ERROR" in content


class TestDemoModeManager:
    """Test cases for demo mode management."""
    
    def setup_method(self):
        """Set up test demo manager."""
        self.temp_dir = tempfile.mkdtemp()
        self.demo_manager = DemoModeManager()
    
    def test_demo_manager_initialization(self):
        """Test demo manager initialization."""
        assert self.demo_manager.config is not None
        assert self.demo_manager.sample_file_manager is not None
        assert isinstance(self.demo_manager.active_sessions, dict)
    
    def test_is_demo_mode(self):
        """Test demo mode detection."""
        # Demo mode should be False by default in tests
        assert isinstance(self.demo_manager.is_demo_mode(), bool)
    
    def test_get_demo_limits(self):
        """Test getting demo limits."""
        limits = self.demo_manager.get_demo_limits()
        
        assert "max_file_size" in limits
        assert "max_requests_per_minute" in limits
        assert "max_requests_per_hour" in limits
        assert "max_demo_sessions" in limits
        
        assert limits["max_file_size"] > 0
        assert limits["max_requests_per_minute"] > 0
        assert limits["max_requests_per_hour"] > 0
    
    def test_get_demo_banner(self):
        """Test getting demo banner information."""
        banner = self.demo_manager.get_demo_banner()
        
        assert "enabled" in banner
        assert "message" in banner
        assert "limits" in banner
        assert "sample_files" in banner
        
        assert isinstance(banner["enabled"], bool)
        assert isinstance(banner["message"], str)
        assert isinstance(banner["limits"], dict)
        assert isinstance(banner["sample_files"], list)
    
    def test_register_demo_session(self):
        """Test demo session registration."""
        session_id = "test_session_123"
        user_info = {"user": "test_user"}
        
        self.demo_manager.register_demo_session(session_id, user_info)
        
        assert session_id in self.demo_manager.active_sessions
        session = self.demo_manager.active_sessions[session_id]
        assert session["user_info"] == user_info
        assert "created_at" in session
        assert session["requests_count"] == 0
    
    def test_check_demo_limits(self):
        """Test demo limits checking."""
        session_id = "test_session_456"
        self.demo_manager.register_demo_session(session_id)
        
        # Check limits for new session
        limits_check = self.demo_manager.check_demo_limits(session_id)
        assert limits_check["allowed"] is True
        
        # Simulate exceeding limits
        self.demo_manager.active_sessions[session_id]["requests_count"] = 1000
        
        limits_check = self.demo_manager.check_demo_limits(session_id)
        assert limits_check["allowed"] is False
        assert "exceeded" in limits_check["reason"].lower()
    
    def test_record_demo_request(self):
        """Test recording demo requests."""
        session_id = "test_session_789"
        self.demo_manager.register_demo_session(session_id)
        
        initial_count = self.demo_manager.active_sessions[session_id]["requests_count"]
        
        self.demo_manager.record_demo_request(session_id)
        
        new_count = self.demo_manager.active_sessions[session_id]["requests_count"]
        assert new_count == initial_count + 1
        assert self.demo_manager.active_sessions[session_id]["last_request"] is not None


class TestSampleFileManager:
    """Test cases for sample file management."""
    
    def setup_method(self):
        """Set up test sample file manager."""
        self.temp_dir = tempfile.mkdtemp()
        self.sample_manager = SampleFileManager(str(self.temp_dir))
    
    def test_sample_file_manager_initialization(self):
        """Test sample file manager initialization."""
        assert self.sample_manager.sample_dir.exists()
        assert len(self.sample_manager.sample_files) > 0
    
    def test_get_sample_files(self):
        """Test getting sample files."""
        sample_files = self.sample_manager.get_sample_files()
        
        assert isinstance(sample_files, dict)
        assert len(sample_files) > 0
        
        # Check sample file structure
        for filename, file_info in sample_files.items():
            assert "path" in file_info
            assert "info" in file_info
            assert "description" in file_info["info"]
            assert "size" in file_info["info"]
            assert "features" in file_info["info"]
    
    def test_get_sample_file_path(self):
        """Test getting sample file path."""
        sample_files = self.sample_manager.get_sample_files()
        first_filename = list(sample_files.keys())[0]
        
        file_path = self.sample_manager.get_sample_file_path(first_filename)
        assert file_path is not None
        assert Path(file_path).exists()
        
        # Test non-existent file
        non_existent_path = self.sample_manager.get_sample_file_path("non_existent.pdf")
        assert non_existent_path is None
    
    def test_cleanup_old_files(self):
        """Test cleanup of old files."""
        # Create a test file
        test_file = self.sample_manager.sample_dir / "test_old_file.txt"
        test_file.write_text("test content")
        
        # Modify file timestamp to make it old
        import time
        old_time = time.time() - (25 * 3600)  # 25 hours ago
        test_file.touch()
        os.utime(test_file, (old_time, old_time))
        
        # Run cleanup
        self.sample_manager.cleanup_old_files(max_age_hours=24)
        
        # File should be deleted
        assert not test_file.exists()


class TestDemoAPI:
    """Test cases for demo API endpoints."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_demo_banner_endpoint(self):
        """Test demo banner endpoint."""
        response = self.client.get("/v1/demo/banner")
        
        # Should return 200 even if demo mode is disabled
        assert response.status_code in [200, 401]  # 401 if auth required
    
    def test_sample_files_endpoint(self):
        """Test sample files endpoint."""
        response = self.client.get("/v1/demo/sample-files")
        
        # Should return 200 even if demo mode is disabled
        assert response.status_code in [200, 401]  # 401 if auth required
    
    def test_demo_limits_endpoint(self):
        """Test demo limits endpoint."""
        response = self.client.get("/v1/demo/limits")
        
        # Should return 200 even if demo mode is disabled
        assert response.status_code in [200, 401]  # 401 if auth required
    
    def test_demo_health_endpoint(self):
        """Test demo health endpoint."""
        response = self.client.get("/v1/demo/health")
        
        # Health endpoint should always return 200
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "demo_mode" in data
        assert "active_sessions" in data
        assert "sample_files_count" in data


class TestIntegration:
    """Integration tests for demo hardening features."""
    
    def test_full_demo_workflow(self):
        """Test complete demo workflow."""
        # Initialize demo manager
        demo_manager = DemoModeManager()
        
        # Register demo session
        session_id = "integration_test_session"
        demo_manager.register_demo_session(session_id, {"test": "user"})
        
        # Check initial limits
        limits_check = demo_manager.check_demo_limits(session_id)
        assert limits_check["allowed"] is True
        
        # Record some requests
        for _ in range(5):
            demo_manager.record_demo_request(session_id)
        
        # Check session status
        session = demo_manager.active_sessions[session_id]
        assert session["requests_count"] == 5
        assert session["last_request"] is not None
        
        # Get demo banner info
        banner = demo_manager.get_demo_banner()
        assert banner["enabled"] == demo_manager.is_demo_mode()
        assert len(banner["sample_files"]) > 0
        
        # Get sample files
        sample_files = demo_manager.get_sample_files()
        assert len(sample_files) > 0
        
        # Test error handling
        error_handler = StructuredErrorHandler()
        error_response = error_handler.create_error_response(
            "INTEGRATION_TEST_ERROR",
            "Integration test error",
            400
        )
        
        assert error_response.status_code == 400
        content = error_response.body.decode()
        assert "INTEGRATION_TEST_ERROR" in content
    
    def test_database_migration_workflow(self):
        """Test complete database migration workflow."""
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        temp_db.close()
        database_url = f"sqlite:///{temp_db.name}"
        
        try:
            # Initialize migrator
            migrator = DatabaseMigrator(database_url)
            
            # Create basic tables
            with migrator.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS countitem (
                        id INTEGER PRIMARY KEY,
                        file TEXT,
                        page INTEGER,
                        type TEXT,
                        status TEXT,
                        confidence REAL
                    )
                """))
                conn.commit()
            
            # Run migrations
            migrator.create_indices()
            migrator.optimize_database()
            
            # Verify indices were created
            with migrator.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name LIKE 'idx_%'
                """)).fetchall()
                
                assert len(result) > 0
                index_names = [row[0] for row in result]
                assert "idx_countitem_file_page" in index_names
            
            # Test sample data creation
            migrator.create_sample_data()
            
            # Verify sample data
            with migrator.engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM countitem")).fetchone()
                assert result[0] > 0
        
        finally:
            # Clean up
            Path(temp_db.name).unlink(missing_ok=True)
