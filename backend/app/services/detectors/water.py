"""Water distribution network detection and extraction."""
import re
import math
import uuid
from typing import List, Dict, Any, Tuple, Optional
import logging

from ..ingest.extract import VectorEl, TextEl
from ..ingest.scale import ScaleInfo, to_world
from ...domain.networks import Node, Edge, NodeType, EdgeType, Material, Network

logger = logging.getLogger(__name__)


def detect_nodes(vectors: List[VectorEl], texts: List[TextEl], symbol_map: Dict[str, Any]) -> List[Node]:
    """
    Detect water distribution network nodes from vectors and texts.
    
    Args:
        vectors: List of vector elements
        texts: List of text elements
        symbol_map: Symbol mapping dictionary
        
    Returns:
        List of detected nodes
    """
    nodes = []
    
    # Get water-related symbols from symbol map
    water_symbols = _get_water_symbols(symbol_map)
    
    # Detect hydrants
    for vector in vectors:
        if _is_hydrant(vector, water_symbols):
            node = _create_node_from_vector(vector, NodeType.HYDRANT)
            if node:
                nodes.append(node)
    
    # Detect valves
    for vector in vectors:
        if _is_valve(vector, water_symbols):
            node = _create_node_from_vector(vector, NodeType.VALVE)
            if node:
                nodes.append(node)
    
    # Detect meters
    for vector in vectors:
        if _is_meter(vector, water_symbols):
            node = _create_node_from_vector(vector, NodeType.METER)
            if node:
                nodes.append(node)
    
    # Detect junctions (intersections of water lines)
    junctions = _detect_junctions(vectors, water_symbols)
    nodes.extend(junctions)
    
    logger.info(f"Detected {len(nodes)} water distribution nodes")
    return nodes


def trace_edges(vectors: List[VectorEl], symbol_map: Dict[str, Any]) -> List[Edge]:
    """
    Trace water distribution network edges from vectors.
    
    Args:
        vectors: List of vector elements
        symbol_map: Symbol mapping dictionary
        
    Returns:
        List of traced edges
    """
    edges = []
    
    # Get water-related symbols from symbol map
    water_symbols = _get_water_symbols(symbol_map)
    
    # Find water pipe vectors
    water_pipes = [v for v in vectors if _is_water_pipe(v, water_symbols)]
    
    # Merge connected polylines
    merged_pipes = _merge_connected_polylines(water_pipes)
    
    # Create edges from merged pipes
    for pipe in merged_pipes:
        edge = _create_edge_from_vector(pipe)
        if edge:
            edges.append(edge)
    
    logger.info(f"Traced {len(edges)} water distribution edges")
    return edges


def attach_labels(edges: List[Edge], texts: List[TextEl]) -> List[Edge]:
    """
    Attach labels to water distribution edges.
    
    Args:
        edges: List of edges to label
        texts: List of text elements
        
    Returns:
        List of edges with attached labels
    """
    labeled_edges = []
    
    for edge in edges:
        # Find nearby text labels
        nearby_texts = _find_nearby_texts(edge, texts)
        
        # Parse labels for diameter, material, etc.
        parsed_labels = _parse_water_labels(nearby_texts)
        
        # Attach parsed information to edge
        if parsed_labels:
            edge.attributes.update(parsed_labels)
            
            # Update edge properties from labels
            if "diameter_in" in parsed_labels:
                edge.diameter_in = parsed_labels["diameter_in"]
            if "material" in parsed_labels:
                edge.material = parsed_labels["material"]
            if "pressure_psi" in parsed_labels:
                edge.attributes["pressure_psi"] = parsed_labels["pressure_psi"]
        
        labeled_edges.append(edge)
    
    logger.info(f"Attached labels to {len(labeled_edges)} edges")
    return labeled_edges


def _get_water_symbols(symbol_map: Dict[str, Any]) -> Dict[str, Any]:
    """Get water-related symbols from symbol map."""
    water_symbols = {}
    
    if "symbols" not in symbol_map:
        return water_symbols
    
    symbols = symbol_map["symbols"]
    
    # Look for water-related symbols
    water_keywords = ["water", "hydrant", "valve", "meter", "pipe", "conduit", "main"]
    
    for symbol_name, symbol_data in symbols.items():
        symbol_name_lower = symbol_name.lower()
        layer_hints = symbol_data.get("layer_hint", [])
        
        # Check if symbol is water-related
        is_water = any(keyword in symbol_name_lower for keyword in water_keywords)
        is_water_layer = any("water" in layer.lower() for layer in layer_hints)
        
        if is_water or is_water_layer:
            water_symbols[symbol_name] = symbol_data
    
    return water_symbols


