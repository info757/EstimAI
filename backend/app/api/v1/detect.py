"""Detection API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict, Any
import uuid
from pathlib import Path
import math

from ...db import get_db
from ...schemas import DetectResponse, DetectItem
from ...models import CountItem as CountItemModel, CountStatus
from ...deps import get_current_user
from ...services.detect import run_detection
from ...core.config import settings

router = APIRouter(prefix="/v1")


@router.post("/detect", response_model=DetectResponse)
async def detect_counts(
    file: str = Query(..., description="PDF filename"),
    page: int = Query(..., description="Page number (0-based)"),
    points_per_foot: float = Query(50.0, description="Points per foot scale factor"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Detect count items on a specific page of a PDF using the configured detector.
    
    Steps:
    1. Resolve PDF path and validate file exists
    2. Run detection pipeline (rasterize + detect + map coordinates)
    3. Upsert count items with deduplication
    4. Return detection results
    """
    try:
        # Step 1: Resolve PDF path and validate
        pdf_path = Path(settings.get_files_dir()) / file
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail=f"PDF file not found: {file}")
        
        # Step 2: Run detection pipeline
        print(f"Running detection on {file}, page {page}")
        hits, meta = run_detection(str(pdf_path), page)
        
        # Step 3: Process hits and upsert count items
        created_items = []
        skipped_items = []
        totals = {}
        
        for hit in hits:
            # Check for existing pending item within 10 points
            existing = db.query(CountItemModel).filter(
                and_(
                    CountItemModel.file == file,
                    CountItemModel.page == page + 1,  # Convert to 1-based
                    CountItemModel.type == hit["type"],
                    CountItemModel.status == CountStatus.PENDING,
                    # Distance check: sqrt((x1-x2)^2 + (y1-y2)^2) <= 10
                    (
                        (CountItemModel.x_pdf - hit["x_pdf"]) ** 2 + 
                        (CountItemModel.y_pdf - hit["y_pdf"]) ** 2
                    ) <= 100  # 10^2 = 100
                )
            ).first()
            
            if existing:
                # Skip duplicate
                skipped_items.append(hit)
                continue
            
            # Create new count item
            count_item = CountItemModel(
                id=str(uuid.uuid4()),
                file=file,
                page=page + 1,  # Convert to 1-based
                type=hit["type"],
                confidence=hit["confidence"],
                x_pdf=hit["x_pdf"],
                y_pdf=hit["y_pdf"],
                points_per_foot=points_per_foot,
                status=CountStatus.PENDING
            )
            
            db.add(count_item)
            created_items.append(count_item)
            
            # Update totals
            type_name = hit["type"]
            totals[type_name] = totals.get(type_name, 0) + 1
        
        # Commit all changes
        db.commit()
        
        # Refresh items to get IDs
        for item in created_items:
            db.refresh(item)
        
        # Step 4: Build response
        detect_items = [
            DetectItem(
                id=item.id,
                type=item.type,
                x_pdf=item.x_pdf,
                y_pdf=item.y_pdf,
                confidence=item.confidence,
                status="pending"
            )
            for item in created_items
        ]
        
        response = DetectResponse(
            file=file,
            page=page + 1,  # Convert to 1-based for response
            points_per_foot=points_per_foot,
            counts=detect_items,
            totals=totals
        )
        
        print(f"Detection complete: {len(created_items)} new items, {len(skipped_items)} duplicates skipped")
        print(f"Totals: {totals}")
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        db.rollback()
        print(f"Detection error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Detection failed: {str(e)}"
        )


@router.get("/detect/{file}/{page}")
async def get_detection_results(
    file: str,
    page: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all count items for a specific file and page.
    
    Args:
        file: PDF filename
        page: Page number (1-based)
        
    Returns:
        List of count items for the specified file and page
    """
    try:
        count_items = db.query(CountItemModel).filter(
            CountItemModel.file == file,
            CountItemModel.page == page
        ).all()
        
        return {
            "file": file,
            "page": page,
            "count_items": count_items,
            "total": len(count_items)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving count items: {str(e)}"
        )


@router.get("/detect/stats/{file}")
async def get_detection_stats(
    file: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get detection statistics for a file.
    
    Args:
        file: PDF filename
        
    Returns:
        Statistics about detections for the file
    """
    try:
        # Get all count items for the file
        count_items = db.query(CountItemModel).filter(
            CountItemModel.file == file
        ).all()
        
        # Calculate statistics
        total_items = len(count_items)
        status_counts = {}
        type_counts = {}
        page_counts = {}
        
        for item in count_items:
            # Status counts
            status = item.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Type counts
            type_name = item.type
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
            
            # Page counts
            page_num = item.page
            page_counts[page_num] = page_counts.get(page_num, 0) + 1
        
        return {
            "file": file,
            "total_items": total_items,
            "status_counts": status_counts,
            "type_counts": type_counts,
            "page_counts": page_counts,
            "pages": sorted(page_counts.keys())
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving detection stats: {str(e)}"
        )