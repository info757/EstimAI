"""Vector and text extraction utilities for PDF processing."""
from typing import List, Tuple, Optional, Any
from dataclasses import dataclass
import logging
import math

from .pdfnet_runtime import Page, PDFDoc

logger = logging.getLogger(__name__)


@dataclass
class VectorEl:
    """Vector element extracted from PDF."""
    kind: str  # "line", "polyline", "polygon", "rect", "circle", etc.
    points: List[Tuple[float, float]]  # Coordinate points
    stroke_rgba: Tuple[int, int, int, int]  # RGBA stroke color
    fill_rgba: Tuple[int, int, int, int]  # RGBA fill color
    stroke_w: float  # Stroke width
    ocg_names: List[str]  # Optional content group names
    xform: List[List[float]]  # Transformation matrix


@dataclass
class TextEl:
    """Text element extracted from PDF."""
    text: str  # Text content
    bbox: Tuple[float, float, float, float]  # Bounding box (x1, y1, x2, y2)
    ocg_names: List[str]  # Optional content group names


def extract_vectors(page: Page) -> List[VectorEl]:
    """
    Extract vector graphics from a PDF page.
    
    Args:
        page: PDFNet Page object
        
    Returns:
        List of VectorEl objects
    """
    vectors = []
    
    try:
        # Get page elements
        element = page.GetFirstElement()
        
        while element:
            vector = _extract_vector_from_element(element)
            if vector:
                vectors.append(vector)
            
            element = element.GetNext()
        
        # Also check for XObjects (nested content)
        vectors.extend(_extract_vectors_from_xobjects(page))
        
    except Exception as e:
        logger.error(f"Error extracting vectors from page: {e}")
    
    return vectors


def _extract_vector_from_element(element) -> Optional[VectorEl]:
    """Extract vector information from a PDF element."""
    try:
        # Get element type
        element_type = element.GetType()
        
        if element_type == "Path":  # Line, polyline, polygon, etc.
            return _extract_path_element(element)
        elif element_type == "Rect":  # Rectangle
            return _extract_rect_element(element)
        elif element_type == "Circle":  # Circle
            return _extract_circle_element(element)
        elif element_type == "Ellipse":  # Ellipse
            return _extract_ellipse_element(element)
        
        return None
        
    except Exception as e:
        logger.debug(f"Error extracting vector from element: {e}")
        return None


def _extract_path_element(element) -> Optional[VectorEl]:
    """Extract path element (lines, polylines, polygons)."""
    try:
        # Get path data
        path_data = element.GetPathData()
        if not path_data:
            return None
        
        # Extract points from path data
        points = _parse_path_data(path_data)
        if not points:
            return None
        
        # Determine kind based on path characteristics
        kind = _determine_path_kind(path_data, points)
        
        # Get styling information
        stroke_rgba = _get_stroke_color(element)
        fill_rgba = _get_fill_color(element)
        stroke_w = _get_stroke_width(element)
        
        # Get transformation matrix
        xform = _get_transformation_matrix(element)
        
        # Get optional content groups
        ocg_names = _get_ocg_names(element)
        
        return VectorEl(
            kind=kind,
            points=points,
            stroke_rgba=stroke_rgba,
            fill_rgba=fill_rgba,
            stroke_w=stroke_w,
            ocg_names=ocg_names,
            xform=xform
        )
        
    except Exception as e:
        logger.debug(f"Error extracting path element: {e}")
        return None


def _extract_rect_element(element) -> Optional[VectorEl]:
    """Extract rectangle element."""
    try:
        # Get rectangle bounds
        bbox = element.GetBBox()
        if not bbox:
            return None
        
        x1, y1, x2, y2 = bbox
        
        # Create rectangle points
        points = [
            (x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)
        ]
        
        # Get styling
        stroke_rgba = _get_stroke_color(element)
        fill_rgba = _get_fill_color(element)
        stroke_w = _get_stroke_width(element)
        xform = _get_transformation_matrix(element)
        ocg_names = _get_ocg_names(element)
        
        return VectorEl(
            kind="rect",
            points=points,
            stroke_rgba=stroke_rgba,
            fill_rgba=fill_rgba,
            stroke_w=stroke_w,
            ocg_names=ocg_names,
            xform=xform
        )
        
    except Exception as e:
        logger.debug(f"Error extracting rect element: {e}")
        return None


def _extract_circle_element(element) -> Optional[VectorEl]:
    """Extract circle element."""
    try:
        # Get circle center and radius
        center = element.GetCenter()
        radius = element.GetRadius()
        
        if not center or radius <= 0:
            return None
        
        cx, cy = center
        
        # Create circle points (approximate with polygon)
        points = []
        num_segments = 32
        for i in range(num_segments + 1):
            angle = 2 * 3.14159 * i / num_segments
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            points.append((x, y))
        
        # Get styling
        stroke_rgba = _get_stroke_color(element)
        fill_rgba = _get_fill_color(element)
        stroke_w = _get_stroke_width(element)
        xform = _get_transformation_matrix(element)
        ocg_names = _get_ocg_names(element)
        
        return VectorEl(
            kind="circle",
            points=points,
            stroke_rgba=stroke_rgba,
            fill_rgba=fill_rgba,
            stroke_w=stroke_w,
            ocg_names=ocg_names,
            xform=xform
        )
        
    except Exception as e:
        logger.debug(f"Error extracting circle element: {e}")
        return None


