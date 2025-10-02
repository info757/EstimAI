# backend/app/api/v1/takeoff_mvp.py
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Tuple, Optional
import os, math, re

from app.services.ingest import get_ingestor
from app.domain.dto import PageVectors, VectorPath, TextToken

router = APIRouter(prefix="/v1")
FILES_DIR = os.getenv("FILES_DIR","./files")

# ----------- Models
class FeatureLine(BaseModel):
    id: str
    kind: str                   # water|sewer|storm
    page_index: int
    points: List[Tuple[float,float]]
    dia_in: Optional[int] = None
    material: Optional[str] = None
    length_ft: float
    cover_ft_min: Optional[float] = None
    cover_ft_max: Optional[float] = None
    confidence: float

class FeaturePoint(BaseModel):
    id: str
    kind: str                   # valve|hydrant|manhole|cb
    page_index: int
    x: float; y: float
    confidence: float
    note: Optional[str] = None

class Rollup(BaseModel):
    linear_ft: Dict[str, float]     # e.g. "water:LF:DIP:8" -> 1234.5
    counts: Dict[str, int]          # e.g. "hydrant" -> 5
    volumes_cy: Dict[str, float]    # e.g. "trench:water" -> 320.2

class QAFlag(BaseModel):
    level: str          # warn|error
    code: str           # e.g. "line-unlabeled", "hydrant-no-valve"
    message: str
    feature_id: Optional[str] = None

class TakeoffMVPOut(BaseModel):
    lines: List[FeatureLine]
    points: List[FeaturePoint]
    rollup: Rollup
    qa: List[QAFlag]

# ----------- helpers
DIA_RX = re.compile(r'(?<!\d)(4|6|8|10|12|16|20|24|30|36)\s*[″"]')
MAT_TOKENS = ["DIP","PVC","CL50","PC350","RCP","HDPE","FM"]

def _ppf_from_scale(scale_in_equals_ft: float) -> float:
    return 72.0 / max(1e-6, scale_in_equals_ft)

def _length_ft(points, ppf): 
    return sum(math.hypot(points[i][0]-points[i-1][0], points[i][1]-points[i-1][1]) for i in range(1,len(points))) / max(1e-6, ppf)

