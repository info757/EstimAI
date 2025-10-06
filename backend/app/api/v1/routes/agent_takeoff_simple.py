"""
Simple agent takeoff API routes.

Provides endpoints for orchestrating the takeoff pipeline.
"""
import logging
import tempfile
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from backend.app.agent.takeoff_simple import run_takeoff_agent, ProposedReview

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/agent", tags=["agent"])


@router.post("/takeoff")
async def post_agent_takeoff(
    session_id: str = Form(...),
    file_ref: Optional[str] = Form(None),
    upload_file: Optional[UploadFile] = File(None)
):
    """
    Process takeoff request with full pipeline orchestration.
    
    Args:
        session_id: Unique session identifier for idempotency
        file_ref: Reference to existing file (optional)
        upload_file: File upload (optional)
        
    Returns:
        ProposedReview with results or error information
    """
    try:
        # Validate input
        if not file_ref and not upload_file:
            raise HTTPException(
                status_code=400,
                detail="Either file_ref or upload_file must be provided"
            )
        
        # Determine file path
        if upload_file is not None:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                content = await upload_file.read()
                tmp_file.write(content)
                file_path = tmp_file.name
        else:
            file_path = file_ref
        
        # Run takeoff agent
        result = run_takeoff_agent(session_id, file_path)
        
        return {
            "proposed_review": result,
            "summary": {
                "session_id": result.session_id,
                "processing_time_sec": result.processing_time_sec,
                "ground_sources": result.ground_sources,
                "networks": {
                    "storm": {
                        "pipes": len(result.payload.networks.storm.pipes) if result.payload.networks.storm else 0,
                        "structures": len(result.payload.networks.storm.structures) if result.payload.networks.storm else 0
                    },
                    "sanitary": {
                        "pipes": len(result.payload.networks.sanitary.pipes) if result.payload.networks.sanitary else 0,
                        "manholes": len(result.payload.networks.sanitary.manholes) if result.payload.networks.sanitary else 0
                    },
                    "water": {
                        "pipes": len(result.payload.networks.water.pipes) if result.payload.networks.water else 0,
                        "hydrants": len(result.payload.networks.water.hydrants) if result.payload.networks.water else 0,
                        "valves": len(result.payload.networks.water.valves) if result.payload.networks.water else 0
                    }
                },
                "qa_flags": len(result.payload.qa_flags)
            },
            "warnings": result.warnings
        }
        
    except Exception as e:
        logger.error(f"Agent takeoff failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Agent takeoff failed: {str(e)}"
        )
    finally:
        # Clean up temporary file if created
        if upload_file is not None and 'file_path' in locals():
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
    return {
        "session_id": session_id,
        "status": "completed",
        "message": "Simple agent implementation - no session tracking"
    }
