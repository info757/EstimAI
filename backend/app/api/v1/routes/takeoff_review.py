from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.schemas_estimai import EstimAIResult
from backend.app.services.persistence.review_writer import estimai_to_count_items, upsert_counts
from backend.app.db import get_db

router = APIRouter(prefix="/v1/takeoff", tags=["takeoff"])

class ReviewIn(BaseModel):
    session_id: str
    sheet_ref: str | None = None
    payload: EstimAIResult

@router.post("/review")
def post_review(data: ReviewIn, db: Session = Depends(get_db)):
    items = estimai_to_count_items(data.payload, sheet=data.sheet_ref)
    upsert_counts(data.session_id, items, db)
    return {"ok": True, "message": f"Review completed - {len(items)} items processed"}
