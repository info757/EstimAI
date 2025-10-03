from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.app.schemas_estimai import EstimAIResult
from backend.app.services.persistence.review_writer import estimai_to_count_items, upsert_counts
# from backend.app.services.counts_repo import get_counts_repo

router = APIRouter(prefix="/v1/takeoff", tags=["takeoff"])

class ReviewIn(BaseModel):
    session_id: str
    sheet_ref: str | None = None
    payload: EstimAIResult

@router.post("/review")
def post_review(data: ReviewIn):  # TODO: Add repo dependency when available
    items = estimai_to_count_items(data.payload, sheet=data.sheet_ref)
    # TODO: Implement upsert_counts when repo is available
    # res = upsert_counts(data.session_id, items, repo)
    return {"ok": True, "message": "Review endpoint ready - repo integration pending"}
