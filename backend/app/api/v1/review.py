"""Review session management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
import uuid
import csv
from datetime import datetime
from pathlib import Path

from ...db import get_db
from ...schemas import ReviewSession, ReviewSessionCreate, CommitRequest, ReportOut
from ...models import ReviewSession as ReviewSessionModel, CountItem as CountItemModel, CountStatus
from ...deps import get_current_user
from ...utils.metrics import compute_pr_f1, localization_stats
from ...core.config import settings

router = APIRouter(prefix="/v1")


@router.post("/review/commit", response_model=ReportOut)
async def commit_review(
    commit_request: CommitRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Commit review results and generate metrics report.
    
    Steps:
    1. Load count items for file/pages
    2. Calculate TP, FP, FN based on status
    3. Build localization pairs for edited items
    4. Compute PR/F1 and localization stats
    5. Export accepted items to CSV
    6. Create/update ReviewSession with metrics
    7. Return ReportOut with CSV URL
    """
    try:
        # Step 1: Load count items for file/pages
        count_items = db.query(CountItemModel).filter(
            and_(
                CountItemModel.file == commit_request.file,
                CountItemModel.page.in_(commit_request.pages)
            )
        ).all()
        
        if not count_items:
            raise HTTPException(
                status_code=404, 
                detail=f"No count items found for file {commit_request.file} and pages {commit_request.pages}"
            )
        
        # Step 2: Calculate TP, FP, FN
        tp = len([item for item in count_items if item.status == CountStatus.ACCEPTED])
        fp = len([item for item in count_items if item.status == CountStatus.REJECTED])
        
        # FN = items with confidence is None and status=="accepted" (reviewer-added)
        fn = len([
            item for item in count_items 
            if item.confidence is None and item.status == CountStatus.ACCEPTED
        ])
        
        # Step 3: Build localization pairs for edited items
        localization_pairs = []
        for item in count_items:
            if (item.status in [CountStatus.EDITED, CountStatus.ACCEPTED] and 
                item.x_pdf_edited is not None and item.y_pdf_edited is not None):
                
                # Use edited coordinates if available, otherwise original
                pred_coords = (item.x_pdf_edited, item.y_pdf_edited)
                gt_coords = (item.x_pdf, item.y_pdf)
                localization_pairs.append((pred_coords, gt_coords))
        
        # Step 4: Compute metrics
        pr_f1_metrics = compute_pr_f1(tp, fp, fn)
        
        # Get points_per_foot from first item (assuming consistent across items)
        ppf = count_items[0].points_per_foot if count_items else 50.0
        loc_metrics = localization_stats(localization_pairs, ppf)
        
        # Step 5: Export accepted items to CSV
        accepted_items = [
            item for item in count_items 
            if item.status == CountStatus.ACCEPTED
        ]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"accepted_{timestamp}.csv"
        csv_path = settings.get_reports_dir() / csv_filename
        
        # Ensure reports directory exists
        settings.get_reports_dir().mkdir(parents=True, exist_ok=True)
        
        # Write CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'file', 'page', 'type', 'x_pdf', 'y_pdf', 'x_ft', 'y_ft', 'confidence'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in accepted_items:
                # Convert PDF coordinates to feet
                x_ft = item.x_pdf / ppf
                y_ft = item.y_pdf / ppf
                
                # Use edited coordinates if available
                x_pdf = item.x_pdf_edited if item.x_pdf_edited is not None else item.x_pdf
                y_pdf = item.y_pdf_edited if item.y_pdf_edited is not None else item.y_pdf
                
                writer.writerow({
                    'file': item.file,
                    'page': item.page,
                    'type': item.type,
                    'x_pdf': x_pdf,
                    'y_pdf': y_pdf,
                    'x_ft': x_ft,
                    'y_ft': y_ft,
                    'confidence': item.confidence
                })
        
        # Step 6: Create/update ReviewSession
        session_id = str(uuid.uuid4())
        
        # Combine all metrics
        all_metrics = {
            **pr_f1_metrics,
            **loc_metrics,
            "total_items": len(count_items),
            "accepted_items": len(accepted_items),
            "localization_pairs": len(localization_pairs),
            "threshold": commit_request.threshold
        }
        
        review_session = ReviewSessionModel(
            id=session_id,
            file=commit_request.file,
            pages=commit_request.pages,
            points_per_foot=ppf,
            metrics=all_metrics
        )
        
        db.add(review_session)
        db.commit()
        db.refresh(review_session)
        
        # Step 7: Return ReportOut
        report = ReportOut(
            n_total=len(count_items),
            n_tp=tp,
            n_fp=fp,
            n_fn=fn,
            precision=pr_f1_metrics["precision"],
            recall=pr_f1_metrics["recall"],
            f1=pr_f1_metrics["f1"],
            loc_mae_ft=loc_metrics["mae_ft"],
            loc_p95_ft=loc_metrics["p95_ft"],
            export_csv_url=f"/reports/{csv_filename}"
        )
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error committing review: {str(e)}"
        )


@router.get("/sessions", response_model=List[ReviewSession])
async def list_review_sessions(
    file: Optional[str] = Query(None, description="Filter by PDF filename"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all review sessions."""
    query = db.query(ReviewSessionModel)
    if file:
        query = query.filter(ReviewSessionModel.file == file)
    return query.all()

@router.get("/sessions/{session_id}", response_model=ReviewSession)
async def get_review_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific review session by ID."""
    session = db.query(ReviewSessionModel).filter(ReviewSessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Review session not found")
    return session

@router.post("/sessions", response_model=ReviewSession, status_code=201)
async def create_review_session(
    session_create: ReviewSessionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new review session."""
    db_session = ReviewSessionModel(**session_create.dict())
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

@router.get("/sessions/{session_id}/counts")
async def get_session_counts(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all count items for a specific review session."""
    session = db.query(ReviewSessionModel).filter(ReviewSessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Review session not found")
    
    counts = db.query(CountItemModel).filter(
        CountItemModel.file == session.file,
        CountItemModel.page.in_(session.pages)
    ).all()
    
    return {"count_items": counts, "session": session}

@router.get("/sessions/{session_id}/metrics")
async def get_session_metrics(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get metrics for a review session."""
    session = db.query(ReviewSessionModel).filter(ReviewSessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Review session not found")
    
    counts = db.query(CountItemModel).filter(
        CountItemModel.file == session.file,
        CountItemModel.page.in_(session.pages)
    ).all()
    
    # Calculate metrics if not already stored
    if not session.metrics:
        from ...utils.metrics import calculate_review_metrics
        metrics = calculate_review_metrics(counts)
        session.metrics = metrics
        db.commit()
    
    return {"session_id": session_id, "metrics": session.metrics}