"""Count items management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime

from ...db import get_db
from ...schemas import CountItemOut, CountItemPatch
from ...models import CountItem as CountItemModel, CountStatus
from ...deps import get_current_user

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