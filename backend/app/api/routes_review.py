"""
Review endpoints for HITL overrides.
"""

import logging
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Path, Depends
from fastapi.responses import JSONResponse

from ..models.review import (
    ReviewResponse, ReviewRow, PatchRequest, PatchResponse, Patch
)
from ..services.overrides import load_overrides, save_overrides, apply_overrides
from ..services.pipeline import latest_stage_rows
from ..core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/projects/{pid}/review/takeoff", response_model=ReviewResponse)
async def get_takeoff_review(
    pid: str = Path(..., description="Project ID"),
    current_user: dict = Depends(get_current_user)
) -> ReviewResponse:
    """
    Get takeoff data for review with AI, override, and merged fields.
    
    Returns each row with:
    - ai: Original AI-generated fields
    - override: Override fields (if any)
    - merged: AI ⊕ override result
    - confidence: AI confidence score (if available)
    
    **Override Behavior:**
    - Last write wins for duplicate field patches
    - Provenance fields (by, reason, at) are stored with each patch
    - Overrides are applied in real-time to show merged results
    """
    try:
        # Load base rows and overrides
        base_rows = latest_stage_rows(pid, "takeoff")
        overrides = load_overrides(pid, "takeoff")
        
        # Create override lookup
        override_lookup = {patch["id"]: patch["fields"] for patch in overrides}
        
        # Build review rows
        review_rows = []
        overridden_count = 0
        
        for row in base_rows:
            row_id = row.get("id", "unknown")
            override_fields = override_lookup.get(row_id)
            
            if override_fields:
                overridden_count += 1
            
            # Create merged row (AI + override)
            merged_row = row.copy()
            if override_fields:
                merged_row.update(override_fields)
            
            review_row = ReviewRow(
                id=row_id,
                ai=row,
                override=override_fields,
                merged=merged_row,
                confidence=row.get("confidence")
            )
            review_rows.append(review_row)
        
        logger.info(f"GET /review/takeoff for {pid}: {len(review_rows)} rows, {overridden_count} overridden")
        
        return ReviewResponse(
            project_id=pid,
            stage="takeoff",
            rows=review_rows,
            total_rows=len(review_rows),
            overridden_rows=overridden_count
        )
        
    except Exception as e:
        logger.error(f"Error in get_takeoff_review for {pid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load takeoff review: {str(e)}")


@router.patch("/projects/{pid}/review/takeoff", response_model=PatchResponse)
async def patch_takeoff_review(
    request: PatchRequest,
    pid: str = Path(..., description="Project ID"),
    current_user: dict = Depends(get_current_user)
) -> PatchResponse:
    """
    Apply patches to takeoff data.
    
    Accepts a list of patches with:
    - id: Row identifier
    - fields: Fields to override
    - by: Who made the override
    - reason: Reason for override (optional)
    
    **Patch Behavior:**
    - Last write wins for duplicate field patches
    - Provenance fields (by, reason, at) are stored with each patch
    - Patches are persisted to artifacts/{pid}/overrides/overrides_takeoff.json
    """
    try:
        # Convert Pydantic models to dict for overrides service
        patches = []
        for patch in request.patches:
            patches.append({
                "id": patch.id,
                "fields": patch.fields,
                "by": patch.by,
                "reason": patch.reason,
                "at": patch.at.isoformat()
            })
        
        # Save overrides
        success = save_overrides(pid, "takeoff", patches)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save overrides")
        
        # Log patch details
        patch_ids = [p["id"] for p in patches]
        first_id = patch_ids[0] if patch_ids else "none"
        last_id = patch_ids[-1] if patch_ids else "none"
        
        logger.info(f"PATCH /review/takeoff for {pid}: {len(patches)} patches, first={first_id}, last={last_id}")
        
        return PatchResponse(
            ok=True,
            patched=len(patches),
            project_id=pid,
            stage="takeoff",
            message=f"Successfully applied {len(patches)} patches to takeoff data"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in patch_takeoff_review for {pid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to apply patches: {str(e)}")


@router.get("/projects/{pid}/review/estimate", response_model=ReviewResponse)
async def get_estimate_review(
    pid: str = Path(..., description="Project ID"),
    current_user: dict = Depends(get_current_user)
) -> ReviewResponse:
    """
    Get estimate data for review with AI, override, and merged fields.
    
    Returns each row with:
    - ai: Original AI-generated fields
    - override: Override fields (if any)
    - merged: AI ⊕ override result
    - confidence: AI confidence score (if available)
    
    **Override Behavior:**
    - Last write wins for duplicate field patches
    - Provenance fields (by, reason, at) are stored with each patch
    - Overrides are applied in real-time to show merged results
    """
    try:
        # Load base rows and overrides
        base_rows = latest_stage_rows(pid, "estimate")
        overrides = load_overrides(pid, "estimate")
        
        # Create override lookup
        override_lookup = {patch["id"]: patch["fields"] for patch in overrides}
        
        # Build review rows
        review_rows = []
        overridden_count = 0
        
        for row in base_rows:
            row_id = row.get("id", "unknown")
            override_fields = override_lookup.get(row_id)
            
            if override_fields:
                overridden_count += 1
            
            # Create merged row (AI + override)
            merged_row = row.copy()
            if override_fields:
                merged_row.update(override_fields)
            
            review_row = ReviewRow(
                id=row_id,
                ai=row,
                override=override_fields,
                merged=merged_row,
                confidence=row.get("confidence")
            )
            review_rows.append(review_row)
        
        logger.info(f"GET /review/estimate for {pid}: {len(review_rows)} rows, {overridden_count} overridden")
        
        return ReviewResponse(
            project_id=pid,
            stage="estimate",
            rows=review_rows,
            total_rows=len(review_rows),
            overridden_rows=overridden_count
        )
        
    except Exception as e:
        logger.error(f"Error in get_estimate_review for {pid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load estimate review: {str(e)}")


@router.patch("/projects/{pid}/review/estimate", response_model=PatchResponse)
async def patch_estimate_review(
    request: PatchRequest,
    pid: str = Path(..., description="Project ID"),
    current_user: dict = Depends(get_current_user)
) -> PatchResponse:
    """
    Apply patches to estimate data.
    
    Accepts a list of patches with:
    - id: Row identifier
    - fields: Fields to override (unit_cost, markups, etc.)
    - by: Who made the override
    - reason: Reason for override (optional)
    
    **Patch Behavior:**
    - Last write wins for duplicate field patches
    - Provenance fields (by, reason, at) are stored with each patch
    - Patches are persisted to artifacts/{pid}/overrides/overrides_estimate.json
    """
    try:
        # Convert Pydantic models to dict for overrides service
        patches = []
        for patch in request.patches:
            patches.append({
                "id": patch.id,
                "fields": patch.fields,
                "by": patch.by,
                "reason": patch.reason,
                "at": patch.at.isoformat()
            })
        
        # Save overrides
        success = save_overrides(pid, "estimate", patches)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save overrides")
        
        # Log patch details
        patch_ids = [p["id"] for p in patches]
        first_id = patch_ids[0] if patch_ids else "none"
        last_id = patch_ids[-1] if patch_ids else "none"
        
        logger.info(f"PATCH /review/estimate for {pid}: {len(patches)} patches, first={first_id}, last={last_id}")
        
        return PatchResponse(
            ok=True,
            patched=len(patches),
            project_id=pid,
            stage="estimate",
            message=f"Successfully applied {len(patches)} patches to estimate data"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in patch_estimate_review for {pid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to apply patches: {str(e)}")
