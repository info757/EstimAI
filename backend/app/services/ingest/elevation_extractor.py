"""
Elevation extraction from PDF text annotations.

Extracts invert elevations (IE, INV) from text near pipe endpoints
and matches them to pipe geometry.
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def extract_pipe_elevations(
    polyline: Dict[str, Any],
    text_runs: List[Dict[str, Any]],
    search_radius_ft: float = 10.0
) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract invert elevations for a pipe from nearby text.
    
    Looks for patterns like:
    - IE=95.5
    - INV. 95.5
    - INV IN=95.5
    - INV OUT=96.2
    
    Args:
        polyline: Polyline dict with vertices or bbox
        text_runs: List of text runs with bbox and text
        search_radius_ft: Search radius around pipe endpoints
        
    Returns:
        (invert_in, invert_out) tuple, or (None, None) if not found
    """
    if not text_runs:
        return (None, None)
    
    # Get pipe endpoints
    vertices = polyline.get("vertices", [])
    if not vertices or len(vertices) < 2:
        # Fall back to bbox
        bbox = polyline.get("bbox", [])
        if len(bbox) >= 4:
            vertices = [[bbox[0], bbox[1]], [bbox[2], bbox[3]]]
        else:
            return (None, None)
    
    start = vertices[0]
    end = vertices[-1]
    
    # Find text near start
    start_elevations = _find_elevations_near_point(start, text_runs, search_radius_ft)
    
    # Find text near end
    end_elevations = _find_elevations_near_point(end, text_runs, search_radius_ft)
    
    # Determine which is invert in vs out
    # Heuristic: Lower elevation is usually downstream (out)
    invert_in = None
    invert_out = None
    
    if start_elevations and end_elevations:
        # Have both - assign based on elevation
        if start_elevations[0] > end_elevations[0]:
            invert_in = start_elevations[0]
            invert_out = end_elevations[0]
        else:
            invert_in = end_elevations[0]
            invert_out = start_elevations[0]
    elif start_elevations:
        # Only have start - use as invert_in
        invert_in = start_elevations[0]
    elif end_elevations:
        # Only have end - use as invert_out
        invert_out = end_elevations[0]
    
    if invert_in or invert_out:
        in_str = f"{invert_in:.2f}" if invert_in is not None else "N/A"
        out_str = f"{invert_out:.2f}" if invert_out is not None else "N/A"
        logger.debug(
            f"Extracted elevations for {polyline.get('id')}: "
            f"IN={in_str}, OUT={out_str}"
        )
    
    return (invert_in, invert_out)


def _find_elevations_near_point(
    point: List[float],
    text_runs: List[Dict[str, Any]],
    radius_ft: float
) -> List[float]:
    """
    Find elevation values in text near a point.
    
    Uses regex first, then LLM fallback if no regex matches.
    
    Returns:
        List of elevation values (may be empty or have multiple)
    """
    px, py = point[0], point[1]
    elevations = []
    nearby_text_snippets = []
    
    for text_run in text_runs:
        # Check distance
        bbox = text_run.get("bbox", [])
        if len(bbox) < 4:
            continue
        
        # Use bbox center
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        
        dist = ((cx - px)**2 + (cy - py)**2)**0.5
        
        if dist <= radius_ft:
            # Check for elevation pattern with regex
            text = text_run.get("text", "")
            found_elevations = _parse_elevation_from_text(text)
            elevations.extend(found_elevations)
            
            # Collect text for LLM fallback
            if text and len(text.strip()) > 2:
                nearby_text_snippets.append(text)
    
    # If regex found nothing, try LLM on combined nearby text
    if not elevations and nearby_text_snippets:
        combined_text = " ".join(nearby_text_snippets)
        if len(combined_text) > 3:
            from ..ai.elevation_parser import get_elevation_parser
            parser = get_elevation_parser()
            llm_elevation = parser.parse_elevation(combined_text, "pipe endpoint")
            if llm_elevation is not None:
                logger.info(f"✨ LLM fallback found elevation {llm_elevation} (regex missed)")
                elevations.append(llm_elevation)
    
    return elevations


def _parse_elevation_from_text(text: str) -> List[float]:
    """
    Parse elevation values from text string.
    
    Patterns:
    - IE=95.5
    - INV. 95.5
    - INV IN=95.5
    - INV OUT=96.2
    - EL. 100.5
    
    Returns:
        List of elevation values found
    """
    elevations = []
    
    # Common elevation patterns
    patterns = [
        r'IE\s*[=:]\s*([0-9]+\.?[0-9]*)',          # IE=95.5
        r'INV\.?\s*[=:]\s*([0-9]+\.?[0-9]*)',      # INV. 95.5, INV:95.5
        r'INV\s+IN\s*[=:]\s*([0-9]+\.?[0-9]*)',    # INV IN=95.5
        r'INV\s+OUT\s*[=:]\s*([0-9]+\.?[0-9]*)',   # INV OUT=96.2
        r'INVERT\s*[=:]\s*([0-9]+\.?[0-9]*)',      # INVERT=95.5
        r'EL\.?\s*[=:]\s*([0-9]+\.?[0-9]*)',       # EL. 100.5, EL:100.5
        r'ELEV\.?\s*[=:]\s*([0-9]+\.?[0-9]*)',     # ELEV. 100.5
    ]
    
    text_upper = text.upper()
    
    for pattern in patterns:
        matches = re.finditer(pattern, text_upper)
        for match in matches:
            try:
                elev = float(match.group(1))
                # Sanity check: elevation should be reasonable (0-10,000 ft typical)
                if 0 < elev < 10_000:
                    elevations.append(elev)
            except (ValueError, IndexError):
                continue
    
    return elevations


def create_s_profile_from_inverts(
    invert_in: Optional[float],
    invert_out: Optional[float],
    pipe_length_ft: float
) -> List[Tuple[float, float]]:
    """
    Create station-elevation profile from invert elevations.
    
    Args:
        invert_in: Invert elevation at inlet (upstream)
        invert_out: Invert elevation at outlet (downstream)
        pipe_length_ft: Pipe length in feet
        
    Returns:
        List of (station, elevation) tuples, or empty if no inverts
    """
    if invert_in is None and invert_out is None:
        return []
    
    # If only one invert, assume constant slope or flat
    if invert_in is not None and invert_out is None:
        # Assume 0.5% slope (typical minimum)
        slope = 0.005
        invert_out = invert_in - (slope * pipe_length_ft)
    elif invert_out is not None and invert_in is None:
        # Assume 0.5% slope
        slope = 0.005
        invert_in = invert_out + (slope * pipe_length_ft)
    
    # Create profile from in to out
    return [
        (0.0, invert_in),
        (1.0, invert_out)
    ]


def estimate_ground_elevation(
    bbox: List[float],
    surface_sampler: Optional[Any] = None,
    default_elevation: float = 100.0
) -> float:
    """
    Estimate ground elevation at pipe location.
    
    Args:
        bbox: Pipe bounding box [minx, miny, maxx, maxy]
        surface_sampler: Optional surface sampler (from contours)
        default_elevation: Fallback if no surface data
        
    Returns:
        Ground elevation in feet
    """
    if surface_sampler is not None:
        # Use surface sampler
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        try:
            elev = surface_sampler.sample(cx, cy)
            if elev is not None and 0 < elev < 10_000:
                return elev
        except Exception as e:
            logger.debug(f"Surface sampler failed: {e}")
    
    # Fallback to default
    return default_elevation

