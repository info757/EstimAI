"""
Quality assurance rules for construction takeoff validation.

This module provides functions to validate design standards and safety requirements
for detected infrastructure elements.
"""
from typing import List, Dict, Any, Optional
import json
from pathlib import Path


# Global QA config storage
_qa_config: Dict[str, Any] = {}


def init_qa_config(base_dir: str = "config") -> None:
    """Initialize QA configuration from JSON files."""
    global _qa_config
    
    base_path = Path(base_dir)
    qa_file = base_path / "qa" / "nc.json"
    
    if qa_file.exists():
        with open(qa_file, 'r') as f:
            _qa_config = json.load(f)
    else:
        # Fallback defaults
        _qa_config = {
            "min_cover_ft": {
                "sewer": 2.5,
                "water": 3.0,
                "storm": 1.5
            },
            "deep_excavation_threshold_ft": 12.0
        }


def validate_pipe_qa(pipe_dict: Dict[str, Any], discipline: str) -> List[Dict[str, Any]]:
    """
    Validate pipe for QA issues based on depth analysis.
    
    Args:
        pipe_dict: Pipe data with depth analysis in extra field
        discipline: Pipe discipline (storm, sanitary, water)
        
    Returns:
        List of QA flags for violations
    """
    if not _qa_config:
        init_qa_config()
    
    qa_flags = []
    extra = pipe_dict.get("extra", {})
    
    # Check minimum cover requirements
    min_depth_ft = extra.get("min_depth_ft")
    if min_depth_ft is not None:
        min_cover_ft = _qa_config.get("min_cover_ft", {}).get(discipline)
        if min_cover_ft and min_depth_ft < min_cover_ft:
            qa_flags.append({
                "code": f"{discipline.upper()}_COVER_LOW",
                "message": f"Minimum cover {min_depth_ft:.1f}ft < required {min_cover_ft}ft",
                "geom_id": pipe_dict.get("id"),
                "sheet_ref": None
            })
    
    # Check for deep excavation
    max_depth_ft = extra.get("max_depth_ft")
    if max_depth_ft is not None:
        deep_threshold = _qa_config.get("deep_excavation_threshold_ft", 12.0)
        if max_depth_ft >= deep_threshold:
            qa_flags.append({
                "code": "DEEP_EXCAVATION",
                "message": f"Maximum depth {max_depth_ft:.1f}ft >= OSHA threshold {deep_threshold}ft",
                "geom_id": pipe_dict.get("id"),
                "sheet_ref": None
            })
    
    return qa_flags


def validate_network_qa(network_data: Dict[str, Any], discipline: str) -> List[Dict[str, Any]]:
    """
    Validate entire network for QA issues.
    
    Args:
        network_data: Network data with pipes and structures
        discipline: Network discipline (storm, sanitary, water)
        
    Returns:
        List of QA flags for violations
    """
    qa_flags = []
    
    # Validate each pipe
    pipes = network_data.get("pipes", [])
    for pipe in pipes:
        pipe_qa = validate_pipe_qa(pipe, discipline)
        qa_flags.extend(pipe_qa)
    
    return qa_flags