def _extract_ellipse_element(element) -> Optional[VectorEl]:
    """Extract ellipse element."""
    try:
        # Get ellipse bounds
        bbox = element.GetBBox()
        if not bbox:
            return None
        
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        rx = (x2 - x1) / 2
        ry = (y2 - y1) / 2
        
        # Create ellipse points
        points = []
        num_segments = 32
        for i in range(num_segments + 1):
            angle = 2 * 3.14159 * i / num_segments
            x = cx + rx * math.cos(angle)
            y = cy + ry * math.sin(angle)
            points.append((x, y))
        
        # Get styling
        stroke_rgba = _get_stroke_color(element)
        fill_rgba = _get_fill_color(element)
        stroke_w = _get_stroke_width(element)
        xform = _get_transformation_matrix(element)
        ocg_names = _get_ocg_names(element)
        
        return VectorEl(
            kind="ellipse",
            points=points,
            stroke_rgba=stroke_rgba,
            fill_rgba=fill_rgba,
            stroke_w=stroke_w,
            ocg_names=ocg_names,
            xform=xform
        )
        
    except Exception as e:
        logger.debug(f"Error extracting ellipse element: {e}")
        return None


def _extract_vectors_from_xobjects(page: Page) -> List[VectorEl]:
    """Extract vectors from XObjects (nested content)."""
    vectors = []
    
    try:
        # This would require more complex PDFNet API usage
        # to traverse XObject content
        # For now, return empty list
        pass
        
    except Exception as e:
        logger.debug(f"Error extracting vectors from XObjects: {e}")
    
    return vectors


def extract_text(page: Page) -> List[TextEl]:
    """
    Extract text elements from a PDF page.
    
    Args:
        page: PDFNet Page object
        
    Returns:
        List of TextEl objects
    """
    text_elements = []
    
    try:
        # Get text content with positioning
        text_data = page.GetTextData()
        if not text_data:
            return text_elements
        
        # Parse text data to extract individual text elements
        for text_item in text_data:
            text = text_item.GetString()
            bbox = text_item.GetBBox()
            
            if text and bbox:
                x1, y1, x2, y2 = bbox
                bbox_tuple = (x1, y1, x2, y2)
                
                # Get optional content groups
                ocg_names = _get_text_ocg_names(text_item)
                
                text_elements.append(TextEl(
                    text=text,
                    bbox=bbox_tuple,
                    ocg_names=ocg_names
                ))
        
    except Exception as e:
        logger.error(f"Error extracting text from page: {e}")
    
    return text_elements


# Helper functions for element processing

def _parse_path_data(path_data) -> List[Tuple[float, float]]:
    """Parse PDF path data to extract coordinate points."""
    points = []
    
    try:
        # This is a simplified implementation
        # Real PDF path parsing is more complex
        # For now, return empty list
        pass
        
    except Exception as e:
        logger.debug(f"Error parsing path data: {e}")
    
    return points


def _determine_path_kind(path_data, points: List[Tuple[float, float]]) -> str:
    """Determine the kind of path based on path data and points."""
    if len(points) < 2:
        return "point"
    elif len(points) == 2:
        return "line"
    elif points[0] == points[-1]:
        return "polygon"
    else:
        return "polyline"


def _get_stroke_color(element) -> Tuple[int, int, int, int]:
    """Get stroke color as RGBA tuple."""
    try:
        # Default to black
        return (0, 0, 0, 255)
    except Exception:
        return (0, 0, 0, 255)


def _get_fill_color(element) -> Tuple[int, int, int, int]:
    """Get fill color as RGBA tuple."""
    try:
        # Default to transparent
        return (0, 0, 0, 0)
    except Exception:
        return (0, 0, 0, 0)


def _get_stroke_width(element) -> float:
    """Get stroke width."""
    try:
        # Default to 1.0
        return 1.0
    except Exception:
        return 1.0


def _get_transformation_matrix(element) -> List[List[float]]:
    """Get transformation matrix."""
    try:
        # Default to identity matrix
        return [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ]
    except Exception:
        return [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ]


def _get_ocg_names(element) -> List[str]:
    """Get optional content group names."""
    try:
        # Default to empty list
        return []
    except Exception:
        return []


def _get_text_ocg_names(text_item) -> List[str]:
    """Get optional content group names for text item."""
    try:
        # Default to empty list
        return []
    except Exception:
        return []
