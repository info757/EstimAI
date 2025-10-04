"""
PDF export API endpoints.

Provides endpoints for generating PDF summaries and reports.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
import logging

from backend.app.db import get_db
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
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a PDF summary report from existing count items.
    
    This endpoint creates a summary from count items in the database
    rather than requiring an EstimAI result.
    """
    try:
        from backend.app.models import CountItem as CountItemModel
        from backend.app.schemas_estimai import EstimAIResult, Networks, StormNetwork, SanitaryNetwork, WaterNetwork, Roadway, ESC, Earthwork
        
        # Get count items for the specified file and page
        count_items = db.query(CountItemModel).filter(
            CountItemModel.file == file_name,
            CountItemModel.page == page_number
        ).all()
        
        if not count_items:
            raise HTTPException(
                status_code=404,
                detail=f"No count items found for file {file_name} and page {page_number}"
            )
        
        # Convert count items to EstimAI result format
        estimai_result = _convert_count_items_to_estimai_result(count_items)
        
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating PDF summary from count items: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF summary: {str(e)}"
        )


def _convert_count_items_to_estimai_result(count_items) -> EstimAIResult:
    """Convert count items to EstimAI result format."""
    from backend.app.schemas_estimai import EstimAIResult, Networks, StormNetwork, SanitaryNetwork, WaterNetwork, Roadway, ESC, Earthwork, Pipe, Node
    
    # Group items by type
    storm_pipes = []
    sanitary_pipes = []
    water_pipes = []
    structures = []
    sitework_items = []
    
    for item in count_items:
        item_type = item.type.lower()
        attributes = getattr(item, 'attributes', {}) or {}
        
        if 'storm' in item_type or 'pipe' in item_type:
            # Create pipe object
            pipe = Pipe(
                id=item.id,
                from_id="unknown",
                to_id="unknown",
                length_ft=item.quantity or 0,
                dia_in=attributes.get('diameter_in'),
                mat=attributes.get('material'),
                slope=None,
                avg_depth_ft=attributes.get('avg_depth_ft'),
                extra=attributes
            )
            storm_pipes.append(pipe)
        
        elif 'sanitary' in item_type:
            pipe = Pipe(
                id=item.id,
                from_id="unknown",
                to_id="unknown",
                length_ft=item.quantity or 0,
                dia_in=attributes.get('diameter_in'),
                mat=attributes.get('material'),
                slope=None,
                avg_depth_ft=attributes.get('avg_depth_ft'),
                extra=attributes
            )
            sanitary_pipes.append(pipe)
        
        elif 'water' in item_type:
            pipe = Pipe(
                id=item.id,
                from_id="unknown",
                to_id="unknown",
                length_ft=item.quantity or 0,
                dia_in=attributes.get('diameter_in'),
                mat=attributes.get('material'),
                slope=None,
                avg_depth_ft=attributes.get('avg_depth_ft'),
                extra=attributes
            )
            water_pipes.append(pipe)
        
        elif 'manhole' in item_type or 'inlet' in item_type:
            node = Node(
                id=item.id,
                kind="manhole" if 'manhole' in item_type else "inlet",
                x=item.x_pdf,
                y=item.y_pdf,
                attrs=attributes
            )
            structures.append(node)
        
        elif 'curb' in item_type or 'sidewalk' in item_type:
            sitework_items.append({
                'type': item_type,
                'quantity': item.quantity or 0,
                'attributes': attributes
            })
    
    # Create networks
    networks = Networks()
    
    if storm_pipes:
        networks.storm = StormNetwork(pipes=storm_pipes, structures=[])
    
    if sanitary_pipes:
        networks.sanitary = SanitaryNetwork(pipes=sanitary_pipes, manholes=[])
    
    if water_pipes:
        networks.water = WaterNetwork(pipes=water_pipes, hydrants=[], valves=[])
    
    # Create roadway
    roadway = Roadway()
    for item in sitework_items:
        if 'curb' in item['type']:
            roadway.curb_lf = item['quantity']
        elif 'sidewalk' in item['type']:
            roadway.sidewalk_sf = item['quantity']
    
    # Create ESC
    esc = ESC()
    
    # Create earthwork
    earthwork = Earthwork()
    
    # Create EstimAI result
    result = EstimAIResult(
        sheet_units="ft",
        scale=None,
        networks=networks,
        roadway=roadway,
        e_sc=esc,
        earthwork=earthwork,
        qa_flags=[]
    )
    
    return result
