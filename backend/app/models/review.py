"""
Review endpoint models for HITL overrides.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# Type alias for row identifiers
RowId = str


class Patch(BaseModel):
    """A single field patch for a row."""
    id: RowId = Field(..., description="Row identifier")
    fields: Dict[str, Any] = Field(..., description="Fields to override")
    by: str = Field(..., description="Who made the override")
    reason: Optional[str] = Field(None, description="Reason for the override")
    at: datetime = Field(default_factory=datetime.now, description="When the override was made")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "row-001",
                "fields": {"qty": 42, "unit": "LF", "desc": "Edited desc"},
                "by": "will",
                "reason": "field verification",
                "at": "2025-09-02T12:00:00Z"
            }
        }


class PatchRequest(BaseModel):
    """Request to apply multiple patches."""
    patches: List[Patch] = Field(..., description="List of patches to apply")
    
    class Config:
        json_schema_extra = {
            "example": {
                "patches": [
                    {
                        "id": "row-001",
                        "fields": {"qty": 42, "unit": "LF", "desc": "Edited desc"},
                        "by": "will",
                        "reason": "field verification",
                        "at": "2025-09-02T12:00:00Z"
                    }
                ]
            }
        }


class ReviewRow(BaseModel):
    """A row in review with AI, override, and merged data."""
    id: RowId = Field(..., description="Row identifier")
    ai: Dict[str, Any] = Field(..., description="Original AI-generated fields")
    override: Optional[Dict[str, Any]] = Field(None, description="Override fields if any")
    merged: Dict[str, Any] = Field(..., description="AI ⊕ override merged result")
    confidence: Optional[float] = Field(None, description="AI confidence score if available")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "row-001",
                "ai": {
                    "description": "Concrete foundation",
                    "qty": 100,
                    "unit": "LF",
                    "confidence": 0.85
                },
                "override": {
                    "qty": 150,
                    "unit": "LF"
                },
                "merged": {
                    "description": "Concrete foundation",
                    "qty": 150,
                    "unit": "LF",
                    "confidence": 0.85
                },
                "confidence": 0.85
            }
        }


class ReviewResponse(BaseModel):
    """Response containing review data for a stage."""
    project_id: str = Field(..., description="Project identifier")
    stage: str = Field(..., description="Stage name (takeoff, estimate, etc.)")
    rows: List[ReviewRow] = Field(..., description="Review rows with AI, override, and merged data")
    total_rows: int = Field(..., description="Total number of rows")
    overridden_rows: int = Field(..., description="Number of rows with overrides")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "demo",
                "stage": "takeoff",
                "rows": [
                    {
                        "id": "row-001",
                        "ai": {
                            "description": "Concrete foundation",
                            "qty": 100,
                            "unit": "LF",
                            "confidence": 0.85
                        },
                        "override": {
                            "qty": 150,
                            "unit": "LF"
                        },
                        "merged": {
                            "description": "Concrete foundation",
                            "qty": 150,
                            "unit": "LF",
                            "confidence": 0.85
                        },
                        "confidence": 0.85
                    },
                    {
                        "id": "row-002",
                        "ai": {
                            "description": "Steel beams",
                            "qty": 25,
                            "unit": "EA",
                            "confidence": 0.92
                        },
                        "override": None,
                        "merged": {
                            "description": "Steel beams",
                            "qty": 25,
                            "unit": "EA",
                            "confidence": 0.92
                        },
                        "confidence": 0.92
                    }
                ],
                "total_rows": 2,
                "overridden_rows": 1
            }
        }


class PatchResponse(BaseModel):
    """Response from applying patches."""
    ok: bool = Field(..., description="Success status")
    patched: int = Field(..., description="Number of patches applied")
    project_id: str = Field(..., description="Project identifier")
    stage: str = Field(..., description="Stage name")
    message: str = Field(..., description="Human-readable message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ok": True,
                "patched": 1,
                "project_id": "demo",
                "stage": "takeoff",
                "message": "Successfully applied 1 patches to takeoff data"
            }
        }
