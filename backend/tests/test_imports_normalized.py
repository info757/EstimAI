"""
Test that imports are properly normalized and work correctly.

This test ensures that:
1. backend.vpdf imports work
2. backend.app.core.config imports work
3. No import errors occur
"""
import pytest


def test_backend_vpdf_imports():
    """Test that backend.vpdf imports work."""
    try:
        import backend.vpdf
        assert backend.vpdf is not None
    except ImportError as e:
        pytest.fail(f"Failed to import backend.vpdf: {e}")


def test_backend_app_core_config_imports():
    """Test that backend.app.core.config imports work."""
    try:
        from backend.app.core.config import settings
        assert settings is not None
        # Basic validation that settings has expected attributes
        assert hasattr(settings, 'DATABASE_URL')
        assert hasattr(settings, 'PROJECT_NAME')
    except ImportError as e:
        pytest.fail(f"Failed to import backend.app.core.config: {e}")


def test_backend_app_main_imports():
    """Test that backend.app.main imports work."""
    try:
        from backend.app.main import app
        assert app is not None
    except ImportError as e:
        pytest.fail(f"Failed to import backend.app.main: {e}")


def test_no_disallowed_imports():
    """Test that no files contain disallowed import patterns."""
    import subprocess
    import sys
    from pathlib import Path
    
    # Run the check_imports script
    script_path = Path(__file__).parent.parent.parent / "scripts" / "check_imports.sh"
    
    try:
        result = subprocess.run(
            [str(script_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        
        if result.returncode != 0:
            pytest.fail(f"Import check failed:\n{result.stdout}\n{result.stderr}")
        
        # If we get here, the check passed
        assert "✅ Imports look good." in result.stdout
        
    except FileNotFoundError:
        pytest.fail("check_imports.sh script not found")
    except Exception as e:
        pytest.fail(f"Failed to run import check: {e}")


def test_import_normalization_script():
    """Test that the import normalization script works."""
    import subprocess
    import sys
    from pathlib import Path
    
    script_path = Path(__file__).parent.parent.parent / "scripts" / "fix_imports.py"
    
    try:
        # Test dry-run mode
        result = subprocess.run(
            [sys.executable, str(script_path), "--dry-run"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        
        # Should not fail even if no changes needed
        assert result.returncode == 0
        
    except FileNotFoundError:
        pytest.fail("fix_imports.py script not found")
    except Exception as e:
        pytest.fail(f"Failed to run import normalization script: {e}")
