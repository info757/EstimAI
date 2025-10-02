"""
Vector PDF Parser - Extracts geometric data from vector PDFs for quantity takeoff.

This module extracts polylines, polygons, rectangles, and text annotations from
vector PDFs to enable accurate measurement of quantities for construction estimating.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
import pdfplumber

from ..core.paths import project_dir


def calculate_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate Euclidean distance between two points."""
    return ((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)**0.5


def calculate_polyline_length(points: List[Tuple[float, float]]) -> float:
    """Calculate total length of a polyline from a list of points."""
    if len(points) < 2:
        return 0.0
    
    total_length = 0.0
    for i in range(len(points) - 1):
        total_length += calculate_distance(points[i], points[i+1])
    return total_length


def calculate_polygon_area(points: List[Tuple[float, float]]) -> float:
    """Calculate area of a polygon using the shoelace formula."""
    if len(points) < 3:
        return 0.0
    
    # Shoelace formula
    area = 0.0
    for i in range(len(points)):
        j = (i + 1) % len(points)
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return abs(area) / 2.0


def parse_scale_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Parse scale information from text like '1\" = 20\'' or 'Scale: 1:240'.
    Returns dict with scale_factor (PDF units to real-world feet).
    """
    # Pattern: 1" = 20' or similar
    pattern1 = r'1["\']?\s*=\s*(\d+)[\'"]?'
    match = re.search(pattern1, text, re.IGNORECASE)
    if match:
        feet_per_inch = float(match.group(1))
        # Assume 72 PDF points = 1 inch
        pdf_units_per_inch = 72.0
        pdf_units_per_foot = pdf_units_per_inch / feet_per_inch
        return {
            "scale_text": match.group(0),
            "feet_per_inch": feet_per_inch,
            "pdf_units_per_foot": pdf_units_per_foot
        }
    
    # Pattern: 1:240 (1 inch = 20 feet = 240 inches)
    pattern2 = r'1\s*:\s*(\d+)'
    match = re.search(pattern2, text, re.IGNORECASE)
    if match:
        ratio = float(match.group(1))
        feet_per_inch = ratio / 12.0
        pdf_units_per_inch = 72.0
        pdf_units_per_foot = pdf_units_per_inch / feet_per_inch
        return {
            "scale_text": match.group(0),
            "feet_per_inch": feet_per_inch,
            "pdf_units_per_foot": pdf_units_per_foot
        }
    
    return None


def extract_lines(page) -> List[Dict[str, Any]]:
    """Extract line segments from a PDF page."""
    lines = []
    
    # pdfplumber provides lines as dict objects with x0, y0, x1, y1
    page_lines = page.lines if hasattr(page, 'lines') else []
    
    for line in page_lines:
        x0, y0, x1, y1 = line.get('x0'), line.get('y0'), line.get('x1'), line.get('y1')
        if all(coord is not None for coord in [x0, y0, x1, y1]):
            length = calculate_distance((x0, y0), (x1, y1))
            lines.append({
                "start": [float(x0), float(y0)],
                "end": [float(x1), float(y1)],
                "length": float(length),
                "width": float(line.get('width', 1.0))
            })
    
    return lines


def extract_rectangles(page) -> List[Dict[str, Any]]:
    """Extract rectangles from a PDF page."""
    rectangles = []
    
    # pdfplumber provides rects as dict objects
    page_rects = page.rects if hasattr(page, 'rects') else []
    
    for rect in page_rects:
        x0, y0, x1, y1 = rect.get('x0'), rect.get('y0'), rect.get('x1'), rect.get('y1')
        if all(coord is not None for coord in [x0, y0, x1, y1]):
            width = abs(x1 - x0)
            height = abs(y1 - y0)
            area = width * height
            
            rectangles.append({
                "bbox": [float(x0), float(y0), float(x1), float(y1)],
                "width": float(width),
                "height": float(height),
                "area": float(area),
                "center": [float((x0 + x1) / 2), float((y0 + y1) / 2)]
            })
    
    return rectangles


def extract_curves(page) -> List[Dict[str, Any]]:
    """Extract curves and paths from a PDF page."""
    curves = []
    
    # pdfplumber provides curves as path objects
    page_curves = page.curves if hasattr(page, 'curves') else []
    
    for curve in page_curves:
        pts = curve.get('pts', [])
        if len(pts) >= 2:
            # Convert points to list of tuples
            points = [(float(p[0]), float(p[1])) for p in pts]
            length = calculate_polyline_length(points)
            
            curves.append({
                "points": [[float(p[0]), float(p[1])] for p in points],
                "length": float(length),
                "closed": bool(curve.get('closed', False))
            })
    
    return curves


def group_lines_into_polylines(lines: List[Dict[str, Any]], tolerance: float = 5.0) -> List[Dict[str, Any]]:
    """
    Group connected line segments into polylines with improved algorithm.
    Handles disconnected segments and creates multiple polylines.
    """
    if not lines:
        return []
    
    polylines = []
    used = set()
    
    # Try to build polylines starting from each unused line
    for i, line in enumerate(lines):
        if i in used:
            continue
            
        # Start a new polyline
        points = [line["start"][:], line["end"][:]]
        used.add(i)
        
        # Try to extend both ends repeatedly
        changed = True
        while changed:
            changed = False
            
            for j, other in enumerate(lines):
                if j in used:
                    continue
                
                # Check connections at both ends
                start_to_start = calculate_distance(tuple(points[0]), tuple(other["start"])) < tolerance
                start_to_end = calculate_distance(tuple(points[0]), tuple(other["end"])) < tolerance
                end_to_start = calculate_distance(tuple(points[-1]), tuple(other["start"])) < tolerance
                end_to_end = calculate_distance(tuple(points[-1]), tuple(other["end"])) < tolerance
                
                if start_to_end:
                    # Prepend other line (reversed)
                    points.insert(0, other["start"])
                    used.add(j)
                    changed = True
                elif start_to_start:
                    # Prepend other line
                    points.insert(0, other["end"])
                    used.add(j)
                    changed = True
                elif end_to_start:
                    # Append other line
                    points.append(other["end"])
                    used.add(j)
                    changed = True
                elif end_to_end:
                    # Append other line (reversed)
                    points.append(other["start"])
                    used.add(j)
                    changed = True
        
        # Convert to tuples for length calculation
        points_tuples = [tuple(p) for p in points]
        length = calculate_polyline_length(points_tuples)
        
        polylines.append({
            "points": points,
            "length": float(length),
            "segments": len(points) - 1
        })
    
    return polylines


def find_text_near_geometry(geometry_center: Tuple[float, float], text_objects: List[Dict[str, Any]], max_distance: float = 50.0) -> List[str]:
    """
    Find text objects near a geometry element.
    Returns list of text strings found within max_distance.
    """
    nearby_text = []
    
    for text_obj in text_objects:
        bbox = text_obj.get("bbox", [])
        if len(bbox) >= 4:
            text_center = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
            distance = calculate_distance(geometry_center, text_center)
            
            if distance < max_distance:
                nearby_text.append(text_obj.get("text", "").lower())
    
    return nearby_text


def classify_geometry_with_text(
    rect: Dict[str, Any], 
    nearby_text: List[str],
    all_text: str
) -> Optional[str]:
    """
    Classify rectangles based on size and nearby text with improved heuristics.
    """
    area = rect["area"]
    text_combined = " ".join(nearby_text) + " " + all_text.lower()
    
    # Check for explicit labels first
    if any(word in text_combined for word in ["warehouse", "building"]):
        if area > 50000:
            return "building"
    
    if "sidewalk" in text_combined or "walk" in text_combined:
        if 1000 < area < 100000:
            return "sidewalk"
    
    if any(word in text_combined for word in ["stall", "parking"]):
        if 50 < area < 2000:
            return "parking_stall"
    
    # Size-based classification as fallback
    if area > 200000:  # Very large
        return "building"
    elif area > 50000:  # Large
        return "pavement"
    elif 1000 < area < 50000:  # Medium
        # Could be sidewalk or smaller pavement area
        return "pavement_or_sidewalk"
    elif 50 < area < 1000:  # Small
        return "parking_stall"
    
    return None


def classify_polyline_with_text(
    polyline: Dict[str, Any],
    nearby_text: List[str],
    all_text: str
) -> Optional[str]:
    """
    Classify polylines (utilities, curbs, etc.) based on nearby text.
    """
    text_combined = " ".join(nearby_text) + " " + all_text.lower()
    length = polyline["length"]
    
    # Look for utility keywords
    if any(word in text_combined for word in ["sanitary", "sewer", "san"]):
        if length > 100:  # Reasonable utility line length
            return "sanitary_sewer"
    
    if any(word in text_combined for word in ["storm", "drain"]):
        if length > 100:
            return "storm_drain"
    
    if any(word in text_combined for word in ["water", "h2o"]):
        if length > 100:
            return "water_main"
    
    if any(word in text_combined for word in ["curb", "gutter"]):
        if length > 50:
            return "curb"
    
    # If it's a long polyline without specific classification
    if length > 500:
        return "utility_or_curb"
    
    return None


def extract_text_with_positions(page) -> List[Dict[str, Any]]:
    """Extract text along with bounding box positions."""
    text_objects = []
    
    try:
        words = page.extract_words()
        for word in words:
            text_objects.append({
                "text": word.get("text", ""),
                "bbox": [
                    float(word.get("x0", 0)),
                    float(word.get("top", 0)),
                    float(word.get("x1", 0)),
                    float(word.get("bottom", 0))
                ]
            })
    except Exception:
        # Fallback if extract_words fails
        pass
    
    return text_objects


def parse_pdf_geometry(pdf_path: Path) -> Dict[str, Any]:
    """
    Parse a PDF and extract all geometric elements with scale and classification.
    
    Returns a structured dict with lines, rectangles, curves, polylines,
    and calculated measurements in both PDF units and real-world units.
    """
    pages_data = []
    detected_scale = None
    
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            # First pass: look for scale information in all pages
            all_text = ""
            for page in pdf.pages:
                page_text = (page.extract_text() or "").strip()
                all_text += " " + page_text
                if not detected_scale:
                    detected_scale = parse_scale_from_text(page_text)
            
            # Default scale if not found (assume 1:1 or mark as unknown)
            if not detected_scale:
                detected_scale = {
                    "scale_text": "unknown",
                    "feet_per_inch": 1.0,  # Assume 1:1 if no scale found
                    "pdf_units_per_foot": 72.0
                }
            
            # Second pass: extract geometry with classification
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract raw geometry
                lines = extract_lines(page)
                rectangles = extract_rectangles(page)
                curves = extract_curves(page)
                
                # Extract text for context and proximity matching
                text = (page.extract_text() or "").strip()
                text_objects = extract_text_with_positions(page)
                
                # Group lines into polylines with improved algorithm
                polylines = group_lines_into_polylines(lines, tolerance=5.0)
                
                # Classify rectangles with text proximity
                classified_rects = []
                for rect in rectangles:
                    center = tuple(rect["center"])
                    nearby_text = find_text_near_geometry(center, text_objects, max_distance=100.0)
                    geometry_type = classify_geometry_with_text(rect, nearby_text, text)
                    
                    # Convert to real-world units
                    pdf_to_ft = 1.0 / detected_scale["pdf_units_per_foot"]
                    width_ft = rect["width"] * pdf_to_ft
                    height_ft = rect["height"] * pdf_to_ft
                    area_sf = rect["area"] * (pdf_to_ft ** 2)
                    
                    classified_rects.append({
                        **rect,
                        "type": geometry_type,
                        "width_ft": float(width_ft),
                        "height_ft": float(height_ft),
                        "area_sf": float(area_sf)
                    })
                
                # Classify polylines with text proximity
                classified_polylines = []
                for polyline in polylines:
                    # Get center point of polyline
                    points = polyline["points"]
                    if points:
                        mid_idx = len(points) // 2
                        center = tuple(points[mid_idx])
                        nearby_text = find_text_near_geometry(center, text_objects, max_distance=100.0)
                        polyline_type = classify_polyline_with_text(polyline, nearby_text, text)
                        
                        # Convert to real-world units
                        pdf_to_ft = 1.0 / detected_scale["pdf_units_per_foot"]
                        length_ft = polyline["length"] * pdf_to_ft
                        
                        classified_polylines.append({
                            **polyline,
                            "type": polyline_type,
                            "length_ft": float(length_ft)
                        })
                    else:
                        classified_polylines.append({
                            **polyline,
                            "type": None,
                            "length_ft": 0.0
                        })
                
                # Calculate summaries
                pdf_to_ft = 1.0 / detected_scale["pdf_units_per_foot"]
                total_line_length_ft = sum(line["length"] for line in lines) * pdf_to_ft
                total_polyline_length_ft = sum(pl["length"] for pl in polylines) * pdf_to_ft
                total_rectangle_area_sf = sum(rect["area"] for rect in rectangles) * (pdf_to_ft ** 2)
                
                page_data = {
                    "page_number": page_num,
                    "dimensions": {
                        "width": float(page.width),
                        "height": float(page.height)
                    },
                    "lines": lines,
                    "rectangles": classified_rects,
                    "curves": curves,
                    "polylines": classified_polylines,
                    "text_objects": text_objects,
                    "summary": {
                        "line_count": len(lines),
                        "rectangle_count": len(rectangles),
                        "curve_count": len(curves),
                        "polyline_count": len(polylines),
                        "total_line_length_pdf": float(sum(line["length"] for line in lines)),
                        "total_polyline_length_pdf": float(sum(pl["length"] for pl in polylines)),
                        "total_rectangle_area_pdf": float(sum(rect["area"] for rect in rectangles)),
                        "total_line_length_ft": float(total_line_length_ft),
                        "total_polyline_length_ft": float(total_polyline_length_ft),
                        "total_rectangle_area_sf": float(total_rectangle_area_sf)
                    }
                }
                
                pages_data.append(page_data)
    
    except Exception as e:
        # If parsing fails, return minimal structure
        return {
            "error": str(e),
            "scale": None,
            "pages": []
        }
    
    return {
        "file": str(pdf_path),
        "page_count": len(pages_data),
        "scale": detected_scale,
        "pages": pages_data
    }


def write_geometry_index(pid: str) -> Path:
    """
    Parse all PDFs in a project's docs folder and create geometry_index.json.
    
    This index contains vector geometry data (lines, polygons, measurements)
    that can be used by the takeoff agent for quantity extraction.
    """
    proj = project_dir(pid)
    docs = proj / "docs"
    
    geometries = []
    
    if docs.exists():
        for pdf_path in sorted(docs.glob("*.pdf")):
            geometry_data = parse_pdf_geometry(pdf_path)
            geometries.append(geometry_data)
    
    index = {
        "project_id": pid,
        "geometries": geometries
    }
    
    output_path = proj / "geometry_index.json"
    output_path.write_text(json.dumps(index, indent=2))
    
    return output_path