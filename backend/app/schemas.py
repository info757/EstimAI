"""Pydantic v2 schemas for EstimAI API."""
from datetime import datetime
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, UUID4, Field
from uuid import UUID, uuid4
from .models import CountStatus

class CountItemBase(BaseModel):
    file: str
    page: int
    type: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    x_pdf: float
    y_pdf: float
    points_per_foot: float
    status: CountStatus = CountStatus.PENDING
    reviewer_note: Optional[str] = None
    x_pdf_edited: Optional[float] = None
    y_pdf_edited: Optional[float] = None
    type_edited: Optional[str] = None

class CountItemCreate(CountItemBase):
    pass

class CountItemUpdate(BaseModel):
    status: Optional[CountStatus] = None
    reviewer_note: Optional[str] = None
    x_pdf_edited: Optional[float] = None
    y_pdf_edited: Optional[float] = None
    type_edited: Optional[str] = None

class CountItemOut(BaseModel):
    """Complete count item with all fields including edited values."""
    id: UUID4
    file: str
    page: int
    type: str
    confidence: float
    x_pdf: float
    y_pdf: float
    points_per_foot: float
    status: Literal["pending", "accepted", "rejected", "edited"]
    reviewer_note: Optional[str] = None
    x_pdf_edited: Optional[float] = None
    y_pdf_edited: Optional[float] = None
    type_edited: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class CountItemPatch(BaseModel):
    """Patch schema for updating count items."""
    status: Optional[CountStatus] = None
    reviewer_note: Optional[str] = None
    type_edited: Optional[str] = None
    x_pdf_edited: Optional[float] = None
    y_pdf_edited: Optional[float] = None

class ReviewSessionBase(BaseModel):
    file: str
    pages: List[int]
    points_per_foot: float
    metrics: Optional[Dict[str, Any]] = None

class ReviewSessionCreate(ReviewSessionBase):
    pass

class ReviewSession(ReviewSessionBase):
    id: UUID4
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class CountItemBulkUpdate(BaseModel):
    items: List[CountItemUpdate]
    item_ids: List[UUID4]

class DetectionRequest(BaseModel):
    file: str
    page: int
    scale_in_equals_ft: float = 50.0

class DetectItem(BaseModel):
    """Individual detection item."""
    id: UUID4
    type: str
    x_pdf: float
    y_pdf: float
    confidence: float
    status: Literal["pending"] = "pending"

class DetectResponse(BaseModel):
    """Detection response with counts and totals."""
    file: str
    page: int
    points_per_foot: float
    counts: List[DetectItem]
    totals: Dict[str, int]

class CommitRequest(BaseModel):
    """Request to commit detections for review."""
    file: str
    pages: List[int]
    threshold: Optional[float] = None

class ReportOut(BaseModel):
    """Report output with metrics and export URL."""
    n_total: int
    n_tp: int
    n_fp: int
    n_fn: int
    precision: float
    recall: float
    f1: float
    loc_mae_ft: float
    loc_p95_ft: float
    export_csv_url: Optional[str] = None
