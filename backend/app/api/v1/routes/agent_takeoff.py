"""
API routes for agent takeoff processing.

Provides endpoints for orchestrating the full takeoff pipeline
with Apryse → LLM → Review workflow.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from backend.app.agent.takeoff import process_takeoff_request, get_session_status, cleanup_old_sessions, TakeoffRequest, TakeoffResponse


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
    upload_file: Optional[UploadFile] = File(None)
):
    """
    Process takeoff request with full pipeline orchestration.
    
    Args:
        session_id: Unique session identifier for idempotency
        file_ref: Reference to existing file (optional)
        upload_file: File upload (optional)
        
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
        if upload_file:
            # For now, save to a temporary location
            # In production, this would be more sophisticated
            import tempfile
            import shutil
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                shutil.copyfileobj(upload_file.file, tmp_file)
                file_ref = tmp_file.name
                logger.info(f"Uploaded file saved to: {file_ref}")
        
        # Create request
        request = TakeoffRequest(
            session_id=session_id,
            file_ref=file_ref
        )
        
        # Process takeoff
        logger.info(f"Processing takeoff request for session {session_id}")
        response = await process_takeoff_request(request)
        
        # Convert to response model
        return TakeoffResponseModel(
            session_id=response.session_id,
            status=response.status,
            proposed_review=response.proposed_review.dict() if response.proposed_review else None,
            summary=response.summary,
            error_message=response.error_message,
            processing_time=response.processing_time
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
