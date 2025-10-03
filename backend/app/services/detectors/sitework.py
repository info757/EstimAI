"""Sitework measurement and quantification utilities."""
import re
import math
from typing import List, Dict, Any, Tuple, Optional
import logging

from ..ingest.extract import VectorEl, TextEl
from ..ingest.scale import ScaleInfo, to_world, len_world
from ...domain.networks import Node

logger = logging.getLogger(__name__)


def measure_curb_lf(vectors: List[VectorEl], symbol_map: Dict[str, Any]) -> float:
    """
    Measure total curb length in linear feet.
    
    Args:
        vectors: List of vector elements
        symbol_map: Symbol mapping dictionary
        
    Returns:
        Total curb length in linear feet
    """
    curb_length = 0.0
    
    # Get curb-related symbols from symbol map
    curb_symbols = _get_curb_symbols(symbol_map)
    
    # Find curb vectors
    curb_vectors = [v for v in vectors if _is_curb(v, curb_symbols)]
    
    # Calculate total length
    for vector in curb_vectors:
        if len(vector.points) >= 2:
            length = _calculate_vector_length(vector)
            curb_length += length
    
    logger.info(f"Measured {curb_length:.2f} LF of curb")
    return curb_length


def measure_sidewalk_sf(vectors: List[VectorEl], symbol_map: Dict[str, Any], default_width_ft: Optional[float] = None) -> float:
    """
    Measure total sidewalk area in square feet.
    
    Args:
        vectors: List of vector elements
        symbol_map: Symbol mapping dictionary
        default_width_ft: Default sidewalk width if not specified in drawing
        
    Returns:
        Total sidewalk area in square feet
    """
    sidewalk_area = 0.0
    
    # Get sidewalk-related symbols from symbol map
    sidewalk_symbols = _get_sidewalk_symbols(symbol_map)
    
    # Find sidewalk vectors
    sidewalk_vectors = [v for v in vectors if _is_sidewalk(v, sidewalk_symbols)]
    
    # Calculate area for each sidewalk
    for vector in sidewalk_vectors:
        if len(vector.points) >= 2:
            length = _calculate_vector_length(vector)
            width = _get_sidewalk_width(vector, default_width_ft)
            area = length * width
            sidewalk_area += area
    
    logger.info(f"Measured {sidewalk_area:.2f} SF of sidewalk")
    return sidewalk_area


def measure_silt_fence_lf(vectors: List[VectorEl], symbol_map: Dict[str, Any]) -> float:
    """
    Measure total silt fence length in linear feet.
    
    Args:
        vectors: List of vector elements
        symbol_map: Symbol mapping dictionary
        
    Returns:
        Total silt fence length in linear feet
    """
    silt_fence_length = 0.0
    
    # Get silt fence-related symbols from symbol map
    silt_fence_symbols = _get_silt_fence_symbols(symbol_map)
    
    # Find silt fence vectors
    silt_fence_vectors = [v for v in vectors if _is_silt_fence(v, silt_fence_symbols)]
    
    # Calculate total length
    for vector in silt_fence_vectors:
        if len(vector.points) >= 2:
            length = _calculate_vector_length(vector)
            silt_fence_length += length
    
    logger.info(f"Measured {silt_fence_length:.2f} LF of silt fence")
    return silt_fence_length


def count_inlet_protections(nodes: List[Node], texts: List[TextEl]) -> int:
    """
    Count inlet protection devices.
    
    Args:
        nodes: List of network nodes
        texts: List of text elements
        
    Returns:
        Number of inlet protection devices
    """
    inlet_protections = 0
    
    # Look for inlet protection text labels
    protection_keywords = ["INLET PROTECTION", "INLET FILTER", "SILT SOCK", "FILTER FABRIC"]
    
    for text in texts:
        text_content = text.text.upper().strip()
        for keyword in protection_keywords:
            if keyword in text_content:
                inlet_protections += 1
                break
    
    # Look for inlet protection symbols near inlets
    for node in nodes:
        if node.node_type.value == "inlet":
            nearby_texts = _find_nearby_texts(node, texts)
            for text in nearby_texts:
                text_content = text.text.upper().strip()
                for keyword in protection_keywords:
                    if keyword in text_content:
                        inlet_protections += 1
                        break
    
    logger.info(f"Counted {inlet_protections} inlet protection devices")
    return inlet_protections


