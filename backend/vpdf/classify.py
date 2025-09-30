from __future__ import annotations
from typing import Dict, List, Tuple
from shapely.geometry import LineString
from .extract import PageDraw
from .config import load_config, nearest_color

def classify_lines(px: PageDraw, config_path: str | None = None):
    cfg, palette = load_config(config_path)
    tol = cfg["tolerances"]["color"]
    sanitary, storm, water, curb = [], [], [], []
    
    for ln in px.lines:
        if not ln.stroke: 
            continue
        name, dist = nearest_color(ln.stroke, {
            "sanitary": palette["sanitary"],
            "storm": palette["storm"],
            "water": palette["water"],
            "curb": palette["curb"],
        })
        if dist > tol:
            continue
        ls = LineString([ln.p1, ln.p2])
        if name == "sanitary": sanitary.append(ls)
        elif name == "storm":  storm.append(ls)
        elif name == "water":  water.append(ls)
        elif name == "curb":   curb.append(ls)
    
    return {"sanitary": sanitary, "storm": storm, "water": water, "curb": curb}

def classify_areas(px: PageDraw, config_path: str | None = None) -> Dict[str, List[List[Tuple[float, float]]]]:
    cfg, palette = load_config(config_path)
    tol = cfg["tolerances"]["color"]
    building_rings, pavement_rings, sidewalk_rings = [], [], []
    
    for rect in px.filled_rects:
        if not rect.fill: 
            continue
        name, dist = nearest_color(rect.fill, {
            "building_fill": palette["building_fill"],
            "pavement_fill": palette["pavement_fill"],
        })
        if dist > tol:
            continue
        
        # Close the ring
        ring = rect.points + [rect.points[0]]
        
        if name == "building_fill":
            building_rings.append(ring)
        elif name == "pavement_fill":
            pavement_rings.append(ring)
    
    return {"building": building_rings, "pavement": pavement_rings, "sidewalk": sidewalk_rings}
