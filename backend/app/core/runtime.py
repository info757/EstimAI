"""
Runtime information and monitoring utilities.

This module provides functions to track application uptime and version information.
"""
import os
import time
from typing import Optional

# Record start time when module is imported
START_TIME = time.monotonic()


def uptime_seconds() -> float:
    """
    Get the application uptime in seconds.
    
    Returns:
        float: Uptime in seconds since application start
    """
    return time.monotonic() - START_TIME


def app_version() -> str:
    """
    Get the application version from environment or fallback to 'dev'.
    
    Returns:
        str: Version string (COMMIT_SHA or 'dev')
    """
    return os.getenv("COMMIT_SHA", "dev")


def get_runtime_info(include_debug: bool = False) -> dict:
    """
    Get comprehensive runtime information.
    
    Args:
        include_debug: Whether to include debug information
        
    Returns:
        dict: Runtime information dictionary
    """
    info = {
        "status": "ok",
        "uptime_seconds": round(uptime_seconds(), 3),
        "version": app_version()
    }
    
    if include_debug:
        info["info"] = {
            "start_time": START_TIME,
            "artifact_dir": os.getenv("ARTIFACT_DIR", "not_set")
        }
    
    return info
