from pydantic import BaseModel, Field
from typing import List, Optional, Literal
class TakeoffItem(BaseModel):
    assembly_id: str
    measure_type: Literal["SF","LF","EA","CY"]
    qty: float
    unit: str
    confidence: float = Field(ge=0, le=1)
    evidence_uri: Optional[str] = None
    sheet_id: Optional[str] = None
class TakeoffOutput(BaseModel):
    project_id: str
    items: List[TakeoffItem]
    notes: Optional[str] = None
class ScopeBlock(BaseModel):
    trade: str
    inclusions: List[str]
    exclusions: List[str]
    clarifications: List[str]
class ScopeOutput(BaseModel):
    project_id: str
    scopes: List[ScopeBlock]
class QuoteLine(BaseModel):
    assembly_id: str
    price: float
    included: bool
class LevelingResult(BaseModel):
    project_id: str
    subcontractor: str
    compliance_score: int
    includes: List[str]
    excludes: List[str]
    normalized: List[QuoteLine]
class RiskItem(BaseModel):
    category: str
    description: str
    probability: float
    impact_days: int
    impact_cost_pct: float
    mitigation: str
class RiskOutput(BaseModel):
    project_id: str
    risks: List[RiskItem]
class WBSItem(BaseModel):
    name: str
    csi_code: str
    qty: float
    unit: str
    unit_cost: float
    total: float