def _get_curb_symbols(symbol_map: Dict[str, Any]) -> Dict[str, Any]:
    """Get curb-related symbols from symbol map."""
    curb_symbols = {}
    
    if "symbols" not in symbol_map:
        return curb_symbols
    
    symbols = symbol_map["symbols"]
    
    # Look for curb-related symbols
    curb_keywords = ["curb", "gutter", "edge", "border"]
    
    for symbol_name, symbol_data in symbols.items():
        symbol_name_lower = symbol_name.lower()
        layer_hints = symbol_data.get("layer_hint", [])
        
        # Check if symbol is curb-related
        is_curb = any(keyword in symbol_name_lower for keyword in curb_keywords)
        is_curb_layer = any("curb" in layer.lower() for layer in layer_hints)
        
        if is_curb or is_curb_layer:
            curb_symbols[symbol_name] = symbol_data
    
    return curb_symbols


def _get_sidewalk_symbols(symbol_map: Dict[str, Any]) -> Dict[str, Any]:
    """Get sidewalk-related symbols from symbol map."""
    sidewalk_symbols = {}
    
    if "symbols" not in symbol_map:
        return sidewalk_symbols
    
    symbols = symbol_map["symbols"]
    
    # Look for sidewalk-related symbols
    sidewalk_keywords = ["sidewalk", "walk", "pedestrian", "path"]
    
    for symbol_name, symbol_data in symbols.items():
        symbol_name_lower = symbol_name.lower()
        layer_hints = symbol_data.get("layer_hint", [])
        
        # Check if symbol is sidewalk-related
        is_sidewalk = any(keyword in symbol_name_lower for keyword in sidewalk_keywords)
        is_sidewalk_layer = any("sidewalk" in layer.lower() for layer in layer_hints)
        
        if is_sidewalk or is_sidewalk_layer:
            sidewalk_symbols[symbol_name] = symbol_data
    
    return sidewalk_symbols


def _get_silt_fence_symbols(symbol_map: Dict[str, Any]) -> Dict[str, Any]:
    """Get silt fence-related symbols from symbol map."""
    silt_fence_symbols = {}
    
    if "symbols" not in symbol_map:
        return silt_fence_symbols
    
    symbols = symbol_map["symbols"]
    
    # Look for silt fence-related symbols
    silt_fence_keywords = ["silt", "fence", "barrier", "filter"]
    
    for symbol_name, symbol_data in symbols.items():
        symbol_name_lower = symbol_name.lower()
        layer_hints = symbol_data.get("layer_hint", [])
        
        # Check if symbol is silt fence-related
        is_silt_fence = any(keyword in symbol_name_lower for keyword in silt_fence_keywords)
        is_silt_fence_layer = any("silt" in layer.lower() for layer in layer_hints)
        
        if is_silt_fence or is_silt_fence_layer:
            silt_fence_symbols[symbol_name] = symbol_data
    
    return silt_fence_symbols


def _is_curb(vector: VectorEl, curb_symbols: Dict[str, Any]) -> bool:
    """Check if vector represents a curb."""
    # Check against curb symbols
    for symbol_name, symbol_data in curb_symbols.items():
        if _matches_symbol(vector, symbol_data):
            return True
    
    # Check for curb patterns (lines and polylines)
    if vector.kind in ["line", "polyline"] and vector.stroke_w > 0:
        return True
    
    return False


def _is_sidewalk(vector: VectorEl, sidewalk_symbols: Dict[str, Any]) -> bool:
    """Check if vector represents a sidewalk."""
    # Check against sidewalk symbols
    for symbol_name, symbol_data in sidewalk_symbols.items():
        if _matches_symbol(vector, symbol_data):
            return True
    
    # Check for sidewalk patterns (lines, polylines, and polygons)
    if vector.kind in ["line", "polyline", "polygon"] and vector.stroke_w > 0:
        return True
    
    return False


