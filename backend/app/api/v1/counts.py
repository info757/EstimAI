"""Count items management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Dict, Any
from datetime import datetime

from ...db import get_db
from ...schemas import CountItemOut, CountItemPatch
from ...models import CountItem as CountItemModel, CountStatus
from ...deps import get_current_user
from ...services.assemblies import map_count_items_to_assemblies, get_assemblies_mapper

router = APIRouter(prefix="/v1")


@router.get("/counts", response_model=List[CountItemOut])
async def get_counts(
    file: Optional[str] = Query(None, description="Filter by PDF filename"),
    page: Optional[int] = Query(None, description="Filter by page number (1-based)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    type: Optional[str] = Query(None, description="Filter by object type"),
    min_conf: Optional[float] = Query(None, description="Minimum confidence threshold"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get count items with optional filters.
    
    Args:
        file: Filter by PDF filename
        page: Filter by page number (1-based)
        status: Filter by status (pending, accepted, rejected, edited)
        type: Filter by object type (water, sewer, storm, etc.)
        min_conf: Minimum confidence threshold (0.0-1.0)
        
    Returns:
        List of CountItemOut objects matching the filters
    """
    try:
        # Build query with filters
        query = db.query(CountItemModel)
        filters = []
        
        if file is not None:
            filters.append(CountItemModel.file == file)
        
        if page is not None:
            filters.append(CountItemModel.page == page)
        
        if status is not None:
            # Validate status
            try:
                status_enum = CountStatus(status)
                filters.append(CountItemModel.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid status: {status}. Must be one of: {[s.value for s in CountStatus]}"
                )
        
        if type is not None:
            filters.append(CountItemModel.type == type)
        
        if min_conf is not None:
            if not 0.0 <= min_conf <= 1.0:
                raise HTTPException(
                    status_code=400,
                    detail="min_conf must be between 0.0 and 1.0"
                )
            filters.append(CountItemModel.confidence >= min_conf)
        
        # Apply all filters
        if filters:
            query = query.filter(and_(*filters))
        
        # Execute query
        count_items = query.all()
        
        return count_items
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving count items: {str(e)}"
        )


@router.patch("/counts/{count_id}", response_model=CountItemOut)
async def patch_count_item(
    count_id: str,
    patch_data: CountItemPatch,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Patch a count item with only the provided fields.
    
    Args:
        count_id: ID of the count item to update
        patch_data: CountItemPatch with only the fields to update
        
    Returns:
        Updated CountItemOut object
    """
    try:
        # Find the count item
        count_item = db.query(CountItemModel).filter(CountItemModel.id == count_id).first()
        if not count_item:
            raise HTTPException(status_code=404, detail="Count item not found")
        
        # Get only the fields that were provided (exclude unset)
        update_dict = patch_data.model_dump(exclude_unset=True)
        
        if not update_dict:
            # No fields to update, return current item
            return count_item
        
        # Update only the provided fields
        for key, value in update_dict.items():
            if hasattr(count_item, key):
                setattr(count_item, key, value)
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid field: {key}"
                )
        
        # Update timestamp
        count_item.updated_at = datetime.utcnow()
        
        # Save changes
        db.add(count_item)
        db.commit()
        db.refresh(count_item)
        
        return count_item
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating count item: {str(e)}"
        )


@router.get("/counts/{count_id}", response_model=CountItemOut)
async def get_count_item(
    count_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific count item by ID.
    
    Args:
        count_id: ID of the count item
        
    Returns:
        CountItemOut object
    """
    try:
        count_item = db.query(CountItemModel).filter(CountItemModel.id == count_id).first()
        if not count_item:
            raise HTTPException(status_code=404, detail="Count item not found")
        return count_item
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving count item: {str(e)}"
        )


