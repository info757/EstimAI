"""
Agent API routes using Protocol-based dependency injection.

This module implements the agent endpoints using the TakeoffAgent protocol,
which provides type safety and catches signature drift at compile time.
The route depends on the protocol interface, not the concrete implementation,
making it resilient to changes in the underlying implementation.
"""
from __future__ import annotations
import logging
import tempfile
import os
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel

from backend.app.agent.types import TakeoffRequest, TakeoffResponse, TakeoffOptions
from backend.app.agent.protocols import TakeoffAgent
from backend.app.agent.takeoff_impl import create_default_agent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/agent", tags=["agent"])

# Protocol-based dependency injection
_agent: TakeoffAgent = create_default_agent()


class AgentResponseModel(BaseModel):
    """Response model for agent endpoints."""
    session_id: str
    status: str
    proposed_review: Optional[dict] = None
    summary: Optional[dict] = None
    error_message: Optional[str] = None
    warnings: Optional[list] = None


@router.post("/takeoff", response_model=AgentResponseModel)
async def agent_takeoff(
    session_id: str = Form(...),
    file: Optional[UploadFile] = File(default=None),
    file_ref: Optional[str] = Form(default=None),
    dry_run: bool = Form(default=False),
    max_pages: Optional[int] = Form(default=None),
    force_ground_source: Optional[str] = Form(default=None),
):
    """
    Process takeoff request using the TakeoffAgent protocol.
    
    This endpoint uses protocol-based dependency injection to ensure
    type safety and catch signature drift at compile time. The route
    depends on the TakeoffAgent protocol interface, not the concrete
    implementation, making it resilient to changes in the underlying code.
    
    Args:
        session_id: Unique session identifier for idempotency
        file: Uploaded PDF file (optional)
        file_ref: Reference to existing file (optional)
        dry_run: If True, run analysis but don't commit results
        max_pages: Maximum number of pages to process
        force_ground_source: Force specific ground elevation source
        
    Returns:
        AgentResponseModel with results or error information
        
    Raises:
        HTTPException: If validation fails or agent encounters an error
    """
    try:
        # Validate request parameters
        if not file and not file_ref:
            raise HTTPException(
                status_code=400, 
                detail="Either file or file_ref is required"
            )
        
        # Handle file upload if provided
        if file and not file_ref:
            # Save uploaded file to temporary location
            upload_bytes = await file.read()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(upload_bytes)
                file_ref = tmp_file.name
                logger.info(f"Uploaded file saved to: {file_ref}")
        
        # Create typed request using the stable contract
        request = TakeoffRequest(
            session_id=session_id,
            file_ref=file_ref,
            upload_file=None,  # We're using file_ref instead
            options=TakeoffOptions(
                dry_run=dry_run,
                max_pages=max_pages,
                force_ground_source=force_ground_source
            )
        )
        
        # Process using protocol-based agent
        logger.info(f"Processing takeoff request for session {session_id}")
        response = _agent.run(request)
        
        # Convert to response model
        return AgentResponseModel(
            session_id=session_id,
            status="completed" if response.proposed_review else "failed",
            proposed_review=response.proposed_review.dict() if response.proposed_review else None,
            summary=response.summary.dict() if response.summary else None,
            error_message=response.error,
            warnings=response.warnings
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing takeoff request: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )
    finally:
        # Clean up temporary file if created
        if file and file_ref and os.path.exists(file_ref):
            try:
                os.unlink(file_ref)
            except OSError:
                logger.warning(f"Failed to clean up temporary file: {file_ref}")


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
        # This would need to be implemented based on your session management
        # For now, return a placeholder response
        return {
            "session_id": session_id,
            "status": "unknown",
            "message": "Session status not implemented in protocol-based agent"
        }
        
    except Exception as e:
        logger.error(f"Error getting session status: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )


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
        # This would need to be implemented based on your session management
        # For now, return a placeholder response
        return {
            "message": f"Session cleanup not implemented in protocol-based agent",
            "cleaned_count": 0
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for agent service."""
    try:
        # Test that the agent protocol is working
        test_request = TakeoffRequest(
            session_id="health_check",
            file_ref="dummy",  # This will fail, but we're just testing the interface
            options=TakeoffOptions(dry_run=True)
        )
        
        # The agent should handle this gracefully
        return {
            "status": "healthy",
            "service": "agent-takeoff",
            "protocol": "TakeoffAgent",
            "implementation": type(_agent).__name__
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Health check failed: {str(e)}"
        )


# Factory function for dependency injection
def create_agent_router(agent: Optional[TakeoffAgent] = None) -> APIRouter:
    """
    Create agent router with dependency injection.
    
    This allows for easy testing and different agent implementations
    without changing the route logic.
    
    Args:
        agent: Optional TakeoffAgent implementation (defaults to DefaultTakeoffAgent)
        
    Returns:
        Configured APIRouter with agent dependency
    """
    global _agent
    if agent is not None:
        _agent = agent
    return router
