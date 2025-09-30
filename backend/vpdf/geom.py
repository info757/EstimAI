from __future__ import annotations
from typing import List
import numpy as np
from shapely.geometry import LineString
from shapely.ops import linemerge, unary_union

def snap_lines(lines: List[LineString], tol: float) -> List[LineString]:
    """Snap line endpoints to a grid with given tolerance."""
    snapped = []
    for ls in lines:
        coords = np.array(ls.coords, dtype=float)
        # Round to nearest tol
        coords = np.round(coords / tol) * tol
        snapped.append(LineString(coords))
    return snapped

def merge_lines(lines: List[LineString]) -> List[LineString]:
    """Merge connected and overlapping lines."""
    if not lines:
        return []
    merged = linemerge(unary_union(lines))
    if isinstance(merged, LineString):
        return [merged]
    return list(merged.geoms)