def _is_silt_fence(vector: VectorEl, silt_fence_symbols: Dict[str, Any]) -> bool:
    """Check if vector represents a silt fence."""
    # Check against silt fence symbols
    for symbol_name, symbol_data in silt_fence_symbols.items():
        if _matches_symbol(vector, symbol_data):
            return True
    
    # Check for silt fence patterns (lines and polylines)
    if vector.kind in ["line", "polyline"] and vector.stroke_w > 0:
        return True
    
    return False


def _matches_symbol(vector: VectorEl, symbol_data: Dict[str, Any]) -> bool:
    """Check if vector matches symbol data."""
    # Check shape hints
    shape_data = symbol_data.get("shape", {})
    if shape_data:
        for shape_type, count in shape_data.items():
            if count > 0:
                if shape_type == "line" and vector.kind in ["line", "polyline"]:
                    return True
                elif shape_type == "polygon" and vector.kind == "polygon":
                    return True
    
    # Check vector characteristics
    vector_data = symbol_data.get("vector", {})
    if vector_data:
        if "stroke_min" in vector_data and vector.stroke_w < vector_data["stroke_min"]:
            return False
        if "stroke_max" in vector_data and vector.stroke_w > vector_data["stroke_max"]:
            return False
        if "double_line" in vector_data and vector_data["double_line"]:
            # Check for double line pattern (simplified)
            return vector.stroke_w > 2.0
    
    return True


def _calculate_vector_length(vector: VectorEl) -> float:
    """Calculate length of a vector element."""
    if len(vector.points) < 2:
        return 0.0
    
    length = 0.0
    for i in range(len(vector.points) - 1):
        x1, y1 = vector.points[i]
        x2, y2 = vector.points[i + 1]
        length += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    
    return length


def _get_sidewalk_width(vector: VectorEl, default_width_ft: Optional[float] = None) -> float:
    """Get sidewalk width from vector or use default."""
    # Try to extract width from vector attributes
    if "width_ft" in vector.attributes:
        return vector.attributes["width_ft"]
    
    # Try to extract width from vector name or description
    if hasattr(vector, 'name') and vector.name:
        width_match = re.search(r'(\d+(?:\.\d+)?)\s*["\"]?\s*WIDE', vector.name, re.IGNORECASE)
        if width_match:
            return float(width_match.group(1))
    
    # Use default width if provided
    if default_width_ft:
        return default_width_ft
    
    # Default sidewalk width (typically 4-6 feet)
    return 5.0


def _find_nearby_texts(node: Node, texts: List[TextEl]) -> List[TextEl]:
    """Find text elements near a node."""
    nearby_texts = []
    tolerance = 50.0  # feet
    
    for text in texts:
        if _text_near_node(text, node, tolerance):
            nearby_texts.append(text)
    
    return nearby_texts


def _text_near_node(text: TextEl, node: Node, tolerance: float) -> bool:
    """Check if text is near a node."""
    # Get text center
    text_center = ((text.bbox[0] + text.bbox[2]) / 2, (text.bbox[1] + text.bbox[3]) / 2)
    
    # Check distance to node
    distance = math.sqrt((text_center[0] - node.x_ft) ** 2 + (text_center[1] - node.y_ft) ** 2)
    return distance <= tolerance


def measure_pavement_sf(vectors: List[VectorEl], symbol_map: Dict[str, Any]) -> float:
    """
    Measure total pavement area in square feet.
    
    Args:
        vectors: List of vector elements
        symbol_map: Symbol mapping dictionary
        
    Returns:
        Total pavement area in square feet
    """
    pavement_area = 0.0
    
    # Get pavement-related symbols from symbol map
    pavement_symbols = _get_pavement_symbols(symbol_map)
    
    # Find pavement vectors
    pavement_vectors = [v for v in vectors if _is_pavement(v, pavement_symbols)]
    
    # Calculate area for each pavement
    for vector in pavement_vectors:
        if vector.kind == "polygon" and len(vector.points) >= 3:
            area = _calculate_polygon_area(vector.points)
            pavement_area += area
    
    logger.info(f"Measured {pavement_area:.2f} SF of pavement")
    return pavement_area