def _is_hydrant(vector: VectorEl, water_symbols: Dict[str, Any]) -> bool:
    """Check if vector represents a hydrant."""
    # Check against water symbols
    for symbol_name, symbol_data in water_symbols.items():
        if "hydrant" in symbol_name.lower() and _matches_symbol(vector, symbol_data):
            return True
    
    # Check for hydrant patterns (circle with crossbar)
    if vector.kind == "circle" and vector.stroke_w > 0:
        return True
    
    # Check for hydrant symbol patterns (circle with line through it)
    if vector.kind == "polygon" and len(vector.points) >= 4:
        return True
    
    return False


def _is_valve(vector: VectorEl, water_symbols: Dict[str, Any]) -> bool:
    """Check if vector represents a valve."""
    # Check against water symbols
    for symbol_name, symbol_data in water_symbols.items():
        if "valve" in symbol_name.lower() and _matches_symbol(vector, symbol_data):
            return True
    
    # Check for valve patterns (small circles or squares)
    if vector.kind == "circle" and vector.stroke_w > 0:
        # Check size (valves are typically smaller than hydrants)
        bbox = _get_vector_bbox(vector)
        if bbox:
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            if width < 8.0 and height < 8.0:  # Small size threshold
                return True
    
    if vector.kind == "rect":
        bbox = _get_vector_bbox(vector)
        if bbox:
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            if width < 8.0 and height < 8.0:  # Small size threshold
                return True
    
    return False


def _is_meter(vector: VectorEl, water_symbols: Dict[str, Any]) -> bool:
    """Check if vector represents a meter."""
    # Check against water symbols
    for symbol_name, symbol_data in water_symbols.items():
        if "meter" in symbol_name.lower() and _matches_symbol(vector, symbol_data):
            return True
    
    # Check for meter patterns (small circles or rectangles)
    if vector.kind == "circle" and vector.stroke_w > 0:
        # Check size (meters are typically small)
        bbox = _get_vector_bbox(vector)
        if bbox:
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            if width < 6.0 and height < 6.0:  # Small size threshold
                return True
    
    if vector.kind == "rect":
        bbox = _get_vector_bbox(vector)
        if bbox:
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            if width < 6.0 and height < 6.0:  # Small size threshold
                return True
    
    return False


def _is_water_pipe(vector: VectorEl, water_symbols: Dict[str, Any]) -> bool:
    """Check if vector represents a water pipe."""
    # Check against water symbols
    for symbol_name, symbol_data in water_symbols.items():
        if "pipe" in symbol_name.lower() and _matches_symbol(vector, symbol_data):
            return True
    
    # Check for pipe patterns (lines and polylines)
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
                if shape_type == "circle" and vector.kind == "circle":
                    return True
                elif shape_type == "line" and vector.kind in ["line", "polyline"]:
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


def _create_node_from_vector(vector: VectorEl, node_type: NodeType) -> Optional[Node]:
    """Create a node from a vector element."""
    try:
        # Get center point of vector
        center = _get_vector_center(vector)
        if not center:
            return None
        
        # Create node
        node = Node(
            id=str(uuid.uuid4()),
            node_type=node_type,
            x_ft=center[0],
            y_ft=center[1],
            attributes={
                "source_vector": vector.kind,
                "stroke_width": vector.stroke_w,
                "stroke_color": vector.stroke_rgba,
                "fill_color": vector.fill_rgba
            }
        )
        
        return node
        
    except Exception as e:
        logger.error(f"Error creating node from vector: {e}")
        return None


