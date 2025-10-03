"""Earthwork surface estimation using TIN-based analysis."""
import math
import re
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import logging

from ..ingest.extract import VectorEl, TextEl
from ..ingest.scale import ScaleInfo

logger = logging.getLogger(__name__)


@dataclass
class ContourPoint:
    """Contour point with elevation."""
    x_ft: float
    y_ft: float
    elevation_ft: float
    contour_type: str  # "existing" or "proposed"


@dataclass
class TINSurface:
    """Triangulated Irregular Network surface."""
    points: List[ContourPoint]
    triangles: List[Tuple[int, int, int]]  # Indices into points
    bounds: Tuple[float, float, float, float]  # min_x, min_y, max_x, max_y


@dataclass
class EarthworkVolume:
    """Earthwork volume calculation result."""
    cut_yd3: float
    fill_yd3: float
    net_yd3: float
    area_sf: float
    method: str  # "tin" or "grid"
    confidence: float  # 0.0 to 1.0


def estimate_earthwork_from_contours(
    vectors: List[VectorEl], 
    texts: List[TextEl], 
    scale_info: ScaleInfo
) -> Optional[EarthworkVolume]:
    """
    Estimate earthwork volumes from contour lines.
    
    Args:
        vectors: List of vector elements
        texts: List of text elements
        scale_info: Scale information for coordinate conversion
        
    Returns:
        Earthwork volume estimate or None if insufficient data
    """
    try:
        # Extract contour points
        existing_points = _extract_contour_points(vectors, texts, "existing")
        proposed_points = _extract_contour_points(vectors, texts, "proposed")
        
        if not existing_points and not proposed_points:
            logger.warning("No contour points found")
            return None
        
        # Create TIN surfaces
        existing_surface = _create_tin_surface(existing_points) if existing_points else None
        proposed_surface = _create_tin_surface(proposed_points) if proposed_points else None
        
        if not existing_surface and not proposed_surface:
            logger.warning("Could not create TIN surfaces")
            return None
        
        # Calculate earthwork volumes
        volume = _calculate_earthwork_volume(existing_surface, proposed_surface)
        
        logger.info(f"Estimated earthwork: {volume.cut_yd3:.1f} YD3 cut, {volume.fill_yd3:.1f} YD3 fill")
        return volume
        
    except Exception as e:
        logger.error(f"Error estimating earthwork from contours: {e}")
        return None


def _extract_contour_points(vectors: List[VectorEl], texts: List[TextEl], contour_type: str) -> List[ContourPoint]:
    """Extract contour points from vectors and texts."""
    points = []
    
    # Find contour vectors
    contour_vectors = _find_contour_vectors(vectors, contour_type)
    
    for vector in contour_vectors:
        # Extract elevation from nearby text
        elevation = _extract_elevation_from_text(vector, texts)
        
        if elevation is not None:
            # Sample points along the contour
            for point in vector.points:
                points.append(ContourPoint(
                    x_ft=point[0],
                    y_ft=point[1],
                    elevation_ft=elevation,
                    contour_type=contour_type
                ))
    
    return points


def _find_contour_vectors(vectors: List[VectorEl], contour_type: str) -> List[VectorEl]:
    """Find contour vectors of specified type."""
    contour_vectors = []
    
    for vector in vectors:
        if _is_contour_vector(vector, contour_type):
            contour_vectors.append(vector)
    
    return contour_vectors


def _is_contour_vector(vector: VectorEl, contour_type: str) -> bool:
    """Check if vector represents a contour line."""
    # Check for contour patterns
    if vector.kind in ["line", "polyline"] and vector.stroke_w > 0:
        # Check for contour characteristics
        if vector.stroke_w < 2.0:  # Contours are typically thin lines
            return True
    
    return False


def _extract_elevation_from_text(vector: VectorEl, texts: List[TextEl]) -> Optional[float]:
    """Extract elevation from text near a vector."""
    # Find nearby texts
    nearby_texts = _find_nearby_texts(vector, texts)
    
    for text in nearby_texts:
        elevation = _parse_elevation_from_text(text.text)
        if elevation is not None:
            return elevation
    
    return None


def _find_nearby_texts(vector: VectorEl, texts: List[TextEl]) -> List[TextEl]:
    """Find text elements near a vector."""
    nearby_texts = []
    tolerance = 50.0  # feet
    
    for text in texts:
        if _text_near_vector(text, vector, tolerance):
            nearby_texts.append(text)
    
    return nearby_texts


