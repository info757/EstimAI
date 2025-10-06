"""
Export API routes for PDF generation.

Provides endpoints for generating PDF reports and summaries.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.app.services.pdf_export.summary import export_session_summary_bytes, create_summary_exporter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/export", tags=["export"])


class ExportSummaryRequest(BaseModel):
    """Request model for PDF summary export."""
    session_id: str


@router.post("/summary")
async def export_summary(request: ExportSummaryRequest):
    """
    Export takeoff summary as PDF.
    
    Args:
        request: Export request with session_id
        
    Returns:
        PDF file response
    """
    try:
        session_id = request.session_id
        
        # Generate PDF bytes
        pdf_bytes = export_session_summary_bytes(session_id)
        
        # Return PDF as response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=estimai_summary_{session_id}.pdf"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to export summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export summary: {str(e)}"
        )


@router.get("/summary/{session_id}")
async def export_summary_get(session_id: str):
    """
    Export takeoff summary as PDF (GET endpoint).
    
    Args:
        session_id: Session identifier
        
    Returns:
        PDF file response
    """
    try:
        # Generate PDF bytes
        pdf_bytes = export_session_summary_bytes(session_id)
        
        # Return PDF as response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=estimai_summary_{session_id}.pdf"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to export summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export summary: {str(e)}"
        )


@router.get("/summary/{session_id}/preview")
async def export_summary_preview(session_id: str):
    """
    Preview takeoff summary as HTML.
    
    Args:
        session_id: Session identifier
        
    Returns:
        HTML preview response
    """
    try:
        exporter = create_summary_exporter()
        html_content = exporter.generate_html(session_id)
        
        return Response(
            content=html_content,
            media_type="text/html"
        )
        
    except Exception as e:
        logger.error(f"Failed to preview summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to preview summary: {str(e)}"
        )