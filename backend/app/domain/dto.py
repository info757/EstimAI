from pydantic import BaseModel
from typing import Literal, List, Optional, Tuple

Pt = Tuple[float, float]

class TextToken(BaseModel):
    text: str
    x: float; y: float; width: float; height: float
    rotation_deg: float = 0.0
    page_index: int

class VectorPath(BaseModel):
    kind: Literal["line","polyline","bezier","rect","circle","arc"] = "polyline"
    points: List[Pt]
    stroke_rgb: Optional[Tuple[int,int,int]] = None
    stroke_width: Optional[float] = None
    layer_hint: Optional[str] = None
    page_index: int

class PageVectors(BaseModel):
    page_index: int
    width_pt: float; height_pt: float
    paths: List[VectorPath]
    texts: List[TextToken]
