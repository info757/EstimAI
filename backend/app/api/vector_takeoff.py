from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel
import tempfile, shutil, math
from typing import List, Optional, Literal, Dict, Any

from backend.vpdf.extract import extract_lines
from backend.vpdf.scale import detect_scale_bar_ft_per_unit
from backend.vpdf.measure import curb_length_lf
from backend.vpdf.classify import classify_lines, classify_areas
from backend.vpdf.legend import LegendParser, LegendBasedClassifier
from backend.vpdf.llm_classifier import LLMGeometryClassifier
from backend.vpdf.llm_client import LLMClient
from backend.vpdf.config import load_config
import fitz  # PyMuPDF

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
        # Convert Shapely LineString to polyline format
        polyline = [list(coord) for coord in ls.coords]
        out.append({"polyline": polyline, "kind": "curb"})  # kind will be fixed by caller
    return out

@router.post("/vector", response_model=TakeoffOK | TakeoffErr)
async def takeoff_vector(
    file: UploadFile = File(...),
    page_index: int = Query(1, ge=0, description="0-based page index; 1 is typical Site Plan"),
    config_key: Optional[str] = Query(None),
    debug_overlays: bool = Query(True),
    manual_ft_per_unit: Optional[float] = Query(None),
    process_all_sheets: bool = Query(False, description="Process entire PDF across all sheets"),
    use_llm_classification: bool = Query(False, description="Use LLM-based classification instead of hardcoded rules"),
    analyze_all_pages: bool = Query(True, description="Analyze all pages in PDF instead of single page")
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
        if analyze_all_pages:
            # Intelligent multi-page analysis
            print("Starting multi-page analysis...")
            all_pages_data = analyze_all_pdf_pages(pdf_path)
            print(f"Analyzed {len(all_pages_data)} pages")
            
            # Print page analysis results
            for page_idx, page_data, metadata in all_pages_data:
                print(f"Page {page_idx}: {metadata['page_type']} - {metadata['line_count']} lines, {metadata['text_count']} texts, has_scale={metadata['has_scale']}, has_utilities={metadata['has_utilities']}")
            
            # Find the best site plan page
            site_plan_page = find_site_plan_page(all_pages_data)
            print(f"Selected site plan page: {site_plan_page}")
            
            if site_plan_page is not None:
                px = all_pages_data[site_plan_page][1]  # Get the PageDraw object
                print(f"Using page {site_plan_page} for analysis")
            else:
                # Fallback to requested page
                print(f"No site plan found, using fallback page {page_index}")
                px = extract_lines(pdf_path, page_index)
        elif process_all_sheets:
            # Process all sheets and combine data
            all_sheets_data = []
            doc = fitz.open(pdf_path)
            for sheet_idx in range(len(doc)):
                try:
                    sheet_data = extract_lines(pdf_path, sheet_idx)
                    all_sheets_data.append((sheet_idx, sheet_data))
                except Exception:
                    continue  # Skip problematic sheets
            doc.close()
            
            # Use primary sheet (page_index) for main analysis
            px = extract_lines(pdf_path, page_index)
        else:
            # Single sheet processing (original behavior)
            px = extract_lines(pdf_path, page_index)
            all_sheets_data = [(page_index, px)]
        
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

        # 3) Classification approach
        q = Quantities()
        
        if use_llm_classification:
            # Use LLM-based classification
            print("Using LLM classification...")
            llm_client = LLMClient()
            llm_classifier = LLMGeometryClassifier(llm_client)
            
            # Extract all geometry elements
            elements = llm_classifier.extract_geometry_elements(px)
            print(f"Extracted {len(elements)} geometry elements for LLM")
            
            # Get legend text from other sheets
            legend_text = ""
            try:
                for legend_page_idx in [1, 2, 3]:  # Pages 2, 3, 4
                    try:
                        legend_px = extract_lines(pdf_path, legend_page_idx)
                        legend_texts = [text.text for text in legend_px.texts if len(text.text) > 3]
                        legend_text += " ".join(legend_texts) + " "
                    except Exception:
                        continue
            except Exception:
                pass
            
            print(f"Legend text length: {len(legend_text)}")
            
            # Classify with LLM
            classified_elements = llm_classifier.classify_with_llm(elements, legend_text)
            
            # Convert to Shapely objects
            areas = {}
            lines = {}
            shapely_objects = llm_classifier.convert_to_shapely_objects(classified_elements)
            
            # Separate areas and lines
            for category in ["building", "pavement", "sidewalk"]:
                areas[category] = shapely_objects.get(category, [])
            for category in ["curb", "sanitary", "storm", "water"]:
                lines[category] = shapely_objects.get(category, [])
            
            print(f"LLM classification results: areas={[(k, len(v)) for k, v in areas.items()]}, lines={[(k, len(v)) for k, v in lines.items()]}")
            
            pipe_depths = {}  # LLM could extract this too, but keeping simple for now
            
        else:
            # Use existing legend-aware classification
            legend_classifier = None
            try:
                # Look for legend on pages 2-4 (common legend locations)
                for legend_page_idx in [1, 2, 3]:  # Pages 2, 3, 4
                    try:
                        legend_px = extract_lines(pdf_path, legend_page_idx)
                        legend_parser = LegendParser()
                        legend_entries = legend_parser.parse_legend_page(legend_px)
                        if legend_entries:
                            rules = legend_parser.build_classification_rules()
                            if rules:
                                legend_classifier = LegendBasedClassifier(rules)
                                break
                    except Exception:
                        continue  # Try next page
            except Exception:
                pass  # Fallback to color-based classification
        
            if legend_classifier:
                # Use legend-based classification
                areas = legend_classifier.classify_areas(px)
                lines = legend_classifier.classify_lines(px)
                # Extract pipe depth information
                pipe_depths = legend_classifier.extract_pipe_depths(px)
            else:
                # Fallback to color-based classification
                areas = classify_areas(px)
                lines = classify_lines(px)
                pipe_depths = {}
        
        # If processing all sheets, extract additional data from other sheets
        if process_all_sheets:
            profile_data = extract_profile_data(all_sheets_data)
            # Merge profile data with main classification
            lines, areas, pipe_depths = merge_profile_data(lines, areas, pipe_depths, profile_data)
        
        # Calculate quantities
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
        def _sum_len(ls_arr): 
            total = 0.0
            for ls in ls_arr:
                # Use Shapely's built-in length calculation
                total += ls.length * ft_per_unit
            return total
        q.sanitary_len_lf = _sum_len(lines["sanitary"])
        q.storm_len_lf    = _sum_len(lines["storm"])
        q.water_len_lf    = _sum_len(lines["water"])
        # parking_stalls: leave 0 for now unless you implemented ticks

        # 4) overlays (optional)
        overlays = {"polylines": [], "polygons": [], "points": []}
        if debug_overlays:
            # polylines
            def _polyline_dump(arr, kind):
                return [{"polyline": [list(coord) for coord in ls.coords], "kind": kind} for ls in arr]
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
        notes = None
        if pipe_depths:
            depth_notes = [f"{utility}: {depth:.1f} ft depth" for utility, depth in pipe_depths.items()]
            notes = " | ".join(depth_notes)
        
        diag = Diagnostics(
            ft_per_unit=ft_per_unit,
            scale_source=scale_source, 
            tolerances=cfg["tolerances"],
            notes=notes
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

@router.post("/debug-extraction")
async def debug_extraction(
    file: UploadFile = File(...),
    page_index: int = Query(1, ge=0, description="0-based page index"),
    analyze_all_pages: bool = Query(True, description="Analyze all pages to find best site plan")
):
    """Debug endpoint to see what geometry is extracted from PDF."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            pdf_path = tmp.name
        
        if analyze_all_pages:
            # Use multi-page analysis
            print("Debug: Starting multi-page analysis...")
            all_pages_data = analyze_all_pdf_pages(pdf_path)
            print(f"Debug: Analyzed {len(all_pages_data)} pages")
            
            # Print page analysis results
            for page_idx, page_data, metadata in all_pages_data:
                print(f"Debug: Page {page_idx}: {metadata['page_type']} - {metadata['line_count']} lines, {metadata['text_count']} texts")
            
            # Find the best site plan page
            site_plan_page = find_site_plan_page(all_pages_data)
            print(f"Debug: Selected site plan page: {site_plan_page}")
            
            if site_plan_page is not None:
                px = all_pages_data[site_plan_page][1]
                selected_page = site_plan_page
            else:
                px = extract_lines(pdf_path, page_index)
                selected_page = page_index
        else:
            # Single page analysis
            px = extract_lines(pdf_path, page_index)
            selected_page = page_index
        
        # Count elements
        line_count = len(px.lines)
        text_count = len(px.texts)
        rect_count = len(px.filled_rects)
        
        # Sample some elements
        sample_lines = []
        for i, line in enumerate(px.lines[:10]):  # First 10 lines
            sample_lines.append({
                "p1": line.p1,
                "p2": line.p2,
                "stroke": line.stroke,
                "width": line.width,
                "length": ((line.p2[0] - line.p1[0])**2 + (line.p2[1] - line.p1[1])**2)**0.5
            })
        
        sample_texts = []
        for i, text in enumerate(px.texts[:10]):  # First 10 texts
            sample_texts.append({
                "text": text.text,
                "bbox": text.bbox
            })
        
        sample_rects = []
        for i, rect in enumerate(px.filled_rects[:10]):  # First 10 rects
            sample_rects.append({
                "points": rect.points,
                "fill": rect.fill
            })
        
        return {
            "ok": True,
            "selected_page": selected_page,
            "summary": {
                "lines": line_count,
                "texts": text_count,
                "filled_rects": rect_count
            },
            "sample_lines": sample_lines,
            "sample_texts": sample_texts,
            "sample_rects": sample_rects
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}

def extract_profile_data(all_sheets_data):
    """Extract profile/section data from all sheets."""
    profile_data = {
        "elevations": {},
        "depths": {},
        "utilities": {}
    }
    
    for sheet_idx, sheet_data in all_sheets_data:
        # Look for profile indicators
        for text in sheet_data.texts:
            text_lower = text.text.lower()
            
            # Look for elevation data (EG, INV, etc.)
            if any(keyword in text_lower for keyword in ["eg", "inv", "elevation", "grade", "depth"]):
                # Extract numeric values
                import re
                numbers = re.findall(r'(\d+(?:\.\d+)?)', text.text)
                if numbers:
                    # Try to associate with nearby utilities
                    nearby_utility = find_nearby_utility(sheet_data, text)
                    if nearby_utility:
                        if "eg" in text_lower or "elevation" in text_lower:
                            profile_data["elevations"][nearby_utility] = float(numbers[0])
                        elif "inv" in text_lower or "depth" in text_lower:
                            profile_data["depths"][nearby_utility] = float(numbers[0])
            
            # Look for utility labels
            if any(keyword in text_lower for keyword in ["sanitary", "storm", "water", "sewer", "drain"]):
                utility_type = classify_utility_from_text(text.text)
                if utility_type:
                    profile_data["utilities"][utility_type] = text.text
    
    return profile_data

def find_nearby_utility(sheet_data, text):
    """Find utility type near a text element."""
    text_center = ((text.bbox[0] + text.bbox[2]) / 2, (text.bbox[1] + text.bbox[3]) / 2)
    min_distance = float('inf')
    closest_utility = None
    
    for line in sheet_data.lines:
        if not line.stroke:
            continue
        
        line_center = ((line.p1[0] + line.p2[0]) / 2, (line.p1[1] + line.p2[1]) / 2)
        distance = ((text_center[0] - line_center[0])**2 + (text_center[1] - line_center[1])**2)**0.5
        
        if distance < min_distance and distance < 100:  # Within 100 units
            min_distance = distance
            # Classify line by color/position
            if line.stroke:
                if all(c < 0.2 for c in line.stroke):
                    closest_utility = "curb"
                elif line.stroke[2] > line.stroke[0] and line.stroke[2] > line.stroke[1]:
                    closest_utility = "water"
                elif line.stroke[0] > line.stroke[1] and line.stroke[0] > line.stroke[2]:
                    closest_utility = "sanitary"
                elif line.stroke[1] > line.stroke[0] and line.stroke[1] > line.stroke[2]:
                    closest_utility = "storm"
    
    return closest_utility

def classify_utility_from_text(text):
    """Classify utility type from text content."""
    text_lower = text.lower()
    if any(word in text_lower for word in ["sanitary", "sewer"]):
        return "sanitary"
    elif any(word in text_lower for word in ["storm", "drain"]):
        return "storm"
    elif any(word in text_lower for word in ["water", "h2o"]):
        return "water"
    return None

def merge_profile_data(lines, areas, pipe_depths, profile_data):
    """Merge profile data with main classification results."""
    # Add profile depths to pipe_depths
    for utility, depth in profile_data["depths"].items():
        pipe_depths[utility] = depth
    
    # Add profile elevations as additional data
    for utility, elevation in profile_data["elevations"].items():
        if utility not in pipe_depths:
            pipe_depths[f"{utility}_elevation"] = elevation
    
    return lines, areas, pipe_depths

def analyze_all_pdf_pages(pdf_path: str) -> List[tuple]:
    """Analyze all pages in PDF and return page data with metadata."""
    all_pages_data = []
    doc = fitz.open(pdf_path)
    
    for page_idx in range(len(doc)):
        try:
            page_data = extract_lines(pdf_path, page_idx)
            
            # Analyze page content to determine page type
            page_type = classify_page_type(page_data)
            page_metadata = {
                "page_index": page_idx,
                "page_type": page_type,
                "line_count": len(page_data.lines),
                "text_count": len(page_data.texts),
                "area_count": len(page_data.filled_rects),
                "has_scale": detect_scale_in_page(page_data),
                "has_utilities": detect_utilities_in_page(page_data),
                "has_profiles": detect_profiles_in_page(page_data)
            }
            
            all_pages_data.append((page_idx, page_data, page_metadata))
            
        except Exception as e:
            print(f"Failed to analyze page {page_idx}: {e}")
            continue
    
    doc.close()
    return all_pages_data

def classify_page_type(page_data) -> str:
    """Classify what type of page this is based on content."""
    text_content = " ".join([text.text.lower() for text in page_data.texts])
    
    # Check for specific page types
    if any(keyword in text_content for keyword in ["cover", "title", "index"]):
        return "cover"
    elif any(keyword in text_content for keyword in ["site plan", "overall", "plan view"]):
        return "site_plan"
    elif any(keyword in text_content for keyword in ["utility", "sewer", "storm", "water"]):
        return "utility_plan"
    elif any(keyword in text_content for keyword in ["profile", "section", "elevation", "eg", "inv"]):
        return "profile"
    elif any(keyword in text_content for keyword in ["detail", "section", "typical"]):
        return "detail"
    else:
        return "unknown"

def detect_scale_in_page(page_data) -> bool:
    """Detect if page has scale information."""
    for text in page_data.texts:
        if any(keyword in text.text.lower() for keyword in ["scale", "1\"", "ft", "feet"]):
            return True
    return False

def detect_utilities_in_page(page_data) -> bool:
    """Detect if page has utility information."""
    for text in page_data.texts:
        if any(keyword in text.text.lower() for keyword in ["sanitary", "storm", "water", "sewer", "utility"]):
            return True
    return False

def detect_profiles_in_page(page_data) -> bool:
    """Detect if page has profile information."""
    for text in page_data.texts:
        if any(keyword in text.text.lower() for keyword in ["profile", "eg", "inv", "elevation", "grade"]):
            return True
    return False

def find_site_plan_page(all_pages_data: List[tuple]) -> Optional[int]:
    """Find the best site plan page from all pages."""
    site_plan_candidates = []
    
    for page_idx, page_data, metadata in all_pages_data:
        if metadata["page_type"] == "site_plan":
            # Score based on content richness
            score = (
                metadata["line_count"] * 0.4 +  # More lines = more geometry
                metadata["text_count"] * 0.3 +  # More text = more labels
                metadata["area_count"] * 0.2 +  # More areas = more buildings
                (10 if metadata["has_scale"] else 0) +  # Scale is important
                (10 if metadata["has_utilities"] else 0)  # Utilities are important
            )
            site_plan_candidates.append((page_idx, score))
    
    if site_plan_candidates:
        # Return the page with highest score
        best_page = max(site_plan_candidates, key=lambda x: x[1])
        return best_page[0]
    
    # Fallback: find page with most geometry
    geometry_rich_pages = []
    for page_idx, page_data, metadata in all_pages_data:
        if metadata["line_count"] > 50:  # Substantial geometry
            geometry_rich_pages.append((page_idx, metadata["line_count"]))
    
    if geometry_rich_pages:
        best_page = max(geometry_rich_pages, key=lambda x: x[1])
        return best_page[0]
    
    return None