def _nearest_tokens_along(poly, tokens: List[TextToken], win_pt=120.0) -> List[TextToken]:
    # simple: compare bbox centers to poly mid
    if not poly: return []
    mid = poly[len(poly)//2]
    out=[]
    for t in tokens:
        cx=t.x+t.width/2; cy=t.y+t.height/2
        if math.hypot(cx-mid[0], cy-mid[1]) <= win_pt:
            out.append(t)
    return out

def _parse_dia_mat(txt: str) -> Tuple[Optional[int], Optional[str]]:
    s = txt.upper().replace("INCH","\"").replace("\"","\"")
    dia = None; m = DIA_RX.search(s)
    if m: dia = int(m.group(1))
    mat = None
    for tok in MAT_TOKENS:
        if tok in s: mat = tok; break
    return dia, mat

def _is_line_kind(p: VectorPath, tokens: List[TextToken]) -> Optional[str]:
    txt = " ".join(t.text for t in _nearest_tokens_along(p.points, tokens))
    s = txt.upper()
    # color hint
    k_color = None
    if p.stroke_rgb:
        r,g,b = p.stroke_rgb
        if b>r and b>g and b>80: k_color="water"
        elif g>r and g>b and g>80: k_color="sewer_or_storm"  # will refine by text
        elif r>g and r>b and r>80: k_color="storm_or_misc"

    # text hints
    if any(t in s for t in ["DIP","PVC","WATER","WL","HYDRANT"]): return "water"
    if any(t in s for t in ["SEWER","SAN","SS","MH","FM"]): return "sewer"
    if any(t in s for t in ["STORM","RCP","CB","CULVERT","DRAIN"]): return "storm"

    if k_color == "water": return "water"
    if k_color == "sewer_or_storm": 
        # try material tie-breaker
        if "RCP" in s or "CB" in s or "DRAIN" in s: return "storm"
        if "MH" in s or "SEWER" in s: return "sewer"
    return None

def _detect_points(tokens: List[TextToken]) -> List[FeaturePoint]:
    pts=[]
    for i,t in enumerate(tokens):
        s=t.text.upper()
        # Robust MVP: rely on labels; symbol matching can be added later
        if "HYDRANT" in s or "FH" in s:
            pts.append(FeaturePoint(id=f"PT-H-{i}", kind="hydrant", page_index=t.page_index, x=t.x, y=t.y, confidence=0.8))
        elif re.search(r'\bVALVE\b|\bGV\b|\bBFV\b', s):
            pts.append(FeaturePoint(id=f"PT-V-{i}", kind="valve", page_index=t.page_index, x=t.x, y=t.y, confidence=0.7))
        elif re.search(r'\bMH\b|\bMANHOLE\b', s):
            pts.append(FeaturePoint(id=f"PT-MH-{i}", kind="manhole", page_index=t.page_index, x=t.x, y=t.y, confidence=0.85))
        elif re.search(r'\bCB\b|\bCATCH BASIN\b', s):
            pts.append(FeaturePoint(id=f"PT-CB-{i}", kind="cb", page_index=t.page_index, x=t.x, y=t.y, confidence=0.8))
    return pts

INV_RX = re.compile(r'(INV[.\s]*:?)[^\d\-]*([\-]?\d{2,3}\.?\d*)', re.I)
GRD_RX = re.compile(r'(PROP\.?\s*GRADE|GRADE)[^\d\-]*([\-]?\d{2,3}\.?\d*)', re.I)
COVER_RX = re.compile(r'(MIN\.?\s*)(\d+)[\'′]?[\s-]*COVER', re.I)

def _parse_profile_cover(tokens: List[TextToken]) -> Tuple[Optional[float], Optional[float]]:
    inv=None; grd=None; mincov=None
    for t in tokens:
        s=t.text.upper()
        m = INV_RX.search(s)
        if m: inv = float(m.group(2))
        m = GRD_RX.search(s)
        if m: grd = float(m.group(2))
        m = COVER_RX.search(s)
        if m: mincov = float(m.group(2))
    if inv is not None and grd is not None:
        cov = grd - inv
        return max(cov, 0.0), max(cov, 0.0)
    if mincov is not None:
        return mincov, mincov
    return None, None

def _trench_cy(length_ft: float, dia_in: Optional[int], cover_min: Optional[float], cover_max: Optional[float]) -> float:
    # Simple MVP trench template: width = max(2.0, 0.5 + dia_in/12 + 1.0 bedding)
    if length_ft <= 0: return 0.0
    dia_ft = (dia_in or 8)/12.0
    depth_ft = (cover_max or cover_min or 4.0) + dia_ft/2 + 0.5  # cover + radius + bedding 0.5
    width_ft = max(2.0, 0.5 + dia_ft + 0.5)
    return (length_ft * width_ft * depth_ft) / 27.0  # cuft -> CY
# -----------

@router.get("/run/mvp", response_model=TakeoffMVPOut)
def run_mvp(
    name: str = Query(..., description="PDF file in /files"),
    page: int = Query(0),
    scale_in_equals_ft: float = Query(50.0)
):
    path = os.path.join(FILES_DIR, name)
    if not os.path.isfile(path):
        raise HTTPException(404, "file not found")

    ing = get_ingestor()
    pv: PageVectors = ing.read_page(path, page)
    ppf = _ppf_from_scale(scale_in_equals_ft)

    lines: List[FeatureLine] = []
    qa: List[QAFlag] = []

    # classify polylines and label dia/material
    for i, p in enumerate(pv.paths):
        if len(p.points) < 2: continue
        kind = _is_line_kind(p, pv.texts)
        if not kind: continue

        near = _nearest_tokens_along(p.points, pv.texts, 140.0)
        dia, mat = None, None
        for t in near:
            d, m = _parse_dia_mat(t.text)
            dia = dia or d; mat = mat or m
            if dia and mat: break

        length_ft = round(_length_ft(p.points, ppf), 2)
        cov_min, cov_max = _parse_profile_cover(near)  # use nearby profile labels first (MVP)
        conf = 0.55 + (0.15 if mat else 0.0) + (0.15 if dia else 0.0) + (0.15 if length_ft>0 else 0.0)

        fid = f"{kind.upper()}-{page}-{i}"
        lines.append(FeatureLine(
            id=fid, kind=kind, page_index=page, points=p.points,
            dia_in=dia, material=mat, length_ft=length_ft,
            cover_ft_min=cov_min, cover_ft_max=cov_max, confidence=min(conf,0.97)
        ))

        if dia is None:
            qa.append(QAFlag(level="warn", code="line-unlabeled-dia", message="Missing diameter", feature_id=fid))
        if mat is None:
            qa.append(QAFlag(level="warn", code="line-unlabeled-mat", message="Missing material", feature_id=fid))

    # detect points by label (robust for MVP)
    points = _detect_points(pv.texts)

    # rollups
    lf: Dict[str, float] = {}
    counts: Dict[str, int] = {}
    vols: Dict[str, float] = {}

    for L in lines:
        k = f"{L.kind}:LF:{(L.material or 'UNK')}:{(L.dia_in or 0)}"
        lf[k] = round(lf.get(k,0.0) + L.length_ft, 2)
        # rough trench volume per kind
        vkey = f"trench:{L.kind}"
        vols[vkey] = round(vols.get(vkey,0.0) + _trench_cy(L.length_ft, L.dia_in, L.cover_ft_min, L.cover_ft_max), 2)

    for P in points:
        counts[P.kind] = counts.get(P.kind, 0) + 1

    # simple QA: hydrant should be near a water line and a valve
    if counts.get("hydrant"):
        if not any(l.kind=="water" for l in lines):
            qa.append(QAFlag(level="warn", code="hydrant-no-water", message="Hydrant(s) found but no water line detected"))

    return TakeoffMVPOut(
        lines=lines,
        points=points,
        rollup=Rollup(linear_ft=lf, counts=counts, volumes_cy=vols),
        qa=qa
    )
