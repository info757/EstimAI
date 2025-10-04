"""
Demo mode API endpoints.

Provides endpoints for demo mode information, sample files, and demo-specific features.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional
import logging

from backend.app.deps import get_current_user
from backend.app.core.demo_config import get_demo_manager, is_demo_mode
from backend.app.middleware.security import get_error_handler

router = APIRouter(prefix="/v1/demo", tags=["demo"])
logger = logging.getLogger(__name__)


@router.get("/banner")
async def get_demo_banner(
    current_user: dict = Depends(get_current_user)
):
    """
    Get demo mode banner information.
    
    Returns information about demo mode status, limits, and available sample files.
    """
    try:
        demo_manager = get_demo_manager()
        banner_info = demo_manager.get_demo_banner()
        
        return banner_info
        
    except Exception as e:
        logger.error(f"Error getting demo banner info: {e}")
        error_handler = get_error_handler()
        return error_handler.create_error_response(
            "DEMO_INFO_ERROR",
            "Failed to get demo mode information",
            500
        )


@router.get("/sample-files")
async def get_sample_files(
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of available sample files for demos.
    
    Returns detailed information about sample files including descriptions,
    features, and file sizes.
    """
    try:
        demo_manager = get_demo_manager()
        sample_files = demo_manager.get_sample_files()
        
        return {
            "sample_files": sample_files,
            "total_count": len(sample_files),
            "demo_mode": is_demo_mode()
        }
        
    except Exception as e:
        logger.error(f"Error getting sample files: {e}")
        error_handler = get_error_handler()
        return error_handler.create_error_response(
            "SAMPLE_FILES_ERROR",
            "Failed to get sample files",
            500
        )


@router.get("/sample-files/{filename}")
async def download_sample_file(
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Download a sample file for demo purposes.
    
    Args:
        filename: Name of the sample file to download
        
    Returns:
        File download response
    """
    try:
        demo_manager = get_demo_manager()
        file_path = demo_manager.sample_file_manager.get_sample_file_path(filename)
        
        if not file_path:
            raise HTTPException(
                status_code=404,
                detail=f"Sample file '{filename}' not found"
            )
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/pdf"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading sample file {filename}: {e}")
        error_handler = get_error_handler()
        return error_handler.create_error_response(
            "DOWNLOAD_ERROR",
            f"Failed to download sample file: {filename}",
            500
        )


@router.get("/limits")
async def get_demo_limits(
    current_user: dict = Depends(get_current_user)
):
    """
    Get demo mode limits and restrictions.
    
    Returns information about file size limits, rate limits, and session limits.
    """
    try:
        demo_manager = get_demo_manager()
        limits = demo_manager.get_demo_limits()
        
        return {
            "limits": limits,
            "demo_mode": is_demo_mode(),
            "description": "Demo mode limits for safe demonstration"
        }
        
    except Exception as e:
        logger.error(f"Error getting demo limits: {e}")
        error_handler = get_error_handler()
        return error_handler.create_error_response(
            "LIMITS_ERROR",
            "Failed to get demo limits",
            500
        )


@router.post("/session/register")
async def register_demo_session(
    session_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    Register a new demo session.
    
    Args:
        session_data: Session information including session_id and optional user_info
        
    Returns:
        Registration confirmation
    """
    try:
        demo_manager = get_demo_manager()
        
        session_id = session_data.get("session_id")
        if not session_id:
            raise HTTPException(
                status_code=400,
                detail="session_id is required"
            )
        
        user_info = session_data.get("user_info", {})
        demo_manager.register_demo_session(session_id, user_info)
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Demo session registered successfully",
            "limits": demo_manager.get_demo_limits()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering demo session: {e}")
        error_handler = get_error_handler()
        return error_handler.create_error_response(
            "SESSION_REGISTRATION_ERROR",
            "Failed to register demo session",
            500
        )


@router.get("/session/{session_id}/status")
async def get_demo_session_status(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get status of a demo session.
    
    Args:
        session_id: ID of the demo session
        
    Returns:
        Session status and limits information
    """
    try:
        demo_manager = get_demo_manager()
        
        if session_id not in demo_manager.active_sessions:
            raise HTTPException(
                status_code=404,
                detail=f"Demo session '{session_id}' not found"
            )
        
        limits_check = demo_manager.check_demo_limits(session_id)
        session_info = demo_manager.active_sessions[session_id]
        
        return {
            "session_id": session_id,
            "status": "active",
            "limits_check": limits_check,
            "session_info": {
                "created_at": session_info["created_at"],
                "requests_count": session_info["requests_count"],
                "last_request": session_info["last_request"]
            },
            "demo_limits": demo_manager.get_demo_limits()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting demo session status: {e}")
        error_handler = get_error_handler()
        return error_handler.create_error_response(
            "SESSION_STATUS_ERROR",
            f"Failed to get demo session status: {session_id}",
            500
        )


@router.post("/session/{session_id}/request")
async def record_demo_request(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Record a demo request for rate limiting.
    
    Args:
        session_id: ID of the demo session
        
    Returns:
        Request recording confirmation
    """
    try:
        demo_manager = get_demo_manager()
        
        if session_id not in demo_manager.active_sessions:
            raise HTTPException(
                status_code=404,
                detail=f"Demo session '{session_id}' not found"
            )
        
        # Check limits before recording
        limits_check = demo_manager.check_demo_limits(session_id)
        if not limits_check["allowed"]:
            raise HTTPException(
                status_code=429,
                detail=f"Demo session limit exceeded: {limits_check['reason']}"
            )
        
        # Record the request
        demo_manager.record_demo_request(session_id)
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Demo request recorded successfully",
            "limits_check": limits_check
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording demo request: {e}")
        error_handler = get_error_handler()
        return error_handler.create_error_response(
            "REQUEST_RECORDING_ERROR",
            f"Failed to record demo request: {session_id}",
            500
        )


@router.get("/health")
async def demo_health_check():
    """
    Demo mode health check endpoint.
    
    Returns basic health information for demo mode.
    """
    try:
        demo_manager = get_demo_manager()
        
        return {
            "status": "healthy",
            "demo_mode": is_demo_mode(),
            "active_sessions": len(demo_manager.active_sessions),
            "sample_files_count": len(demo_manager.sample_file_manager.get_sample_files()),
            "limits": demo_manager.get_demo_limits()
        }
        
    except Exception as e:
        logger.error(f"Demo health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "demo_mode": False
        }