def _create_edge_from_vector(vector: VectorEl) -> Optional[Edge]:
    """Create an edge from a vector element."""
    try:
        if len(vector.points) < 2:
            return None
        
        # Create edge
        edge = Edge(
            id=str(uuid.uuid4()),
            edge_type=EdgeType.PIPE,
            from_node_id="",  # Will be set when connecting to nodes
            to_node_id="",    # Will be set when connecting to nodes
            points_ft=vector.points,
            attributes={
                "source_vector": vector.kind,
                "stroke_width": vector.stroke_w,
                "stroke_color": vector.stroke_rgba,
                "fill_color": vector.fill_rgba
            }
        )
        
        # Calculate length
        length = 0.0
        for i in range(len(vector.points) - 1):
            x1, y1 = vector.points[i]
            x2, y2 = vector.points[i + 1]
            length += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        edge.length_ft = length
        
        return edge
        
    except Exception as e:
        logger.error(f"Error creating edge from vector: {e}")
        return None


def _detect_junctions(vectors: List[VectorEl], water_symbols: Dict[str, Any]) -> List[Node]:
    """Detect junctions where water lines intersect."""
    junctions = []
    
    # Find intersection points
    intersection_points = _find_line_intersections(vectors)
    
    for point in intersection_points:
        node = Node(
            id=str(uuid.uuid4()),
            node_type=NodeType.JUNCTION,
            x_ft=point[0],
            y_ft=point[1],
            attributes={
                "junction_type": "intersection",
                "intersection_count": point[2] if len(point) > 2 else 2
            }
        )
        junctions.append(node)
    
    return junctions


def _find_line_intersections(vectors: List[VectorEl]) -> List[Tuple[float, float, int]]:
    """Find intersection points between lines."""
    intersections = []
    
    # Get all line segments
    segments = []
    for vector in vectors:
        if vector.kind in ["line", "polyline"]:
            for i in range(len(vector.points) - 1):
                segments.append((vector.points[i], vector.points[i + 1]))
    
    # Find intersections
    for i, seg1 in enumerate(segments):
        for j, seg2 in enumerate(segments[i + 1:], i + 1):
            intersection = _line_intersection(seg1, seg2)
            if intersection:
                intersections.append((intersection[0], intersection[1], 2))
    
    return intersections


def _line_intersection(seg1: Tuple[Tuple[float, float], Tuple[float, float]], 
                      seg2: Tuple[Tuple[float, float], Tuple[float, float]]) -> Optional[Tuple[float, float]]:
    """Find intersection point between two line segments."""
    # Simplified line intersection (would need more robust implementation)
    return None


def _merge_connected_polylines(pipes: List[VectorEl]) -> List[VectorEl]:
    """Merge connected polylines into single edges."""
    if not pipes:
        return []
    
    merged = []
    used = set()
    
    for i, pipe in enumerate(pipes):
        if i in used:
            continue
        
        # Start with this pipe
        merged_pipe = pipe
        used.add(i)
        
        # Find connected pipes
        connected = True
        while connected:
            connected = False
            for j, other_pipe in enumerate(pipes):
                if j in used:
                    continue
                
                if _are_connected(merged_pipe, other_pipe):
                    merged_pipe = _merge_pipes(merged_pipe, other_pipe)
                    used.add(j)
                    connected = True
                    break
        
        merged.append(merged_pipe)
    
    return merged


def _are_connected(pipe1: VectorEl, pipe2: VectorEl) -> bool:
    """Check if two pipes are connected."""
    if not pipe1.points or not pipe2.points:
        return False
    
    # Check if endpoints are close
    tolerance = 5.0  # feet
    
    p1_start = pipe1.points[0]
    p1_end = pipe1.points[-1]
    p2_start = pipe2.points[0]
    p2_end = pipe2.points[-1]
    
    # Check all combinations
    if _points_close(p1_start, p2_start, tolerance):
        return True
    if _points_close(p1_start, p2_end, tolerance):
        return True
    if _points_close(p1_end, p2_start, tolerance):
        return True
    if _points_close(p1_end, p2_end, tolerance):
        return True
    
    return False


def _points_close(p1: Tuple[float, float], p2: Tuple[float, float], tolerance: float) -> bool:
    """Check if two points are close within tolerance."""
    distance = math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
    return distance <= tolerance


def _merge_pipes(pipe1: VectorEl, pipe2: VectorEl) -> VectorEl:
    """Merge two connected pipes."""
    # Determine connection points and merge
    # This is a simplified implementation
    merged_points = pipe1.points + pipe2.points
    
    return VectorEl(
        kind="polyline",
        points=merged_points,
        stroke_rgba=pipe1.stroke_rgba,
        fill_rgba=pipe1.fill_rgba,
        stroke_w=pipe1.stroke_w,
        ocg_names=pipe1.ocg_names,
        xform=pipe1.xform
    )


