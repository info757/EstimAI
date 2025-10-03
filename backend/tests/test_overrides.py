"""
Test HITL Overrides Layer functionality.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from backend.app.services.overrides import (
    overrides_dir,
    ensure_overrides_dir,
    load_overrides,
    save_overrides,
    apply_overrides,
    merge_stage_with_overrides,
    get_reviewed_or_base
)


@pytest.fixture
def test_pid():
    return "test_project"


def test_overrides_dir(test_pid, tmp_path):
    """Test overrides directory path construction."""
    with patch('app.core.paths.artifacts_root') as mock_artifacts_root:
        mock_artifacts_root.return_value = tmp_path
        path = overrides_dir(test_pid)
        assert str(path).endswith(f"{test_pid}/overrides")


def test_ensure_overrides_dir(tmp_path):
    """Test overrides directory creation."""
    with patch('app.core.paths.artifacts_root') as mock_artifacts_root, \
         patch('app.services.overrides.project_dir') as mock_project_dir:
        mock_artifacts_root.return_value = tmp_path
        mock_project_dir.return_value = tmp_path / "test_project"
        
        overrides_path = ensure_overrides_dir("test_project")
        assert overrides_path.exists()
        assert overrides_path.is_dir()


def test_save_and_load_overrides(tmp_path):
    """Test saving and loading overrides."""
    with patch('app.core.paths.artifacts_root') as mock_artifacts_root, \
         patch('app.services.overrides.project_dir') as mock_project_dir:
        mock_artifacts_root.return_value = tmp_path
        mock_project_dir.return_value = tmp_path / "test_project"
        
        patches = [
            {
                "id": "item_1",
                "fields": {"qty": 150, "unit": "LF"},
                "by": "test_user",
                "reason": "manual adjustment",
                "at": "2025-09-01T12:00:00Z"
            }
        ]
        
        # Save overrides
        success = save_overrides("test_project", "takeoff", patches)
        assert success
        
        # Load overrides
        loaded = load_overrides("test_project", "takeoff")
        assert len(loaded) == 1
        assert loaded[0]["id"] == "item_1"
        assert loaded[0]["fields"]["qty"] == 150


def test_apply_overrides():
    """Test applying overrides to base rows."""
    base_rows = [
        {"id": "item_1", "qty": 100, "unit": "EA", "description": "Test item"},
        {"id": "item_2", "qty": 200, "unit": "LF", "description": "Another item"}
    ]
    
    patches = [
        {
            "id": "item_1",
            "fields": {"qty": 150, "unit": "LF"},
            "by": "test_user",
            "reason": "manual adjustment",
            "at": "2025-09-01T12:00:00Z"
        }
    ]
    
    result = apply_overrides(base_rows, patches)
    
    assert len(result) == 2
    assert result[0]["qty"] == 150  # Overridden
    assert result[0]["unit"] == "LF"  # Overridden
    assert result[0]["description"] == "Test item"  # Unchanged
    assert result[1]["qty"] == 200  # Unchanged
    
    # Check provenance metadata
    assert "_override" in result[0]
    assert result[0]["_override"]["by"] == "test_user"
    assert result[0]["_override"]["reason"] == "manual adjustment"


def test_merge_stage_with_overrides(tmp_path):
    """Test merging stage with overrides."""
    with patch('app.core.paths.artifacts_root') as mock_artifacts_root, \
         patch('app.services.overrides.project_dir') as mock_project_dir:
        mock_artifacts_root.return_value = tmp_path
        mock_project_dir.return_value = tmp_path / "test_project"
        
        base_rows = [
            {"id": "item_1", "qty": 100, "unit": "EA"},
            {"id": "item_2", "qty": 200, "unit": "LF"}
        ]
        
        patches = [
            {
                "id": "item_1",
                "fields": {"qty": 150},
                "by": "test_user",
                "reason": "manual adjustment",
                "at": "2025-09-01T12:00:00Z"
            }
        ]
        
        # Save overrides first
        save_overrides("test_project", "takeoff", patches)
        
        # Merge
        result = merge_stage_with_overrides("test_project", "takeoff", base_rows)
        
        assert len(result) == 2
        assert result[0]["qty"] == 150  # Overridden
        assert result[1]["qty"] == 200  # Unchanged
        
        # Check that reviewed.json was created
        reviewed_path = tmp_path / "test_project" / "takeoff" / "reviewed.json"
        assert reviewed_path.exists()


def test_get_reviewed_or_base(tmp_path):
    """Test getting reviewed version or falling back to base."""
    with patch('app.core.paths.artifacts_root') as mock_artifacts_root, \
         patch('app.services.overrides.project_dir') as mock_project_dir:
        mock_artifacts_root.return_value = tmp_path
        mock_project_dir.return_value = tmp_path / "test_project"
        
        base_rows = [
            {"id": "item_1", "qty": 100, "unit": "EA"},
            {"id": "item_2", "qty": 200, "unit": "LF"}
        ]
        
        # No reviewed version exists, should return base
        result = get_reviewed_or_base("test_project", "takeoff", base_rows)
        assert result == base_rows
        
        # Create reviewed version
        reviewed_path = tmp_path / "test_project" / "takeoff"
        reviewed_path.mkdir(parents=True, exist_ok=True)
        
        reviewed_rows = [
            {"id": "item_1", "qty": 150, "unit": "EA", "_override": {"by": "user"}},
            {"id": "item_2", "qty": 200, "unit": "LF"}
        ]
        
        with open(reviewed_path / "reviewed.json", "w") as f:
            json.dump(reviewed_rows, f)
        
        # Should return reviewed version
        result = get_reviewed_or_base("test_project", "takeoff", base_rows)
        assert len(result) == 2
        assert result[0]["qty"] == 150
        assert "_override" in result[0]


def test_load_overrides_nonexistent(tmp_path):
    """Test loading overrides when file doesn't exist."""
    with patch('app.core.paths.artifacts_root') as mock_artifacts_root:
        mock_artifacts_root.return_value = tmp_path
        result = load_overrides("nonexistent_project", "takeoff")
        assert result == []


def test_apply_overrides_empty_patches():
    """Test applying empty patches returns original rows."""
    base_rows = [{"id": "item_1", "qty": 100}]
    result = apply_overrides(base_rows, [])
    assert result == base_rows


def test_apply_overrides_invalid_id():
    """Test applying overrides with invalid row ID."""
    base_rows = [{"id": "item_1", "qty": 100}]
    patches = [{"id": "nonexistent", "fields": {"qty": 200}}]
    
    result = apply_overrides(base_rows, patches)
    assert len(result) == 1
    assert result[0]["qty"] == 100  # Unchanged