def _text_near_vector(text: TextEl, vector: VectorEl, tolerance: float) -> bool:
    """Check if text is near a vector."""
    # Get text center
    text_center = ((text.bbox[0] + text.bbox[2]) / 2, (text.bbox[1] + text.bbox[3]) / 2)
    
    # Check distance to vector points
    for point in vector.points:
        distance = math.sqrt((text_center[0] - point[0]) ** 2 + (text_center[1] - point[1]) ** 2)
        if distance <= tolerance:
            return True
    
    return False


def _parse_elevation_from_text(text: str) -> Optional[float]:
    """Parse elevation from text."""
    # Look for elevation patterns
    elevation_patterns = [
        r'(\d+(?:\.\d+)?)\s*FT',
        r'(\d+(?:\.\d+)?)\s*FEET',
        r'EL\s*(\d+(?:\.\d+)?)',
        r'ELEV\s*(\d+(?:\.\d+)?)',
        r'(\d+(?:\.\d+)?)\s*\''
    ]
    
    for pattern in elevation_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    
    return None


def _create_tin_surface(points: List[ContourPoint]) -> Optional[TINSurface]:
    """Create TIN surface from contour points."""
    if len(points) < 3:
        return None
    
    try:
        # Convert points to numpy array
        point_array = np.array([(p.x_ft, p.y_ft, p.elevation_ft) for p in points])
        
        # Create Delaunay triangulation
        from scipy.spatial import Delaunay
        tri = Delaunay(point_array[:, :2])
        
        # Get triangle indices
        triangles = tri.simplices.tolist()
        
        # Calculate bounds
        min_x = min(p.x_ft for p in points)
        min_y = min(p.y_ft for p in points)
        max_x = max(p.x_ft for p in points)
        max_y = max(p.y_ft for p in points)
        
        return TINSurface(
            points=points,
            triangles=triangles,
            bounds=(min_x, min_y, max_x, max_y)
        )
        
    except ImportError:
        logger.warning("scipy not available, using simplified TIN")
        return _create_simple_tin_surface(points)
    except Exception as e:
        logger.error(f"Error creating TIN surface: {e}")
        return None


def _create_simple_tin_surface(points: List[ContourPoint]) -> Optional[TINSurface]:
    """Create simplified TIN surface without scipy."""
    if len(points) < 3:
        return None
    
    # Simple triangulation (not optimal)
    triangles = []
    for i in range(len(points) - 2):
        triangles.append((i, i + 1, i + 2))
    
    # Calculate bounds
    min_x = min(p.x_ft for p in points)
    min_y = min(p.y_ft for p in points)
    max_x = max(p.x_ft for p in points)
    max_y = max(p.y_ft for p in points)
    
    return TINSurface(
        points=points,
        triangles=triangles,
        bounds=(min_x, min_y, max_x, max_y)
    )


def _calculate_earthwork_volume(
    existing_surface: Optional[TINSurface], 
    proposed_surface: Optional[TINSurface]
) -> EarthworkVolume:
    """Calculate earthwork volume between surfaces."""
    if not existing_surface and not proposed_surface:
        return EarthworkVolume(0.0, 0.0, 0.0, 0.0, "tin", 0.0)
    
    if not existing_surface:
        # Only proposed surface - assume existing is flat at lowest elevation
        min_elevation = min(p.elevation_ft for p in proposed_surface.points)
        return EarthworkVolume(0.0, 0.0, 0.0, 0.0, "tin", 0.0)
    
    if not proposed_surface:
        # Only existing surface - assume proposed is flat at highest elevation
        max_elevation = max(p.elevation_ft for p in existing_surface.points)
        return EarthworkVolume(0.0, 0.0, 0.0, 0.0, "tin", 0.0)
    
    # Calculate volume between surfaces
    cut_volume = 0.0
    fill_volume = 0.0
    area = 0.0
    
    # Sample points on a grid
    grid_size = 10.0  # feet
    min_x, min_y, max_x, max_y = existing_surface.bounds
    
    for x in np.arange(min_x, max_x, grid_size):
        for y in np.arange(min_y, max_y, grid_size):
            # Get elevations from both surfaces
            existing_elev = _interpolate_elevation(existing_surface, x, y)
            proposed_elev = _interpolate_elevation(proposed_surface, x, y)
            
            if existing_elev is not None and proposed_elev is not None:
                diff = proposed_elev - existing_elev
                cell_area = grid_size * grid_size
                cell_volume = diff * cell_area
                
                if diff > 0:
                    fill_volume += cell_volume
                else:
                    cut_volume += abs(cell_volume)
                
                area += cell_area
    
    # Convert to cubic yards
    cut_yd3 = cut_volume / 27.0  # cubic feet to cubic yards
    fill_yd3 = fill_volume / 27.0
    net_yd3 = cut_yd3 - fill_yd3
    area_sf = area
    
    # Calculate confidence based on data quality
    confidence = _calculate_confidence(existing_surface, proposed_surface)
    
    return EarthworkVolume(
        cut_yd3=cut_yd3,
        fill_yd3=fill_yd3,
        net_yd3=net_yd3,
        area_sf=area_sf,
        method="tin",
        confidence=confidence
    )