def _find_nearby_texts(edge: Edge, texts: List[TextEl]) -> List[TextEl]:
    """Find text elements near an edge."""
    nearby_texts = []
    tolerance = 50.0  # feet
    
    for text in texts:
        if _text_near_edge(text, edge, tolerance):
            nearby_texts.append(text)
    
    return nearby_texts


def _text_near_edge(text: TextEl, edge: Edge, tolerance: float) -> bool:
    """Check if text is near an edge."""
    # Get text center
    text_center = ((text.bbox[0] + text.bbox[2]) / 2, (text.bbox[1] + text.bbox[3]) / 2)
    
    # Check distance to edge points
    for point in edge.points_ft:
        distance = math.sqrt((text_center[0] - point[0]) ** 2 + (text_center[1] - point[1]) ** 2)
        if distance <= tolerance:
            return True
    
    return False


def _parse_water_labels(texts: List[TextEl]) -> Dict[str, Any]:
    """Parse water distribution labels from text elements."""
    labels = {}
    
    for text in texts:
        text_content = text.text.strip()
        
        # Parse diameter (e.g., "12\"", "dia 12", "12 inch")
        diameter_match = re.search(r'(\d+(?:\.\d+)?)\s*["\"]', text_content)
        if diameter_match:
            labels["diameter_in"] = float(diameter_match.group(1))
        
        # Parse material
        material_match = re.search(r'(PVC|CONCRETE|DUCTILE|CAST|HDPE|STEEL|COPPER)', text_content, re.IGNORECASE)
        if material_match:
            material_name = material_match.group(1).upper()
            if material_name == "PVC":
                labels["material"] = Material.PVC
            elif material_name == "CONCRETE":
                labels["material"] = Material.CONCRETE
            elif material_name == "DUCTILE":
                labels["material"] = Material.DUCTILE_IRON
            elif material_name == "CAST":
                labels["material"] = Material.CAST_IRON
            elif material_name == "HDPE":
                labels["material"] = Material.HDPE
            elif material_name == "STEEL":
                labels["material"] = Material.STEEL
        
        # Parse pressure (e.g., "150 PSI", "150 psi")
        pressure_match = re.search(r'(\d+(?:\.\d+)?)\s*PSI', text_content, re.IGNORECASE)
        if pressure_match:
            labels["pressure_psi"] = float(pressure_match.group(1))
        
        # Parse flow rate (e.g., "100 GPM", "100 gpm")
        flow_match = re.search(r'(\d+(?:\.\d+)?)\s*GPM', text_content, re.IGNORECASE)
        if flow_match:
            labels["flow_gpm"] = float(flow_match.group(1))
        
        # Parse valve type (e.g., "GATE", "BALL", "BUTTERFLY")
        valve_match = re.search(r'(GATE|BALL|BUTTERFLY|CHECK|PRESSURE)', text_content, re.IGNORECASE)
        if valve_match:
            labels["valve_type"] = valve_match.group(1).upper()
        
        # Parse hydrant type (e.g., "DRY", "WET", "WALL")
        hydrant_match = re.search(r'(DRY|WET|WALL|FLUSH)', text_content, re.IGNORECASE)
        if hydrant_match:
            labels["hydrant_type"] = hydrant_match.group(1).upper()
    
    return labels


def _get_vector_center(vector: VectorEl) -> Optional[Tuple[float, float]]:
    """Get center point of a vector."""
    if not vector.points:
        return None
    
    if len(vector.points) == 1:
        return vector.points[0]
    
    # Calculate centroid
    x_sum = sum(point[0] for point in vector.points)
    y_sum = sum(point[1] for point in vector.points)
    
    return (x_sum / len(vector.points), y_sum / len(vector.points))


def _get_vector_bbox(vector: VectorEl) -> Optional[Tuple[float, float, float, float]]:
    """Get bounding box of a vector."""
    if not vector.points:
        return None
    
    min_x = min(point[0] for point in vector.points)
    min_y = min(point[1] for point in vector.points)
    max_x = max(point[0] for point in vector.points)
    max_y = max(point[1] for point in vector.points)
    
    return (min_x, min_y, max_x, max_y)
