from __future__ import annotations
from typing import Any, Dict, Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator

Units = Literal["ft", "m"]

class Node(BaseModel):
    id: str
    kind: Literal["inlet","junction","manhole","hydrant","valve","unknown"] = "unknown"
    x: float
    y: float
    attrs: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(extra='ignore')

class Pipe(BaseModel):
    id: str
    from_id: str
    to_id: str
    length_ft: float
    dia_in: Optional[float] = None
    mat: Optional[str] = None
    slope: Optional[float] = None        # fraction (0.006), not percent
    avg_depth_ft: Optional[float] = None
    extra: Dict[str, Any] = Field(default_factory=dict)  # <— depth/trench lives here

    model_config = ConfigDict(extra='ignore')  # <— don't explode on new keys

class StormNetwork(BaseModel):
    pipes: List[Pipe] = Field(default_factory=list)
    structures: List[Node] = Field(default_factory=list)
    
    model_config = ConfigDict(extra='ignore')

class SanitaryNetwork(BaseModel):
    pipes: List[Pipe] = Field(default_factory=list)
    manholes: List[Node] = Field(default_factory=list)
    
    model_config = ConfigDict(extra='ignore')

class WaterNetwork(BaseModel):
    pipes: List[Pipe] = Field(default_factory=list)
    hydrants: List[Node] = Field(default_factory=list)
    valves: List[Node] = Field(default_factory=list)
    
    model_config = ConfigDict(extra='ignore')

class Roadway(BaseModel):
    curb_lf: float = 0.0
    sidewalk_sf: float = 0.0
    
    model_config = ConfigDict(extra='ignore')

class ESC(BaseModel):
    silt_fence_lf: float = 0.0
    inlet_protection_ea: int = 0
    entrances: List[Dict[str, float]] = Field(default_factory=list)
    
    model_config = ConfigDict(extra='ignore')

class Earthwork(BaseModel):
    cut_cy: Optional[float] = None
    fill_cy: Optional[float] = None
    undercut_cy: Optional[float] = None
    source: Literal["table","calc","unknown"] = "unknown"
    
    model_config = ConfigDict(extra='ignore')

class QAFlag(BaseModel):
    code: str
    message: str
    geom_id: Optional[str] = None
    sheet_ref: Optional[str] = None
    
    model_config = ConfigDict(extra='ignore')

class Networks(BaseModel):
    storm: Optional[StormNetwork] = None
    sanitary: Optional[SanitaryNetwork] = None
    water: Optional[WaterNetwork] = None
    model_config = ConfigDict(extra='ignore')

class EstimAIResult(BaseModel):
    sheet_units: Literal["ft", "m"] = "ft"
    scale: Optional[str] = None
    networks: Networks = Field(default_factory=Networks)   # <— explicit model, not Dict[str, object]
    roadway: Roadway = Roadway()
    e_sc: ESC = ESC()
    earthwork: Earthwork = Earthwork()
    qa_flags: List[QAFlag] = Field(default_factory=list)
    model_config = ConfigDict(extra='ignore', populate_by_name=True)

    # IMPORTANT: delete any old validator named coerce_networks; it causes this bug.
    # If you still want a guard, use this 'before' validator that preserves dict input:
    @field_validator("networks", mode="before")
    @classmethod
    def _accept_dict_or_model(cls, v):
        # Accept raw dicts like {"sanitary": {...}} and let Pydantic build Networks
        if isinstance(v, dict):
            return v
        return v
