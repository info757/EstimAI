from __future__ import annotations
from typing import Optional
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union
from .extract import PageDraw
from .classify import classify_areas
from .geom import snap_lines, merge_lines
from .scale import _color_close

BLACK = (0.0, 0.0, 0.0)

def curb_length_lf_from_pavement(px: PageDraw, ft_per_unit: float) -> Optional[float]:
    areas = classify_areas(px)
    polys = []
    for ring in areas["pavement"]:
        pts = ring if ring[0] == ring[-1] else (ring + [ring[0]])
        poly = Polygon(pts)
        if poly.is_valid and poly.area > 0:
            polys.append(poly)
    if not polys:
        return None
    merged = unary_union(polys)
    return merged.length * ft_per_unit

def curb_length_lf_from_strokes(px: PageDraw, ft_per_unit: float, min_width: float = 1.5) -> Optional[float]:
    raw = []
    for ln in px.lines:
        if _color_close(ln.stroke, BLACK, tol=30/255.0) and ln.width >= min_width:
            ls = LineString([ln.p1, ln.p2])
            
            # Exclude scale bar: horizontal, near bottom, 50-150 ft length
            length_ft = ls.length * ft_per_unit
            y_avg = (ln.p1[1] + ln.p2[1]) / 2
            is_horizontal = abs(ln.p2[1] - ln.p1[1]) < 5.0
            is_near_bottom = y_avg > 500
            is_scale_bar_length = 50 <= length_ft <= 150
            
            if is_horizontal and is_near_bottom and is_scale_bar_length:
                continue
            
            raw.append(ls)
    
    if not raw:
        return None
    merged = merge_lines(snap_lines(raw, tol=0.5))
    return sum(ls.length for ls in merged) * ft_per_unit

def curb_length_lf(px: PageDraw, ft_per_unit: float) -> float:
    # 1) Explicit curb strokes
    v = curb_length_lf_from_strokes(px, ft_per_unit, min_width=1.5)
    if v is not None:
        return v
    # 2) Pavement perimeter
    v = curb_length_lf_from_pavement(px, ft_per_unit)
    if v is not None:
        return v
    # 3) Relaxed stroke fallback (any black)
    raw = [LineString([ln.p1, ln.p2]) for ln in px.lines if _color_close(ln.stroke, BLACK, tol=30/255.0)]
    if not raw:
        return 0.0
    merged = merge_lines(snap_lines(raw, tol=0.5))
    return sum(ls.length for ls in merged) * ft_per_unit
