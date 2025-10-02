from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Tuple
import os, math

from app.services.ingest import get_ingestor
from app.domain.dto import PageVectors, VectorPath, TextToken

router = APIRouter(prefix="/v1")

FILES_DIR = os.getenv("FILES_DIR","./files")

class TakeoffFeature(BaseModel):
    id: str
    page_index: int
    points: List[Tuple[float,float]]
    dia_in: int | None = None
    material: str | None = None
    length_ft: float
    confidence: float

class TakeoffResult(BaseModel):
    features: List[TakeoffFeature]
    rollup: Dict[str, float]  # e.g., {"water:LF:DIP:8": 1234.5}

def _points_per_foot_from_scale(scale_in_to_ft: float) -> float:
    # e.g., 1in = 50ft  =>  points_per_foot = 72 / 50
    return 72.0 / scale_in_to_ft

def _length_ft(points: List[Tuple[float,float]], ppf: float) -> float:
    total_pt = 0.0
    for i in range(1, len(points)):
        dx = points[i][0] - points[i-1][0]
        dy = points[i][1] - points[i-1][1]
        total_pt += math.hypot(dx, dy)
    return total_pt / ppf if ppf > 0 else 0.0

def _nearby_tokens(line_pts: List[Tuple[float,float]], tokens: List[TextToken], dist_pt: float=40.0) -> List[TextToken]:
    # check labels within 'dist_pt' of the line midpoint
    if not line_pts: return []
    mid = line_pts[len(line_pts)//2]
    out = []
    for t in tokens:
        cx = t.x + t.width/2; cy = t.y + t.height/2
        if math.hypot(cx - mid[0], cy - mid[1]) <= dist_pt:
            out.append(t)
    return out

def _parse_dia_material(text: str) -> Tuple[int | None, str | None]:
    # crude regex-free MVP
    dia = None; mat = None
    s = text.upper().replace("INCH","\"")
    for k in ["4","6","8","10","12","16","20","24","30","36"]:
        if k + "\"" in s or f"{k}" in s:  # handle smart quote
            dia = int(k); break
    for m in ["DIP","PVC","CL50","PC350","RCP","FM"]:
        if m in s:
            mat = m; break
    return dia, mat

def _is_probably_water(path: VectorPath, tokens: List[TextToken]) -> bool:
    # MVP heuristic: blue-ish stroke OR nearby text mentions DIP/PVC without MH/CB
    blueish = False
    if path.stroke_rgb:
        r,g,b = path.stroke_rgb
        blueish = (b > g and b > r and b > 80)
    near = _nearby_tokens(path.points, tokens, dist_pt=60.0)
    txt = " ".join(t.text for t in near).upper()
    label_water = any(x in txt for x in ["DIP","PVC"]) and not any(x in txt for x in ["MH","CB"])
    return blueish or label_water

@router.get("/run/water", response_model=TakeoffResult)
def run_water_takeoff(
    name: str = Query(..., description="PDF file name in /files"),
    page: int = Query(0),
    scale_in_equals_ft: float = Query(50.0, description="Scale like 1in=50ft -> pass 50")
):
    path = os.path.join(FILES_DIR, name)
    if not os.path.isfile(path):
        raise HTTPException(404, "file not found")
    ing = get_ingestor()
    pv: PageVectors = ing.read_page(path, page)

    ppf = _points_per_foot_from_scale(scale_in_equals_ft)

    feats: List[TakeoffFeature] = []
    roll: Dict[str, float] = {}

    # classify lines
    for i, p in enumerate(pv.paths):
        if len(p.points) < 2: continue
        if not _is_probably_water(p, pv.texts): continue

        # infer dia/material from nearby tokens
        dia, material = None, None
        near = _nearby_tokens(p.points, pv.texts, dist_pt=80.0)
        for t in near:
            d,m = _parse_dia_material(t.text)
            dia = dia or d
            material = material or m
            if dia and material: break

        length_ft = round(_length_ft(p.points, ppf), 2)
        conf = 0.6 + (0.2 if material else 0.0) + (0.2 if dia else 0.0)

        feat = TakeoffFeature(
            id=f"W-{page}-{i}",
            page_index=page,
            points=p.points,
            dia_in=dia,
            material=material,
            length_ft=length_ft,
            confidence=min(conf, 0.95)
        )
        feats.append(feat)

        # rollup key
        k = f"water:LF:{material or 'UNK'}:{dia or 0}"
        roll[k] = round(roll.get(k, 0.0) + length_ft, 2)

    return TakeoffResult(features=feats, rollup=roll)
