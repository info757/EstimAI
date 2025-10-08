"""
LangSmith tracing integration for EstimAI agents.

Provides observability for all LLM calls and agent operations.
"""
import os
import logging
from typing import Any, Dict, Optional
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)

# Check if LangSmith is enabled
LANGSMITH_ENABLED = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "estimai-takeoff")

if LANGSMITH_ENABLED:
    try:
        from langsmith import Client, traceable
        from langsmith.run_helpers import get_current_run_tree
        
        client = Client()
        logger.info(f"✅ LangSmith tracing enabled (project: {LANGSMITH_PROJECT})")
    except ImportError:
        logger.warning("LangSmith requested but not installed. Run: pip install langsmith")
        LANGSMITH_ENABLED = False
        traceable = lambda **kwargs: lambda f: f  # No-op decorator
else:
    # No-op decorator when disabled
    traceable = lambda **kwargs: lambda f: f
    client = None


def get_tracer():
    """Get the LangSmith client (or None if disabled)."""
    return client if LANGSMITH_ENABLED else None


@traceable(name="vision_takeoff", run_type="chain", project_name=LANGSMITH_PROJECT)
def trace_vision_takeoff(
    pdf_path: str,
    page_count: int,
    result: Dict[str, Any],
    latency_ms: float
) -> Dict[str, Any]:
    """
    Trace a complete vision-based takeoff operation.
    
    Args:
        pdf_path: Path to PDF file
        page_count: Number of pages processed
        result: Takeoff result with pipes
        latency_ms: Processing time in milliseconds
    
    Returns:
        Metadata dict for logging
    """
    storm_count = len(result.get("storm_pipes", []))
    sanitary_count = len(result.get("sanitary_pipes", []))
    water_count = len(result.get("water_pipes", []))
    
    metadata = {
        "pdf_path": os.path.basename(pdf_path),
        "page_count": page_count,
        "pipes_detected": {
            "storm": storm_count,
            "sanitary": sanitary_count,
            "water": water_count,
            "total": storm_count + sanitary_count + water_count
        },
        "latency_ms": latency_ms,
        "timestamp": datetime.now().isoformat(),
        "detector_type": "vision",
        "model": "gpt-4o"
    }
    
    if LANGSMITH_ENABLED:
        logger.info(f"📊 LangSmith trace: vision_takeoff - {metadata['pipes_detected']['total']} pipes")
    
    return metadata


@traceable(name="pipe_classification", run_type="llm", project_name=LANGSMITH_PROJECT)
def trace_pipe_classification(
    patches: list,
    model: str,
    detections: list,
    latency_ms: float,
    token_usage: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Trace a pipe classification LLM call.
    
    Args:
        patches: Input patches sent to LLM
        model: Model name (e.g., "gpt-4o-mini")
        detections: Detected pipes returned by LLM
        latency_ms: LLM call latency
        token_usage: Token counts (prompt, completion, total)
    
    Returns:
        Metadata dict
    """
    metadata = {
        "model": model,
        "patch_count": len(patches),
        "detection_count": len(detections),
        "latency_ms": latency_ms,
        "token_usage": token_usage or {},
        "timestamp": datetime.now().isoformat(),
        "detector_type": "apryse_llm"
    }
    
    if LANGSMITH_ENABLED:
        logger.info(f"📊 LangSmith trace: pipe_classification - {len(detections)} detections")
    
    return metadata


@traceable(name="elevation_extraction", run_type="llm", project_name=LANGSMITH_PROJECT)
def trace_elevation_extraction(
    polyline_count: int,
    text_run_count: int,
    elevations_found: int,
    method: str,
    latency_ms: float
) -> Dict[str, Any]:
    """
    Trace elevation extraction operation.
    
    Args:
        polyline_count: Number of polylines processed
        text_run_count: Number of text runs available
        elevations_found: Number of pipes with elevations extracted
        method: Extraction method ("llm", "regex", "hybrid")
        latency_ms: Processing time
    
    Returns:
        Metadata dict
    """
    metadata = {
        "polyline_count": polyline_count,
        "text_run_count": text_run_count,
        "elevations_found": elevations_found,
        "success_rate": elevations_found / polyline_count if polyline_count > 0 else 0,
        "method": method,
        "latency_ms": latency_ms,
        "timestamp": datetime.now().isoformat()
    }
    
    if LANGSMITH_ENABLED:
        logger.info(
            f"📊 LangSmith trace: elevation_extraction - "
            f"{elevations_found}/{polyline_count} pipes ({metadata['success_rate']:.1%})"
        )
    
    return metadata


def log_agent_run(
    session_id: str,
    pdf_path: str,
    result: Dict[str, Any],
    latency_ms: float,
    error: Optional[str] = None
):
    """
    Log a complete agent run to LangSmith.
    
    This is a high-level wrapper that logs the entire takeoff operation.
    """
    if not LANGSMITH_ENABLED or not client:
        return
    
    try:
        pipes_total = result.get("summary", {}).get("pipes_total", 0)
        
        client.create_run(
            name="takeoff_agent_run",
            run_type="chain",
            project_name=LANGSMITH_PROJECT,
            inputs={
                "session_id": session_id,
                "pdf": os.path.basename(pdf_path)
            },
            outputs={
                "pipes_total": pipes_total,
                "networks": {
                    k: len(v.get("pipes", []))
                    for k, v in result.get("proposed_review", {}).get("payload", {}).get("networks", {}).items()
                },
                "qa_flags": result.get("summary", {}).get("qa_flags", {}),
                "error": error
            },
            extra={
                "metadata": {
                    "latency_ms": latency_ms,
                    "timestamp": datetime.now().isoformat(),
                    "status": "error" if error else "success"
                }
            }
        )
        
        logger.info(f"📊 LangSmith logged agent run: {session_id} - {pipes_total} pipes")
    
    except Exception as e:
        logger.warning(f"Failed to log to LangSmith: {e}")