def _get_pavement_symbols(symbol_map: Dict[str, Any]) -> Dict[str, Any]:
    """Get pavement-related symbols from symbol map."""
    pavement_symbols = {}
    
    if "symbols" not in symbol_map:
        return pavement_symbols
    
    symbols = symbol_map["symbols"]
    
    # Look for pavement-related symbols
    pavement_keywords = ["pavement", "asphalt", "concrete", "road", "street", "driveway"]
    
    for symbol_name, symbol_data in symbols.items():
        symbol_name_lower = symbol_name.lower()
        layer_hints = symbol_data.get("layer_hint", [])
        
        # Check if symbol is pavement-related
        is_pavement = any(keyword in symbol_name_lower for keyword in pavement_keywords)
        is_pavement_layer = any("pavement" in layer.lower() for layer in layer_hints)
        
        if is_pavement or is_pavement_layer:
            pavement_symbols[symbol_name] = symbol_data
    
    return pavement_symbols


def _is_pavement(vector: VectorEl, pavement_symbols: Dict[str, Any]) -> bool:
    """Check if vector represents pavement."""
    # Check against pavement symbols
    for symbol_name, symbol_data in pavement_symbols.items():
        if _matches_symbol(vector, symbol_data):
            return True
    
    # Check for pavement patterns (polygons)
    if vector.kind == "polygon" and len(vector.points) >= 3:
        return True
    
    return False


def _calculate_polygon_area(points: List[Tuple[float, float]]) -> float:
    """Calculate area of a polygon using the shoelace formula."""
    if len(points) < 3:
        return 0.0
    
    area = 0.0
    n = len(points)
    
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    
    return abs(area) / 2.0


def measure_landscaping_sf(vectors: List[VectorEl], symbol_map: Dict[str, Any]) -> float:
    """
    Measure total landscaping area in square feet.
    
    Args:
        vectors: List of vector elements
        symbol_map: Symbol mapping dictionary
        
    Returns:
        Total landscaping area in square feet
    """
    landscaping_area = 0.0
    
    # Get landscaping-related symbols from symbol map
    landscaping_symbols = _get_landscaping_symbols(symbol_map)
    
    # Find landscaping vectors
    landscaping_vectors = [v for v in vectors if _is_landscaping(v, landscaping_symbols)]
    
    # Calculate area for each landscaping
    for vector in landscaping_vectors:
        if vector.kind == "polygon" and len(vector.points) >= 3:
            area = _calculate_polygon_area(vector.points)
            landscaping_area += area
    
    logger.info(f"Measured {landscaping_area:.2f} SF of landscaping")
    return landscaping_area


def _get_landscaping_symbols(symbol_map: Dict[str, Any]) -> Dict[str, Any]:
    """Get landscaping-related symbols from symbol map."""
    landscaping_symbols = {}
    
    if "symbols" not in symbol_map:
        return landscaping_symbols
    
    symbols = symbol_map["symbols"]
    
    # Look for landscaping-related symbols
    landscaping_keywords = ["landscaping", "landscape", "grass", "lawn", "shrub", "tree", "planting"]
    
    for symbol_name, symbol_data in symbols.items():
        symbol_name_lower = symbol_name.lower()
        layer_hints = symbol_data.get("layer_hint", [])
        
        # Check if symbol is landscaping-related
        is_landscaping = any(keyword in symbol_name_lower for keyword in landscaping_keywords)
        is_landscaping_layer = any("landscaping" in layer.lower() for layer in layer_hints)
        
        if is_landscaping or is_landscaping_layer:
            landscaping_symbols[symbol_name] = symbol_data
    
    return landscaping_symbols


def _is_landscaping(vector: VectorEl, landscaping_symbols: Dict[str, Any]) -> bool:
    """Check if vector represents landscaping."""
    # Check against landscaping symbols
    for symbol_name, symbol_data in landscaping_symbols.items():
        if _matches_symbol(vector, symbol_data):
            return True
    
    # Check for landscaping patterns (polygons)
    if vector.kind == "polygon" and len(vector.points) >= 3:
        return True
    
    return False