@router.delete("/counts/{count_id}")
async def delete_count_item(
    count_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a count item.
    
    Args:
        count_id: ID of the count item to delete
        
    Returns:
        Success message
    """
    try:
        count_item = db.query(CountItemModel).filter(CountItemModel.id == count_id).first()
        if not count_item:
            raise HTTPException(status_code=404, detail="Count item not found")
        
        db.delete(count_item)
        db.commit()
        
        return {"message": "Count item deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting count item: {str(e)}"
        )


@router.get("/counts/assemblies")
async def get_count_assemblies(
    file: Optional[str] = Query(None, description="Filter by PDF filename"),
    page: Optional[int] = Query(None, description="Filter by page number (1-based)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    type: Optional[str] = Query(None, description="Filter by object type"),
    min_conf: Optional[float] = Query(None, description="Minimum confidence threshold"),
    include_pricing: bool = Query(True, description="Include pricing information"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get count items mapped to construction assemblies with CSI codes and pricing.
    
    Args:
        file: Filter by PDF filename
        page: Filter by page number (1-based)
        status: Filter by status (pending, accepted, rejected, edited)
        type: Filter by object type (water, sewer, storm, etc.)
        min_conf: Minimum confidence threshold (0.0-1.0)
        include_pricing: Whether to include pricing calculations
        
    Returns:
        Dictionary with assemblies, pricing, and summary information
    """
    try:
        # Get count items using existing logic
        query = db.query(CountItemModel)
        filters = []
        
        if file is not None:
            filters.append(CountItemModel.file == file)
        
        if page is not None:
            filters.append(CountItemModel.page == page)
        
        if status is not None:
            try:
                status_enum = CountStatus(status)
                filters.append(CountItemModel.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid status: {status}. Must be one of: {[s.value for s in CountStatus]}"
                )
        
        if type is not None:
            filters.append(CountItemModel.type == type)
        
        if min_conf is not None:
            if not 0.0 <= min_conf <= 1.0:
                raise HTTPException(
                    status_code=400,
                    detail="min_conf must be between 0.0 and 1.0"
                )
            filters.append(CountItemModel.confidence >= min_conf)
        
        # Apply all filters
        if filters:
            query = query.filter(and_(*filters))
        
        # Execute query
        count_items = query.all()
        
        # Convert to dictionaries for assembly mapping
        count_item_dicts = []
        for item in count_items:
            item_dict = {
                'id': str(item.id),
                'type': item.type,
                'quantity': getattr(item, 'quantity', 1),  # Default to 1 if not present
                'attributes': getattr(item, 'attributes', {}),  # Get attributes if present
                'file': item.file,
                'page': item.page,
                'confidence': item.confidence,
                'status': item.status.value
            }
            count_item_dicts.append(item_dict)
        
        # Map to assemblies
        assemblies, pricing_items = map_count_items_to_assemblies(count_item_dicts)
        
        # Generate summary
        mapper = get_assemblies_mapper()
        summary = mapper.generate_assembly_summary(assemblies)
        
        # Prepare response
        response = {
            'count_items': len(count_items),
            'assemblies': [
                {
                    'csi_code': assembly.csi_code,
                    'assembly_type': assembly.assembly_type.value,
                    'description': assembly.description,
                    'unit': assembly.unit,
                    'quantity': assembly.quantity,
                    'attributes': assembly.attributes,
                    'pricing_key': assembly.pricing_key
                }
                for assembly in assemblies
            ],
            'summary': summary
        }
        
        # Add pricing if requested
        if include_pricing:
            response['pricing'] = [
                {
                    'csi_code': item.csi_code,
                    'description': item.description,
                    'unit': item.unit,
                    'quantity': item.quantity,
                    'unit_cost': item.unit_cost,
                    'total_cost': item.total_cost,
                    'attributes': item.attributes
                }
                for item in pricing_items
            ]
            
            # Calculate totals
            total_cost = sum(item.total_cost for item in pricing_items if item.total_cost)
            response['pricing_summary'] = {
                'total_cost': total_cost,
                'item_count': len(pricing_items),
                'items_with_pricing': len([item for item in pricing_items if item.unit_cost is not None])
            }
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving assemblies: {str(e)}"
        )


@router.get("/counts/pricing")
async def get_count_pricing(
    file: Optional[str] = Query(None, description="Filter by PDF filename"),
    page: Optional[int] = Query(None, description="Filter by page number (1-based)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    type: Optional[str] = Query(None, description="Filter by object type"),
    min_conf: Optional[float] = Query(None, description="Minimum confidence threshold"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get pricing information for count items.
    
    Args:
        file: Filter by PDF filename
        page: Filter by page number (1-based)
        status: Filter by status (pending, accepted, rejected, edited)
        type: Filter by object type (water, sewer, storm, etc.)
        min_conf: Minimum confidence threshold (0.0-1.0)
        
    Returns:
        Dictionary with pricing information and totals
    """
    try:
        # Get assemblies first
        assemblies_response = await get_count_assemblies(
            file=file,
            page=page,
            status=status,
            type=type,
            min_conf=min_conf,
            include_pricing=True,
            db=db,
            current_user=current_user
        )
        
        # Extract pricing information
        pricing_items = assemblies_response.get('pricing', [])
        pricing_summary = assemblies_response.get('pricing_summary', {})
        
        # Group by CSI code for detailed breakdown
        pricing_by_csi = {}
        for item in pricing_items:
            csi_code = item['csi_code']
            if csi_code not in pricing_by_csi:
                pricing_by_csi[csi_code] = {
                    'description': item['description'],
                    'unit': item['unit'],
                    'unit_cost': item['unit_cost'],
                    'total_quantity': 0,
                    'total_cost': 0,
                    'items': []
                }
            
            pricing_by_csi[csi_code]['total_quantity'] += item['quantity']
            if item['total_cost']:
                pricing_by_csi[csi_code]['total_cost'] += item['total_cost']
            pricing_by_csi[csi_code]['items'].append(item)
        
        return {
            'pricing_items': pricing_items,
            'pricing_by_csi': pricing_by_csi,
            'summary': pricing_summary,
            'total_cost': pricing_summary.get('total_cost', 0),
            'item_count': pricing_summary.get('item_count', 0),
            'items_with_pricing': pricing_summary.get('items_with_pricing', 0)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving pricing: {str(e)}"
        )