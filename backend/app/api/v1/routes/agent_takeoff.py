"""
Agent takeoff API endpoints.

Provides endpoints for automated takeoff processing workflows.
"""
import tempfile
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from backend.app.agent.takeoff import run_takeoff_agent, AgentOptions, ProposedReview

router = APIRouter(prefix="/v1/agent", tags=["agent"])


class TakeoffRequest(BaseModel):
    """Request model for agent takeoff."""
    session_id: str
    file_ref: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class TakeoffResponse(BaseModel):
    """Response model for agent takeoff."""
    proposed_review: ProposedReview
    summary: Dict[str, Any]
    warnings: List[str]


@router.post("/takeoff", response_model=TakeoffResponse)
async def agent_takeoff(
    session_id: str = Form(...),
    file: Optional[UploadFile] = File(None),
    file_ref: Optional[str] = Form(None),
    dry_run: bool = Form(False),
    timeout_sec: int = Form(300),
    include_warnings: bool = Form(True),
    force_regenerate: bool = Form(False)
):
    """
    Run agent takeoff processing workflow.
    
    Args:
        session_id: Unique session identifier
        file: Uploaded PDF file
        file_ref: Reference to existing file
        dry_run: Return proposed payload without committing
        timeout_sec: Processing timeout in seconds
        include_warnings: Include warning messages
        force_regenerate: Force regeneration even if cached
        
    Returns:
        ProposedReview with complete analysis
    """
    try:
        # Determine file path
        if file is not None:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                file_path = tmp_file.name
        elif file_ref:
            file_path = file_ref
        else:
            raise HTTPException(
                status_code=400, 
                detail="Either file or file_ref must be provided"
            )
        
        # Create agent options
        options = AgentOptions(
            dry_run=dry_run,
            timeout_sec=timeout_sec,
            include_warnings=include_warnings,
            force_regenerate=force_regenerate
        )
        
        # Run agent workflow
        proposed_review = run_takeoff_agent(session_id, file_path, options)
        
        # Create summary
        summary = {
            "session_id": proposed_review.session_id,
            "processing_time_sec": proposed_review.processing_time_sec,
            "ground_sources": proposed_review.ground_sources,
            "networks": {
                "storm": {
                    "pipes": len(proposed_review.payload.networks.storm.pipes) if proposed_review.payload.networks.storm else 0,
                    "structures": len(proposed_review.payload.networks.storm.structures) if proposed_review.payload.networks.storm else 0
                },
                "sanitary": {
                    "pipes": len(proposed_review.payload.networks.sanitary.pipes) if proposed_review.payload.networks.sanitary else 0,
                    "manholes": len(proposed_review.payload.networks.sanitary.manholes) if proposed_review.payload.networks.sanitary else 0
                },
                "water": {
                    "pipes": len(proposed_review.payload.networks.water.pipes) if proposed_review.payload.networks.water else 0,
                    "hydrants": len(proposed_review.payload.networks.water.hydrants) if proposed_review.payload.networks.water else 0,
                    "valves": len(proposed_review.payload.networks.water.valves) if proposed_review.payload.networks.water else 0
                }
            },
            "sitework": {
                "curb_lf": proposed_review.payload.roadway.curb_lf,
                "sidewalk_sf": proposed_review.payload.roadway.sidewalk_sf,
                "silt_fence_lf": proposed_review.payload.e_sc.silt_fence_lf,
                "inlet_protection_ea": proposed_review.payload.e_sc.inlet_protection_ea
            },
            "earthwork": {
                "cut_cy": proposed_review.payload.earthwork.cut_cy,
                "fill_cy": proposed_review.payload.earthwork.fill_cy,
                "source": proposed_review.payload.earthwork.source
            },
            "qa_flags": len(proposed_review.payload.qa_flags)
        }
        
        return TakeoffResponse(
            proposed_review=proposed_review,
            summary=summary,
            warnings=proposed_review.warnings
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent takeoff failed: {str(e)}"
        )
    finally:
        # Clean up temporary file if created
        if file is not None and 'file_path' in locals():
            try:
                os.unlink(file_path)
            except:
                pass


@router.get("/takeoff/{session_id}/status")
async def get_agent_status(session_id: str):
    """
    Get status of agent processing session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Session status information
    """
    from backend.app.agent.takeoff import get_takeoff_agent
    
    agent = get_takeoff_agent()
    
    # Check if session is processing
    is_processing = session_id in agent.processing_sessions
    processing_time = None
    
    if is_processing:
        processing_time = time.time() - agent.processing_sessions[session_id]
    
    # Check cache
    cached_sessions = [key.split(':')[0] for key in agent.session_cache.keys() if key.startswith(session_id)]
    
    return {
        "session_id": session_id,
        "is_processing": is_processing,
        "processing_time_sec": processing_time,
        "cached_sessions": len(cached_sessions),
        "cache_keys": cached_sessions
    }


@router.delete("/takeoff/{session_id}/cache")
async def clear_agent_cache(session_id: str):
    """
    Clear agent cache for session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Cache clearing result
    """
    from backend.app.agent.takeoff import get_takeoff_agent
    
    agent = get_takeoff_agent()
    
    # Remove cached sessions
    keys_to_remove = [key for key in agent.session_cache.keys() if key.startswith(f"{session_id}:")]
    
    for key in keys_to_remove:
        del agent.session_cache[key]
    
    return {
        "session_id": session_id,
        "cleared_keys": len(keys_to_remove),
        "remaining_cache_size": len(agent.session_cache)
    }