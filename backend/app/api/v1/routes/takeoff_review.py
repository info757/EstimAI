from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from backend.app.schemas_estimai import EstimAIResult
from backend.app.services.persistence.review_writer import estimai_to_count_items, upsert_counts
# Lazy import - moved to function level to avoid circular imports

router = APIRouter(prefix="/v1/takeoff", tags=["takeoff"])

class ReviewIn(BaseModel):
    session_id: str
    sheet_ref: Optional[str] = None
    payload: EstimAIResult

@router.post("/review")
def post_review(data: ReviewIn):
    # Lazy import to avoid circular dependencies
    from backend.app.db import get_db
    from backend.app.db import SessionLocal
    
    # Get database session
    db = SessionLocal()
    
    try:
        items = estimai_to_count_items(data.payload, sheet=data.sheet_ref)
        upsert_counts(data.session_id, items, db)
        return {"ok": True, "message": f"Review completed - {len(items)} items processed"}
    finally:
        db.close()
