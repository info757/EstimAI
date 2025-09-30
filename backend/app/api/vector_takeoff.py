from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel
import tempfile, shutil
from typing import List, Optional, Literal, Dict, Any

from vpdf.extract import extract_lines
from vpdf.scale import detect_scale_bar_ft_per_unit
from vpdf.measure import curb_length_lf
from vpdf.classify import classify_lines, classify_areas
from vpdf.config import load_config

router = APIRouter(prefix="/takeoff", tags=["takeoff"])

class OverlayPolyline(BaseModel):
    polyline: List[List[float]]  # [[x,y], ...] in page space
    kind: Literal["curb","sanitary","storm","water"]

class OverlayPolygon(BaseModel):
    polygon: List[List[float]]   # [[x,y], ...] closed ring
    kind: Literal["pavement","building"]

class OverlayPoint(BaseModel):
    x: float
    y: float
    kind: Literal["mh","inlet","hydrant"]
    depth_ft: Optional[float] = None

class Diagnostics(BaseModel):
    ft_per_unit: float
    scale_source: Literal["scale_bar","manual","dimension","unknown"]
    tolerances: Dict[str, Any]
    notes: Optional[str] = None

class Quantities(BaseModel):
    building_area_sf: float = 0.0
    pavement_area_sf: float = 0.0
    sidewalk_area_sf: float = 0.0
    curb_length_lf: float = 0.0
    sanitary_len_lf: float = 0.0
    storm_len_lf: float = 0.0
    water_len_lf: float = 0.0
    parking_stalls: int = 0

class TakeoffOK(BaseModel):
    ok: Literal[True] = True
    page_index: int
    quantities: Quantities
    diagnostics: Diagnostics
    overlays: Dict[str, List]  # "polylines": [...], "polygons": [...], "points": [...]

class TakeoffErr(BaseModel):
    ok: Literal[False] = False
    code: str
    hint: str

def _as_polyline(lines) -> List[OverlayPolyline]:
    out = []
    for ls in lines:
        out.append({"polyline": list(map(list, ls.coords)), "kind": "curb"})  # kind will be fixed by caller
    return out

@router.post("/vector", response_model=TakeoffOK | TakeoffErr)
async def takeoff_vector(
    file: UploadFile = File(...),
    page_index: int = Query(1, ge=0, description="0-based page index; 1 is typical Site Plan"),
    config_key: Optional[str] = Query(None),
    debug_overlays: bool = Query(True),
    manual_ft_per_unit: Optional[float] = Query(None)
):
    """
    Extract quantities from vector PDF using geometric analysis.
    
    Returns:
        TakeoffOK with quantities and overlays, or TakeoffErr if parsing fails
    """
    # 1) save file to temp
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            shutil.copyfileobj(file.file, tmp)
            pdf_path = tmp.name
    except Exception as e:
        return {"ok": False, "code": "UPLOAD_ERROR", "hint": f"{e}"}

    # 2) parse + scale
    try:
        px = extract_lines(pdf_path, page_index)
        # TODO: map config_key -> path in your DB/FS. For now just default:
        cfg, palette = load_config()

        if manual_ft_per_unit:
            ft_per_unit = float(manual_ft_per_unit)
            scale_source = "manual"
        else:
            ft_per_unit = detect_scale_bar_ft_per_unit(px)
            scale_source = "scale_bar" if ft_per_unit else "unknown"
        if not ft_per_unit:
            return {"ok": False, "code": "SCALE_NOT_FOUND", "hint": "Could not resolve scale. Click two points of a known length or select the scale bar."}

        # 3) quantities
        q = Quantities()
        # areas
        areas = classify_areas(px)
        from shapely.geometry import Polygon
        def _poly_area_sf(rings, ftpu):
            total = 0.0
            for ring in rings:
                pts = ring if ring[0] == ring[-1] else ring + [ring[0]]
                poly = Polygon(pts)
                if poly.is_valid and poly.area > 0:
                    total += poly.area * (ftpu**2)
            return total
        bldg_sf = _poly_area_sf(areas["building"], ft_per_unit)
        pave_sf = _poly_area_sf(areas["pavement"], ft_per_unit)
        q.building_area_sf = bldg_sf
        q.pavement_area_sf = max(0.0, pave_sf - bldg_sf)

        # curb
        q.curb_length_lf = curb_length_lf(px, ft_per_unit)

        # utilities
        lines = classify_lines(px)  # {"sanitary":[LineString], ...}
        def _sum_len(ls_arr): return sum(ls.length for ls in ls_arr) * ft_per_unit
        q.sanitary_len_lf = _sum_len(lines["sanitary"])
        q.storm_len_lf    = _sum_len(lines["storm"])
        q.water_len_lf    = _sum_len(lines["water"])
        # parking_stalls: leave 0 for now unless you implemented ticks

        # 4) overlays (optional)
        overlays = {"polylines": [], "polygons": [], "points": []}
        if debug_overlays:
            # polylines
            def _polyline_dump(arr, kind):
                return [{"polyline": list(map(list, ls.coords)), "kind": kind} for ls in arr]
            overlays["polylines"].extend(_polyline_dump(lines["sanitary"], "sanitary"))
            overlays["polylines"].extend(_polyline_dump(lines["storm"], "storm"))
            overlays["polylines"].extend(_polyline_dump(lines["water"], "water"))
            # curb polyline approximation: we don't recompute, just export fused areas perimeter via pavement if present
            # polygons (areas)
            def _poly_dump(rings, kind):
                out = []
                for ring in rings:
                    pts = ring if ring[0] == ring[-1] else ring + [ring[0]]
                    out.append({"polygon": [list(p) for p in pts], "kind": kind})
                return out
            overlays["polygons"].extend(_poly_dump(areas["pavement"], "pavement"))
            overlays["polygons"].extend(_poly_dump(areas["building"], "building"))

        # 5) diagnostics
        diag = Diagnostics(
            ft_per_unit=ft_per_unit,
            scale_source=scale_source, 
            tolerances=cfg["tolerances"],
            notes=None
        )

        return {
            "ok": True,
            "page_index": page_index,
            "quantities": q,
            "diagnostics": diag,
            "overlays": overlays
        }
    except Exception as e:
        return {"ok": False, "code": "UNHANDLED", "hint": f"{e}"}

