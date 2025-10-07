"""
PDF export API endpoints.

Provides endpoints for generating PDF summaries and reports.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
import logging

# Lazy import - moved to function level to avoid circular imports
from backend.app.deps import get_current_user
from backend.app.schemas_estimai import EstimAIResult
from backend.app.services.pdf_export import get_pdf_export_service
from backend.app.services.assemblies import get_assemblies_mapper

router = APIRouter(prefix="/v1/export", tags=["export"])
logger = logging.getLogger(__name__)


@router.post("/summary")
async def export_summary_pdf(
    estimai_result: EstimAIResult,
    project_name: str = Query("Construction Project", description="Name of the project"),
    file_name: str = Query("unknown.pdf", description="Name of the source file"),
    page_number: int = Query(1, description="Page number being analyzed"),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a PDF summary report from EstimAI result.
    
    Args:
        estimai_result: EstimAI result data
        project_name: Name of the project
        file_name: Name of the source file
        page_number: Page number being analyzed
        
    Returns:
        PDF file as response
    """
    try:
        # Get PDF export service
        pdf_service = get_pdf_export_service()
        
        # Generate PDF
        pdf_bytes = pdf_service.generate_summary_pdf(
            estimai_result=estimai_result,
            project_name=project_name,
            file_name=file_name,
            page_number=page_number
        )
        
        # Return PDF response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=estimai_summary_{project_name.replace(' ', '_')}.pdf"
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating PDF summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF summary: {str(e)}"
        )


@router.get("/summary")
async def export_summary_pdf_get(
    project_name: str = Query("Construction Project", description="Name of the project"),
    file_name: str = Query("unknown.pdf", description="Name of the source file"),
    page_number: int = Query(1, description="Page number being analyzed"),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a PDF summary report from existing count items.
    
    This endpoint creates a summary from count items in the database
    rather than requiring an EstimAI result.
    """
    try:
        # Lazy import to avoid circular dependencies
        from backend.app.db import SessionLocal
        
        # Get database session
        db = SessionLocal()
        
        try:
            # Simple implementation - just return a placeholder for now
            return {
                "message": "PDF export endpoint - implementation pending",
                "project_name": project_name,
                "file_name": file_name,
                "page_number": page_number
            }
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error generating PDF summary from count items: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF summary: {str(e)}"
        )