def _interpolate_elevation(surface: TINSurface, x: float, y: float) -> Optional[float]:
    """Interpolate elevation at a point using TIN surface."""
    # Find triangle containing the point
    for triangle in surface.triangles:
        p1 = surface.points[triangle[0]]
        p2 = surface.points[triangle[1]]
        p3 = surface.points[triangle[2]]
        
        if _point_in_triangle(x, y, p1, p2, p3):
            # Interpolate elevation using barycentric coordinates
            return _barycentric_interpolation(x, y, p1, p2, p3)
    
    return None


def _point_in_triangle(x: float, y: float, p1: ContourPoint, p2: ContourPoint, p3: ContourPoint) -> bool:
    """Check if point is inside triangle."""
    # Use barycentric coordinates
    denom = (p2.y_ft - p3.y_ft) * (p1.x_ft - p3.x_ft) + (p3.x_ft - p2.x_ft) * (p1.y_ft - p3.y_ft)
    if abs(denom) < 1e-10:
        return False
    
    a = ((p2.y_ft - p3.y_ft) * (x - p3.x_ft) + (p3.x_ft - p2.x_ft) * (y - p3.y_ft)) / denom
    b = ((p3.y_ft - p1.y_ft) * (x - p3.x_ft) + (p1.x_ft - p3.x_ft) * (y - p3.y_ft)) / denom
    c = 1 - a - b
    
    return 0 <= a <= 1 and 0 <= b <= 1 and 0 <= c <= 1


def _barycentric_interpolation(x: float, y: float, p1: ContourPoint, p2: ContourPoint, p3: ContourPoint) -> float:
    """Interpolate elevation using barycentric coordinates."""
    denom = (p2.y_ft - p3.y_ft) * (p1.x_ft - p3.x_ft) + (p3.x_ft - p2.x_ft) * (p1.y_ft - p3.y_ft)
    a = ((p2.y_ft - p3.y_ft) * (x - p3.x_ft) + (p3.x_ft - p2.x_ft) * (y - p3.y_ft)) / denom
    b = ((p3.y_ft - p1.y_ft) * (x - p3.x_ft) + (p1.x_ft - p3.x_ft) * (y - p3.y_ft)) / denom
    c = 1 - a - b
    
    return a * p1.elevation_ft + b * p2.elevation_ft + c * p3.elevation_ft


def _calculate_confidence(existing_surface: Optional[TINSurface], proposed_surface: Optional[TINSurface]) -> float:
    """Calculate confidence in the earthwork estimate."""
    confidence = 0.0
    
    if existing_surface:
        confidence += 0.5
        # Higher confidence with more points
        if len(existing_surface.points) > 10:
            confidence += 0.2
    
    if proposed_surface:
        confidence += 0.5
        # Higher confidence with more points
        if len(proposed_surface.points) > 10:
            confidence += 0.2
    
    return min(confidence, 1.0)


def compare_earthwork_estimates(
    table_estimate: float, 
    surface_estimate: float, 
    tolerance_percent: float = 20.0
) -> Dict[str, Any]:
    """Compare earthwork estimates from different methods."""
    if table_estimate == 0:
        return {
            "match": False,
            "difference_percent": float('inf'),
            "warning": "Table estimate is zero"
        }
    
    difference_percent = abs(surface_estimate - table_estimate) / abs(table_estimate) * 100
    match = difference_percent <= tolerance_percent
    
    return {
        "match": match,
        "difference_percent": difference_percent,
        "table_estimate": table_estimate,
        "surface_estimate": surface_estimate,
        "tolerance_percent": tolerance_percent
    }
