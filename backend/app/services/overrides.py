"""
HITL Overrides Layer

Manages human edits to pipeline outputs via JSON patch files.
Overrides live under artifacts/{pid}/overrides/ and are merged into pipeline results.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.paths import project_dir

logger = logging.getLogger(__name__)


def overrides_dir(pid: str) -> Path:
    """Get the overrides directory for a project."""
    return project_dir(pid) / "overrides"


def ensure_overrides_dir(pid: str) -> Path:
    """Ensure overrides directory exists and return path."""
    overrides_path = overrides_dir(pid)
    overrides_path.mkdir(parents=True, exist_ok=True)
    return overrides_path


def load_overrides(pid: str, stage: str) -> List[Dict[str, Any]]:
    """
    Load overrides for a specific stage.
    
    Args:
        pid: Project ID
        stage: Stage name (takeoff, estimate, risk, etc.)
        
    Returns:
        List of patch objects, or empty list if no overrides exist
    """
    overrides_path = overrides_dir(pid) / f"overrides_{stage}.json"
    
    if not overrides_path.exists():
        return []
    
    try:
        with open(overrides_path, 'r') as f:
            patches = json.load(f)
        logger.info(f"Loaded {len(patches)} overrides for stage {stage}")
        return patches
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load overrides for {stage}: {e}")
        return []


def save_overrides(pid: str, stage: str, patches: List[Dict[str, Any]]) -> bool:
    """
    Save overrides for a specific stage.
    
    Args:
        pid: Project ID
        stage: Stage name
        patches: List of patch objects
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        ensure_overrides_dir(pid)
        overrides_path = overrides_dir(pid) / f"overrides_{stage}.json"
        
        with open(overrides_path, 'w') as f:
            json.dump(patches, f, indent=2, default=str)
        
        logger.info(f"Saved {len(patches)} overrides for stage {stage}")
        return True
    except IOError as e:
        logger.error(f"Failed to save overrides for {stage}: {e}")
        return False


def apply_overrides(base_rows: List[Dict[str, Any]], patches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Apply overrides to base rows.
    
    Args:
        base_rows: Original rows from pipeline stage
        patches: List of patch objects with id, fields, by, reason, at
        
    Returns:
        Merged rows with overrides applied
    """
    if not patches:
        return base_rows
    
    # Create lookup for base rows by id
    base_lookup = {row.get('id', str(i)): row.copy() for i, row in enumerate(base_rows)}
    
    # Apply patches (last write wins for same field)
    patched_count = 0
    for patch in patches:
        row_id = patch.get('id')
        if not row_id or row_id not in base_lookup:
            logger.warning(f"Patch references non-existent row id: {row_id}")
            continue
        
        # Apply field updates
        fields = patch.get('fields', {})
        for field, value in fields.items():
            base_lookup[row_id][field] = value
        
        # Add provenance metadata
        base_lookup[row_id]['_override'] = {
            'by': patch.get('by', 'unknown'),
            'reason': patch.get('reason', 'manual adjustment'),
            'at': patch.get('at', datetime.now().isoformat())
        }
        patched_count += 1
    
    result = list(base_lookup.values())
    logger.info(f"Applied overrides: {patched_count} rows patched")
    return result


def merge_stage_with_overrides(pid: str, stage: str, base_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Load overrides for a stage and merge with base rows.
    
    Args:
        pid: Project ID
        stage: Stage name
        base_rows: Original rows from pipeline stage
        
    Returns:
        Merged rows with overrides applied
    """
    patches = load_overrides(pid, stage)
    if not patches:
        return base_rows
    
    merged_rows = apply_overrides(base_rows, patches)
    
    # Save reviewed version
    reviewed_path = project_dir(pid) / stage / "reviewed.json"
    reviewed_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(reviewed_path, 'w') as f:
            json.dump(merged_rows, f, indent=2, default=str)
        logger.info(f"Saved reviewed_{stage}.json with {len(patches)} overrides applied")
    except IOError as e:
        logger.error(f"Failed to save reviewed_{stage}.json: {e}")
    
    return merged_rows


def get_reviewed_or_base(pid: str, stage: str, base_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Get reviewed version if it exists, otherwise return base rows.
    
    Args:
        pid: Project ID
        stage: Stage name
        base_rows: Original rows from pipeline stage
        
    Returns:
        Reviewed rows if available, otherwise base rows
    """
    reviewed_path = project_dir(pid) / stage / "reviewed.json"
    
    if reviewed_path.exists():
        try:
            with open(reviewed_path, 'r') as f:
                reviewed_rows = json.load(f)
            logger.info(f"Using reviewed_{stage}.json with overrides")
            return reviewed_rows
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load reviewed_{stage}.json: {e}")
    
    return base_rows
