"""
API routes for agent takeoff processing.

Provides endpoints for orchestrating the full takeoff pipeline
with Apryse → LLM → Review workflow.

This endpoint uses the stable agent contract defined in backend.app.agent.types
to ensure consistent request/response handling.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from backend.app.agent import TakeoffRequest, TakeoffResponse, TakeoffOptions
from backend.app.agent.takeoff_impl import create_default_agent
from backend.app.agent.takeoff import get_session_status, cleanup_old_sessions


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/agent", tags=["agent"])


class TakeoffRequestModel(BaseModel):
    """Request model for takeoff processing."""
    session_id: str
    file_ref: Optional[str] = None


class TakeoffResponseModel(BaseModel):
    """Response model for takeoff processing."""
    session_id: str
    status: str
    proposed_review: Optional[dict] = None
    summary: Optional[dict] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None


@router.post("/takeoff", response_model=TakeoffResponseModel)
async def post_agent_takeoff(
    session_id: str = Form(...),
    file_ref: Optional[str] = Form(None),
    upload_file: Optional[UploadFile] = File(None),
    dry_run: bool = Form(False),
    max_pages: Optional[int] = Form(None),
    force_ground_source: Optional[str] = Form(None)
):
    """
    Process takeoff request with full pipeline orchestration.
    
    This endpoint uses the stable agent contract defined in backend.app.agent.types
    to ensure consistent request/response handling.
    
    Args:
        session_id: Unique session identifier for idempotency
        file_ref: Reference to existing file (optional)
        upload_file: File upload (optional)
        dry_run: If True, run analysis but don't commit results
        max_pages: Maximum number of pages to process (None = all pages)
        force_ground_source: Force specific ground elevation source
        
    Returns:
        TakeoffResponseModel with results or error information
    """
    try:
        # Validate request
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")
        
        if not file_ref and not upload_file:
            raise HTTPException(status_code=400, detail="Either file_ref or upload_file is required")
        
        # Handle file upload if provided
        upload_bytes = None
        if upload_file:
            upload_bytes = await upload_file.read()
            logger.info(f"Uploaded file received: {len(upload_bytes)} bytes")
        
        # Create typed request using the stable contract
        request = TakeoffRequest(
            session_id=session_id,
            file_ref=file_ref,
            upload_file=upload_bytes,
            options=TakeoffOptions(
                dry_run=dry_run,
                max_pages=max_pages,
                force_ground_source=force_ground_source
            )
        )
        
        # Process takeoff using the stable contract
        logger.info(f"Processing takeoff request for session {session_id}")
        
        # Create and run the agent
        agent = create_default_agent()
        response = agent.run(request)
        
        # Convert to response model
        return TakeoffResponseModel(
            session_id=session_id,
            status="completed" if response.proposed_review else "failed",
            proposed_review=response.proposed_review.dict() if response.proposed_review else None,
            summary=response.summary.dict() if response.summary else None,
            error_message=response.error,
            processing_time=None  # Not tracked in new implementation
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing takeoff request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/takeoff/{session_id}/status")
async def get_takeoff_status(session_id: str):
    """
    Get status of takeoff processing session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Session status information
    """
    try:
        session = get_session_status(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": session.session_id,
            "status": session.status,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "retry_count": session.retry_count,
            "error_message": session.error_message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/cleanup")
async def cleanup_sessions(max_age_hours: int = 24):
    """
    Clean up old sessions.
    
    Args:
        max_age_hours: Maximum age of sessions to keep (default: 24 hours)
        
    Returns:
        Number of sessions cleaned up
    """
    try:
        cleaned_count = cleanup_old_sessions(max_age_hours)
        
        return {
            "message": f"Cleaned up {cleaned_count} old sessions",
            "cleaned_count": cleaned_count
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint for agent service."""
    try:
        # Check if agent is responsive
        return {
            "status": "healthy",
            "service": "agent-takeoff",
            "active_sessions": len(get_session_status.__globals__.get('_agent', {}).sessions)
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")
