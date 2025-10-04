from __future__ import annotations
from typing import Optional, List, Dict, Literal, Any
from pydantic import BaseModel, Field

Units = Literal["ft", "m"]

class Node(BaseModel):
    id: str
    kind: Literal["inlet","junction","manhole","hydrant","valve","unknown"] = "unknown"
    x: float
    y: float
    attrs: Dict[str, float | int | str | bool] = Field(default_factory=dict)

class Pipe(BaseModel):
    id: str
    from_id: str
    to_id: str
    length_ft: float
    dia_in: Optional[float] = None
    mat: Optional[str] = None
    slope: Optional[float] = None  # fraction (e.g., 0.006)
    avg_depth_ft: Optional[float] = None
    extra: Optional[Dict[str, Any]] = None

class StormNetwork(BaseModel):
    pipes: List[Pipe] = Field(default_factory=list)
    structures: List[Node] = Field(default_factory=list)

class SanitaryNetwork(BaseModel):
    pipes: List[Pipe] = Field(default_factory=list)
    manholes: List[Node] = Field(default_factory=list)

class WaterNetwork(BaseModel):
    pipes: List[Pipe] = Field(default_factory=list)
    hydrants: List[Node] = Field(default_factory=list)
    valves: List[Node] = Field(default_factory=list)

class Roadway(BaseModel):
    curb_lf: float = 0.0
    sidewalk_sf: float = 0.0

class ESC(BaseModel):
    silt_fence_lf: float = 0.0
    inlet_protection_ea: int = 0
    entrances: List[Dict[str, float]] = Field(default_factory=list)

class Earthwork(BaseModel):
    cut_cy: Optional[float] = None
    fill_cy: Optional[float] = None
    undercut_cy: Optional[float] = None
    source: Literal["table","calc","unknown"] = "unknown"

class QAFlag(BaseModel):
    code: str
    message: str
    geom_id: Optional[str] = None
    sheet_ref: Optional[str] = None

class EstimAIResult(BaseModel):
    sheet_units: Units = "ft"
    scale: Optional[str] = None
    networks: Dict[str, object] = Field(default_factory=dict)  # storm/sanitary/water objects
    roadway: Roadway = Roadway()
    e_sc: ESC = ESC()
    earthwork: Earthwork = Earthwork()
    qa_flags: List[QAFlag] = Field(default_factory=list)
