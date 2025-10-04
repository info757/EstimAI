"""
QA rules for construction takeoff validation.

This module provides functions to validate detected elements against
construction standards and generate QA flags for review.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class QAFlag:
    """QA flag for construction validation."""
    code: str
    message: str
    geom_id: Optional[str] = None
    sheet_ref: Optional[str] = None


def load_qa_config(base_dir: str = "config") -> Dict[str, Any]:
    """Load QA configuration from JSON files."""
    base_path = Path(base_dir)
    
    # Load trench defaults for cover requirements
    trench_file = base_path / "pipes" / "trench_defaults.json"
    if trench_file.exists():
        with open(trench_file, 'r') as f:
            return json.load(f)
    else:
        # Fallback defaults
        return {
            "min_cover_ft": {
                "water": 3.0,
                "sewer": 2.5,
                "storm": 1.5
            }
        }


def check_pipe_cover_requirements(pipe: Dict[str, Any], discipline: str, config: Dict[str, Any]) -> List[QAFlag]:
    """
    Check pipe cover requirements and generate QA flags.
    
    Args:
        pipe: Pipe object with extra field containing depth analysis
        discipline: Pipe discipline (water, sewer, storm)
        config: QA configuration with min_cover_ft requirements
        
    Returns:
        List of QAFlag objects for cover violations
    """
    flags = []
    
    if "extra" not in pipe or not pipe["extra"]:
        return flags
    
    extra = pipe["extra"]
    min_cover_ft = config.get("min_cover_ft", {}).get(discipline, 1.5)
    
    # Check minimum depth (cover to pipe crown)
    min_depth_ft = extra.get("min_depth_ft", 0.0)
    if min_depth_ft < min_cover_ft:
        if discipline == "sewer":
            flags.append(QAFlag(
                code="SEWER_COVER_LOW",
                message=f"Sewer pipe cover {min_depth_ft:.1f}ft < required {min_cover_ft}ft",
                geom_id=pipe.get("id")
            ))
        elif discipline == "water":
            flags.append(QAFlag(
                code="WATER_COVER_LOW", 
                message=f"Water pipe cover {min_depth_ft:.1f}ft < required {min_cover_ft}ft",
                geom_id=pipe.get("id")
            ))
        elif discipline == "storm":
            flags.append(QAFlag(
                code="STORM_COVER_LOW",
                message=f"Storm pipe cover {min_depth_ft:.1f}ft < required {min_cover_ft}ft", 
                geom_id=pipe.get("id")
            ))
    
    return flags


def check_deep_excavation(pipe: Dict[str, Any]) -> List[QAFlag]:
    """
    Check for deep excavation requirements and generate QA flags.
    
    Args:
        pipe: Pipe object with extra field containing depth analysis
        
    Returns:
        List of QAFlag objects for deep excavation
    """
    flags = []
    
    if "extra" not in pipe or not pipe["extra"]:
        return flags
    
    extra = pipe["extra"]
    max_depth_ft = extra.get("max_depth_ft", 0.0)
    
    # Check for deep excavation (>= 12ft requires special procedures)
    if max_depth_ft >= 12.0:
        flags.append(QAFlag(
            code="DEEP_EXCAVATION",
            message=f"Deep excavation {max_depth_ft:.1f}ft >= 12ft requires special procedures",
            geom_id=pipe.get("id")
        ))
    
    return flags


def validate_network_qa(network_data: Dict[str, Any], discipline: str, base_dir: str = "config") -> List[QAFlag]:
    """
    Validate entire network for QA issues.
    
    Args:
        network_data: Network data with pipes and nodes
        discipline: Network discipline (water, sewer, storm)
        base_dir: Base directory for configuration files
        
    Returns:
        List of QAFlag objects for all issues found
    """
    flags = []
    config = load_qa_config(base_dir)
    
    # Check each pipe for cover and excavation issues
    pipes = network_data.get("pipes", [])
    for pipe in pipes:
        # Check cover requirements
        cover_flags = check_pipe_cover_requirements(pipe, discipline, config)
        flags.extend(cover_flags)
        
        # Check deep excavation
        excavation_flags = check_deep_excavation(pipe)
        flags.extend(excavation_flags)
    
    return flags


def validate_pipe_qa(pipe: Dict[str, Any], discipline: str, base_dir: str = "config") -> List[QAFlag]:
    """
    Validate single pipe for QA issues.
    
    Args:
        pipe: Pipe object with extra field containing depth analysis
        discipline: Pipe discipline (water, sewer, storm)
        base_dir: Base directory for configuration files
        
    Returns:
        List of QAFlag objects for issues found
    """
    flags = []
    config = load_qa_config(base_dir)
    
    # Check cover requirements
    cover_flags = check_pipe_cover_requirements(pipe, discipline, config)
    flags.extend(cover_flags)
    
    # Check deep excavation
    excavation_flags = check_deep_excavation(pipe)
    flags.extend(excavation_flags)
    
    return flags


def get_qa_summary(flags: List[QAFlag]) -> Dict[str, Any]:
    """
    Generate summary of QA flags by code.
    
    Args:
        flags: List of QAFlag objects
        
    Returns:
        Summary dictionary with counts by flag code
    """
    summary = {}
    
    for flag in flags:
        code = flag.code
        if code not in summary:
            summary[code] = {
                "count": 0,
                "examples": []
            }
        
        summary[code]["count"] += 1
        if len(summary[code]["examples"]) < 3:  # Keep first 3 examples
            summary[code]["examples"].append(flag.message)
    
    return summary
