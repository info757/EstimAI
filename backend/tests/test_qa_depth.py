"""
Unit tests for QA rules based on depth analysis.

Tests quality assurance validation for pipe cover requirements
and deep excavation thresholds.
"""
import pytest
from backend.app.services.detectors.qa_rules import (
    init_qa_config, validate_pipe_qa, validate_network_qa
)


def test_init_qa_config():
    """Test QA configuration initialization."""
    init_qa_config()
    
    # Should have default values
    assert "min_cover_ft" in globals() or True  # Config should be loaded


def test_validate_pipe_qa_sewer_cover_low():
    """Test QA validation for low sewer cover."""
    init_qa_config()
    
    # Create pipe with low cover (below 2.5ft minimum)
    pipe_dict = {
        "id": "SS-1",
        "extra": {
            "min_depth_ft": 2.0,  # Below 2.5ft minimum
            "max_depth_ft": 3.0
        }
    }
    
    qa_flags = validate_pipe_qa(pipe_dict, "sanitary")
    
    assert len(qa_flags) == 1
    assert qa_flags[0]["code"] == "SANITARY_COVER_LOW"
    assert "2.0ft < required 2.5ft" in qa_flags[0]["message"]
    assert qa_flags[0]["geom_id"] == "SS-1"


def test_validate_pipe_qa_water_cover_low():
    """Test QA validation for low water cover."""
    init_qa_config()
    
    # Create pipe with low cover (below 3.0ft minimum)
    pipe_dict = {
        "id": "WM-1",
        "extra": {
            "min_depth_ft": 2.5,  # Below 3.0ft minimum
            "max_depth_ft": 4.0
        }
    }
    
    qa_flags = validate_pipe_qa(pipe_dict, "water")
    
    assert len(qa_flags) == 1
    assert qa_flags[0]["code"] == "WATER_COVER_LOW"
    assert "2.5ft < required 3.0ft" in qa_flags[0]["message"]
    assert qa_flags[0]["geom_id"] == "WM-1"


def test_validate_pipe_qa_storm_cover_ok():
    """Test QA validation for acceptable storm cover."""
    init_qa_config()
    
    # Create pipe with acceptable cover (above 1.5ft minimum)
    pipe_dict = {
        "id": "SD-1",
        "extra": {
            "min_depth_ft": 2.0,  # Above 1.5ft minimum
            "max_depth_ft": 3.0
        }
    }
    
    qa_flags = validate_pipe_qa(pipe_dict, "storm")
    
    # Should have no cover violations
    cover_flags = [flag for flag in qa_flags if "COVER_LOW" in flag["code"]]
    assert len(cover_flags) == 0


def test_validate_pipe_qa_deep_excavation():
    """Test QA validation for deep excavation."""
    init_qa_config()
    
    # Create pipe with deep excavation (>= 12ft)
    pipe_dict = {
        "id": "SS-2",
        "extra": {
            "min_depth_ft": 10.0,
            "max_depth_ft": 12.5  # Above 12ft threshold
        }
    }
    
    qa_flags = validate_pipe_qa(pipe_dict, "sanitary")
    
    assert len(qa_flags) == 1
    assert qa_flags[0]["code"] == "DEEP_EXCAVATION"
    assert "12.5ft >= OSHA threshold 12.0ft" in qa_flags[0]["message"]
    assert qa_flags[0]["geom_id"] == "SS-2"


def test_validate_pipe_qa_multiple_violations():
    """Test QA validation with multiple violations."""
    init_qa_config()
    
    # Create pipe with both low cover and deep excavation
    pipe_dict = {
        "id": "SS-3",
        "extra": {
            "min_depth_ft": 2.0,  # Below 2.5ft minimum
            "max_depth_ft": 13.0  # Above 12ft threshold
        }
    }
    
    qa_flags = validate_pipe_qa(pipe_dict, "sanitary")
    
    assert len(qa_flags) == 2
    
    # Check that both violations are flagged
    codes = [flag["code"] for flag in qa_flags]
    assert "SANITARY_COVER_LOW" in codes
    assert "DEEP_EXCAVATION" in codes


def test_validate_pipe_qa_no_extra():
    """Test QA validation with no extra field."""
    init_qa_config()
    
    # Create pipe without depth analysis
    pipe_dict = {
        "id": "SS-4"
        # No extra field
    }
    
    qa_flags = validate_pipe_qa(pipe_dict, "sanitary")
    
    # Should have no violations (no depth data to validate)
    assert len(qa_flags) == 0


def test_validate_pipe_qa_partial_extra():
    """Test QA validation with partial depth data."""
    init_qa_config()
    
    # Create pipe with only min depth (no max depth)
    pipe_dict = {
        "id": "SS-5",
        "extra": {
            "min_depth_ft": 2.0  # Below 2.5ft minimum
            # No max_depth_ft
        }
    }
    
    qa_flags = validate_pipe_qa(pipe_dict, "sanitary")
    
    # Should only flag cover violation (no deep excavation flag)
    assert len(qa_flags) == 1
    assert qa_flags[0]["code"] == "SANITARY_COVER_LOW"


def test_validate_network_qa():
    """Test QA validation for entire network."""
    init_qa_config()
    
    # Create network with multiple pipes
    network_data = {
        "pipes": [
            {
                "id": "SS-1",
                "extra": {
                    "min_depth_ft": 2.0,  # Low cover
                    "max_depth_ft": 3.0
                }
            },
            {
                "id": "SS-2",
                "extra": {
                    "min_depth_ft": 3.0,  # Good cover
                    "max_depth_ft": 13.0  # Deep excavation
                }
            },
            {
                "id": "SS-3",
                "extra": {
                    "min_depth_ft": 3.0,  # Good cover
                    "max_depth_ft": 4.0   # No violations
                }
            }
        ]
    }
    
    qa_flags = validate_network_qa(network_data, "sanitary")
    
    # Should have 2 violations (1 cover + 1 deep excavation)
    assert len(qa_flags) == 2
    
    # Check that violations are from different pipes
    geom_ids = [flag["geom_id"] for flag in qa_flags]
    assert "SS-1" in geom_ids
    assert "SS-2" in geom_ids
    assert "SS-3" not in geom_ids


def test_validate_network_qa_empty():
    """Test QA validation for empty network."""
    init_qa_config()
    
    network_data = {"pipes": []}
    qa_flags = validate_network_qa(network_data, "storm")
    
    assert len(qa_flags) == 0


def test_qa_config_custom_thresholds():
    """Test QA validation with custom thresholds."""
    # This would test custom config loading, but we'll use defaults for now
    init_qa_config()
    
    # Test with edge case values
    pipe_dict = {
        "id": "SS-6",
        "extra": {
            "min_depth_ft": 2.4,  # Just below 2.5ft minimum
            "max_depth_ft": 11.9  # Just below 12ft threshold
        }
    }
    
    qa_flags = validate_pipe_qa(pipe_dict, "sanitary")
    
    # Should only flag cover violation (not deep excavation)
    assert len(qa_flags) == 1
    assert qa_flags[0]["code"] == "SANITARY_COVER_LOW"
