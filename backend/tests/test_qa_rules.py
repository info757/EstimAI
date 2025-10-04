"""
Unit tests for QA rules validation.
"""
import pytest
import tempfile
import json
from pathlib import Path
from backend.app.services.detectors.qa_rules import (
    load_qa_config, check_pipe_cover_requirements, check_deep_excavation,
    validate_network_qa, validate_pipe_qa, get_qa_summary, QAFlag
)


def test_load_qa_config_with_file():
    """Test loading QA config from file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "pipes"
        config_dir.mkdir()
        
        config_data = {
            "min_cover_ft": {
                "water": 3.0,
                "sewer": 2.5,
                "storm": 1.5
            }
        }
        
        with open(config_dir / "trench_defaults.json", 'w') as f:
            json.dump(config_data, f)
        
        config = load_qa_config(temp_dir)
        assert config["min_cover_ft"]["water"] == 3.0
        assert config["min_cover_ft"]["sewer"] == 2.5
        assert config["min_cover_ft"]["storm"] == 1.5


def test_load_qa_config_fallback():
    """Test loading QA config with fallback defaults."""
    config = load_qa_config("nonexistent_dir")
    assert config["min_cover_ft"]["water"] == 3.0
    assert config["min_cover_ft"]["sewer"] == 2.5
    assert config["min_cover_ft"]["storm"] == 1.5


def test_check_pipe_cover_requirements_sewer_low():
    """Test sewer cover requirement violation."""
    pipe = {
        "id": "sewer_pipe_1",
        "extra": {
            "min_depth_ft": 2.0  # Below 2.5ft requirement
        }
    }
    
    config = {"min_cover_ft": {"sewer": 2.5}}
    flags = check_pipe_cover_requirements(pipe, "sewer", config)
    
    assert len(flags) == 1
    assert flags[0].code == "SEWER_COVER_LOW"
    assert "2.0ft" in flags[0].message
    assert "2.5ft" in flags[0].message
    assert flags[0].geom_id == "sewer_pipe_1"


def test_check_pipe_cover_requirements_water_low():
    """Test water cover requirement violation."""
    pipe = {
        "id": "water_pipe_1",
        "extra": {
            "min_depth_ft": 2.5  # Below 3.0ft requirement
        }
    }
    
    config = {"min_cover_ft": {"water": 3.0}}
    flags = check_pipe_cover_requirements(pipe, "water", config)
    
    assert len(flags) == 1
    assert flags[0].code == "WATER_COVER_LOW"
    assert "2.5ft" in flags[0].message
    assert "3.0ft" in flags[0].message
    assert flags[0].geom_id == "water_pipe_1"


def test_check_pipe_cover_requirements_storm_low():
    """Test storm cover requirement violation."""
    pipe = {
        "id": "storm_pipe_1",
        "extra": {
            "min_depth_ft": 1.0  # Below 1.5ft requirement
        }
    }
    
    config = {"min_cover_ft": {"storm": 1.5}}
    flags = check_pipe_cover_requirements(pipe, "storm", config)
    
    assert len(flags) == 1
    assert flags[0].code == "STORM_COVER_LOW"
    assert "1.0ft" in flags[0].message
    assert "1.5ft" in flags[0].message
    assert flags[0].geom_id == "storm_pipe_1"


def test_check_pipe_cover_requirements_adequate():
    """Test pipe with adequate cover (no flags)."""
    pipe = {
        "id": "sewer_pipe_1",
        "extra": {
            "min_depth_ft": 3.0  # Above 2.5ft requirement
        }
    }
    
    config = {"min_cover_ft": {"sewer": 2.5}}
    flags = check_pipe_cover_requirements(pipe, "sewer", config)
    
    assert len(flags) == 0


def test_check_pipe_cover_requirements_no_extra():
    """Test pipe without extra field (no flags)."""
    pipe = {
        "id": "sewer_pipe_1"
    }
    
    config = {"min_cover_ft": {"sewer": 2.5}}
    flags = check_pipe_cover_requirements(pipe, "sewer", config)
    
    assert len(flags) == 0


def test_check_deep_excavation_triggered():
    """Test deep excavation flag when depth >= 12ft."""
    pipe = {
        "id": "deep_pipe_1",
        "extra": {
            "max_depth_ft": 12.5  # Triggers deep excavation
        }
    }
    
    flags = check_deep_excavation(pipe)
    
    assert len(flags) == 1
    assert flags[0].code == "DEEP_EXCAVATION"
    assert "12.5ft" in flags[0].message
    assert "12ft" in flags[0].message
    assert flags[0].geom_id == "deep_pipe_1"


def test_check_deep_excavation_not_triggered():
    """Test no deep excavation flag when depth < 12ft."""
    pipe = {
        "id": "shallow_pipe_1",
        "extra": {
            "max_depth_ft": 10.0  # Below 12ft threshold
        }
    }
    
    flags = check_deep_excavation(pipe)
    
    assert len(flags) == 0


def test_check_deep_excavation_exactly_12ft():
    """Test deep excavation flag when depth exactly 12ft."""
    pipe = {
        "id": "exact_pipe_1",
        "extra": {
            "max_depth_ft": 12.0  # Exactly at threshold
        }
    }
    
    flags = check_deep_excavation(pipe)
    
    assert len(flags) == 1
    assert flags[0].code == "DEEP_EXCAVATION"


def test_validate_network_qa():
    """Test network-level QA validation."""
    network_data = {
        "pipes": [
            {
                "id": "sewer_pipe_1",
                "extra": {
                    "min_depth_ft": 2.0,  # Below requirement
                    "max_depth_ft": 8.0
                }
            },
            {
                "id": "water_pipe_1", 
                "extra": {
                    "min_depth_ft": 3.5,  # Above requirement
                    "max_depth_ft": 12.5  # Deep excavation
                }
            }
        ]
    }
    
    flags = validate_network_qa(network_data, "sewer")
    
    # Should have 1 cover violation for sewer pipe
    assert len(flags) == 1
    assert flags[0].code == "SEWER_COVER_LOW"


def test_validate_pipe_qa_multiple_issues():
    """Test pipe with multiple QA issues."""
    pipe = {
        "id": "problem_pipe_1",
        "extra": {
            "min_depth_ft": 2.0,  # Below water requirement
            "max_depth_ft": 13.0  # Deep excavation
        }
    }
    
    flags = validate_pipe_qa(pipe, "water")
    
    # Should have both cover and excavation issues
    assert len(flags) == 2
    
    codes = [flag.code for flag in flags]
    assert "WATER_COVER_LOW" in codes
    assert "DEEP_EXCAVATION" in codes


def test_get_qa_summary():
    """Test QA summary generation."""
    flags = [
        QAFlag("SEWER_COVER_LOW", "Sewer pipe cover 2.0ft < required 2.5ft", "pipe1"),
        QAFlag("SEWER_COVER_LOW", "Sewer pipe cover 1.8ft < required 2.5ft", "pipe2"),
        QAFlag("DEEP_EXCAVATION", "Deep excavation 12.5ft >= 12ft", "pipe3"),
        QAFlag("WATER_COVER_LOW", "Water pipe cover 2.5ft < required 3.0ft", "pipe4")
    ]
    
    summary = get_qa_summary(flags)
    
    assert summary["SEWER_COVER_LOW"]["count"] == 2
    assert summary["DEEP_EXCAVATION"]["count"] == 1
    assert summary["WATER_COVER_LOW"]["count"] == 1
    
    # Check examples are limited to 3
    assert len(summary["SEWER_COVER_LOW"]["examples"]) == 2
    assert len(summary["DEEP_EXCAVATION"]["examples"]) == 1


def test_qa_flag_creation():
    """Test QAFlag dataclass creation."""
    flag = QAFlag(
        code="TEST_FLAG",
        message="Test message",
        geom_id="test_geom",
        sheet_ref="Sheet1"
    )
    
    assert flag.code == "TEST_FLAG"
    assert flag.message == "Test message"
    assert flag.geom_id == "test_geom"
    assert flag.sheet_ref == "Sheet1"


def test_qa_flag_optional_fields():
    """Test QAFlag with optional fields."""
    flag = QAFlag(
        code="TEST_FLAG",
        message="Test message"
    )
    
    assert flag.code == "TEST_FLAG"
    assert flag.message == "Test message"
    assert flag.geom_id is None
    assert flag.sheet_ref is None
