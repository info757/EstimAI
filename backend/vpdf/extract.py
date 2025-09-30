from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import fitz  # PyMuPDF

RGB = Tuple[float,float,float]

@dataclass
class Line:
    p1: Tuple[float,float]
    p2: Tuple[float,float]
    stroke: Optional[RGB]
    width: float

@dataclass
class TextSpan:
    text: str
    bbox: Tuple[float, float, float, float]

@dataclass
class FilledRect:
    points: List[Tuple[float, float]]
    fill: Optional[RGB]

@dataclass
class PageDraw:
    lines: List[Line]
    texts: List[TextSpan]
    filled_rects: List[FilledRect]

def extract_lines(pdf_path: str, page_index: int) -> PageDraw:
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    lines: List[Line] = []
    texts: List[TextSpan] = []
    filled_rects: List[FilledRect] = []
    
    for d in page.get_drawings():
        stroke = tuple(d["color"]) if d.get("color") else None
        fill = tuple(d["fill"]) if d.get("fill") else None
        width = float(d.get("width", 0.0))
        for item in d["items"]:
            op = item[0]
            if op == "l":                # polyline segments
                # Points are in item[1:] as PyMuPDF Point objects
                points = item[1:]
                for i in range(len(points)-1):
                    p1 = (float(points[i].x), float(points[i].y))
                    p2 = (float(points[i+1].x), float(points[i+1].y))
                    lines.append(Line(p1, p2, stroke, width))
            elif op == "re":             # rectangle → 4 edges
                # Rectangle is item[1] as PyMuPDF Rect object
                rect_obj = item[1]
                x, y, w, h = rect_obj.x0, rect_obj.y0, rect_obj.width, rect_obj.height
                rect_pts = [(x,y),(x+w,y),(x+w,y+h),(x,y+h)]
                
                # If filled, add as filled rect
                if fill:
                    filled_rects.append(FilledRect(points=rect_pts, fill=fill))
                
                # Add edges as lines (for stroke)
                if stroke:
                    for i in range(4):
                        lines.append(Line(rect_pts[i], rect_pts[(i+1)%4], stroke, width))
            # ignore 'c' beziers for now; our synthetic file is rectilinear
    
    # Extract text
    text_dict = page.get_text("dict")
    for block in text_dict.get("blocks", []):
        if block.get("type") == 0:  # text block
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    bbox_tuple = tuple(span.get("bbox", (0,0,0,0)))
                    texts.append(TextSpan(text=text, bbox=bbox_tuple))
    
    return PageDraw(lines=lines, texts=texts, filled_rects=filled_rects)
