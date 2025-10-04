"""
Debug validation endpoint for testing EstimAIResult schema.

This endpoint helps isolate schema validation issues from route logic.
"""
from fastapi import APIRouter
from pydantic import ValidationError
from backend.app.schemas_estimai import EstimAIResult

router = APIRouter(prefix="/v1/debug", tags=["debug"])

@router.post("/validate-estimai")
def validate_estimai(payload: dict):
    """
    Validate a payload against EstimAIResult schema.
    
    Returns:
        - ok: True if validation succeeds, False if it fails
        - normalized: the validated and normalized model data (if ok)
        - errors: validation errors (if not ok)
    """
    try:
        model = EstimAIResult.model_validate(payload)
        # round-trip to ensure it can serialize
        return {"ok": True, "normalized": model.model_dump()}
    except ValidationError as e:
        return {"ok": False, "errors": e.errors()}
