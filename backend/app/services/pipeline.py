"""
Pipeline helper functions for loading stage data.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..core.paths import project_dir, stage_dir

logger = logging.getLogger(__name__)


def latest_stage_rows(pid: str, stage: str) -> List[Dict[str, Any]]:
    """
    Load the latest rows for a stage, preferring reviewed version over base.
    
    Args:
        pid: Project ID
        stage: Stage name (takeoff, estimate, etc.)
        
    Returns:
        List of row dictionaries with stable IDs
    """
    proj_dir = project_dir(pid)
    stage_path = stage_dir(pid, stage)
    
    # First try to load reviewed version
    reviewed_path = stage_path / "reviewed.json"
    if reviewed_path.exists():
        try:
            with open(reviewed_path, 'r') as f:
                rows = json.load(f)
            logger.info(f"Loaded {len(rows)} rows from reviewed_{stage}.json")
            return _ensure_stable_ids(rows)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load reviewed_{stage}.json: {e}")
    
    # Fall back to latest base file
    base_files = list(stage_path.glob("*.json"))
    if not base_files:
        logger.warning(f"No files found for stage {stage} in project {pid}")
        return []
    
    # Get the most recent file by modification time
    latest_file = max(base_files, key=lambda p: p.stat().st_mtime)
    
    try:
        with open(latest_file, 'r') as f:
            data = json.load(f)
        
        # Extract rows based on stage structure
        rows = _extract_rows_from_stage_data(data, stage)
        logger.info(f"Loaded {len(rows)} rows from {latest_file.name}")
        return _ensure_stable_ids(rows)
        
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load {latest_file}: {e}")
        return []


def _extract_rows_from_stage_data(data: Dict[str, Any], stage: str) -> List[Dict[str, Any]]:
    """
    Extract rows from stage data based on the stage structure.
    
    Args:
        data: Stage data dictionary
        stage: Stage name
        
    Returns:
        List of row dictionaries
    """
    if stage == "takeoff":
        return data.get("items", [])
    elif stage == "estimate":
        return data.get("items", [])
    elif stage == "scope":
        # Scope has inclusions and exclusions
        inclusions = data.get("inclusions", [])
        exclusions = data.get("exclusions", [])
        # Combine with type indicators
        rows = []
        for item in inclusions:
            item["type"] = "inclusion"
            rows.append(item)
        for item in exclusions:
            item["type"] = "exclusion"
            rows.append(item)
        return rows
    elif stage == "risk":
        return data.get("risks", [])
    else:
        # Generic fallback - look for common keys
        for key in ["items", "rows", "data", "results"]:
            if key in data and isinstance(data[key], list):
                return data[key]
        return []


def _ensure_stable_ids(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ensure all rows have stable IDs for override tracking.
    
    Args:
        rows: List of row dictionaries
        
    Returns:
        List of rows with stable IDs
    """
    for i, row in enumerate(rows):
        if "id" not in row:
            # Generate stable ID based on content or index
            if "description" in row:
                # Use description hash as ID
                import hashlib
                desc_hash = hashlib.md5(str(row["description"]).encode()).hexdigest()[:8]
                row["id"] = f"row_{desc_hash}"
            else:
                # Fall back to index-based ID
                row["id"] = f"row_{i:03d}"
    
    return rows


def get_stage_summary(pid: str, stage: str) -> Dict[str, Any]:
    """
    Get a summary of stage data for review endpoints.
    
    Args:
        pid: Project ID
        stage: Stage name
        
    Returns:
        Summary dictionary with counts and metadata
    """
    rows = latest_stage_rows(pid, stage)
    
    summary = {
        "project_id": pid,
        "stage": stage,
        "total_rows": len(rows),
        "has_data": len(rows) > 0
    }
    
    # Add stage-specific metadata
    if stage == "takeoff" and rows:
        total_qty = sum(float(row.get("qty", 0)) for row in rows)
        summary["total_quantity"] = total_qty
        summary["units"] = list(set(row.get("unit", "") for row in rows if row.get("unit")))
    
    elif stage == "estimate" and rows:
        subtotal = sum(float(row.get("total", 0)) for row in rows)
        summary["subtotal"] = subtotal
        summary["item_count"] = len(rows)
    
    return summary
