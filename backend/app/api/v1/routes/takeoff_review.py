from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.app.schemas.estimai import EstimAIResult
from backend.app.services.persistence.review_writer import estimai_to_count_items, upsert_counts
# from backend.app.services.counts_repo import get_counts_repo

router = APIRouter(prefix="/v1/takeoff", tags=["takeoff"])

class ReviewIn(BaseModel):
    session_id: str
    sheet_ref: str | None = None
    payload: EstimAIResult

@router.post("/review")
def post_review(data: ReviewIn, repo = Depends(...)):  # get_counts_repo
    items = estimai_to_count_items(data.payload, sheet=data.sheet_ref)
    res = upsert_counts(data.session_id, items, repo)
    return {"ok": True, **res}
