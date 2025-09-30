from __future__ import annotations
from typing import Optional, Tuple
import math, re
from .extract import PageDraw

BLACK = (0.0, 0.0, 0.0)

def _color_close(c, t, tol=30/255.0):
    return c and all(abs(ci - ti) <= tol for ci, ti in zip(c, t))

def _center(b: Tuple[float,float,float,float]) -> Tuple[float,float]:
    x0,y0,x1,y1 = b
    return ((x0+x1)/2.0, (y0+y1)/2.0)

def detect_scale_bar_ft_per_unit(px: PageDraw,
                                 min_len=120.0,
                                 max_len=600.0,
                                 horiz_eps=1.0,
                                 min_width=2.0) -> Optional[float]:
    # 1) Anchor to "Scale" text and parse feet label nearby (e.g., 100 ft)
    scale_spans = [t for t in px.texts if "scale" in t.text.lower()]
    ft_label = None
    anchor_xy = None
    if scale_spans:
        scale_spans.sort(key=lambda s: (s.bbox[1], s.bbox[0]))  # lowest/leftmost
        anchor_xy = _center(scale_spans[0].bbox)
        nearby = sorted(px.texts, key=lambda s: (_center(s.bbox)[0]-anchor_xy[0])**2 + (_center(s.bbox)[1]-anchor_xy[1])**2)[:12]
        for s in nearby:
            m = re.search(r"(\d+(?:\.\d+)?)\s*ft\b", s.text.lower())
            if m:
                ft_label = float(m.group(1)); break

    # 2) Prefer bottom-left quadrant (legend region)
    if px.lines:
        xs = [p for ln in px.lines for p in (ln.p1[0], ln.p2[0])]
        ys = [p for ln in px.lines for p in (ln.p1[1], ln.p2[1])]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        region = (x_min, y_min, x_min + 0.5*(x_max-x_min), y_min + 0.5*(y_max-y_min))
    else:
        region = None

    # 3) Candidate lines: thick black, near-horizontal, bounded length
    candidates = []
    for ln in px.lines:
        if not _color_close(ln.stroke, BLACK): 
            continue
        if ln.width < min_width:
            continue
        (x0,y0),(x1,y1) = ln.p1, ln.p2
        if abs(y1 - y0) > horiz_eps:
            continue
        length_units = math.hypot(x1-x0, y1-y0)
        if not (min_len <= length_units <= max_len):
            continue
        midx, midy = 0.5*(x0+x1), 0.5*(y0+y1)
        dist2_anchor = ((midx - anchor_xy[0])**2 + (midy - anchor_xy[1])**2) if anchor_xy else 0.0
        in_region = 0
        if region:
            rx0, ry0, rx1, ry1 = region
            in_region = 1 if (rx0 <= midx <= rx1 and ry0 <= midy <= ry1) else 0
        score = (dist2_anchor, -in_region, -length_units)  # lower is better
        candidates.append((score, length_units))

    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0])
    best_len_units = candidates[0][1]
    if ft_label is None:
        ft_label = 100.0
    return ft_label / best_len_units
