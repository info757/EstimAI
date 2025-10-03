"""Legend detection and symbol snippet extraction utilities."""
import re
import math
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import logging

from ..ingest.extract import VectorEl, TextEl

logger = logging.getLogger(__name__)


@dataclass
class BBox:
    """Bounding box for legend regions."""
    x1: float
    y1: float
    x2: float
    y2: float
    
    def area(self) -> float:
        """Calculate area of bounding box."""
        return (self.x2 - self.x1) * (self.y2 - self.y1)
    
    def contains(self, x: float, y: float) -> bool:
        """Check if point is inside bounding box."""
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2
    
    def overlaps(self, other: 'BBox') -> bool:
        """Check if this bounding box overlaps with another."""
        return not (self.x2 < other.x1 or self.x1 > other.x2 or 
                   self.y2 < other.y1 or self.y1 > other.y2)


@dataclass
class SymbolSnippet:
    """Symbol snippet with associated metadata."""
    vectors: List[VectorEl]
    texts: List[TextEl]
    bbox: BBox
    stroke_pattern: str  # "solid", "dashed", "dotted", "double"
    stroke_width_stats: Dict[str, float]  # min, max, mean
    shape_hints: List[str]  # "circle", "line", "polygon", etc.
    adjacent_text: List[str]  # Text near the symbol


def find_legend_regions(texts: List[TextEl]) -> List[BBox]:
    """
    Find legend regions in the document based on text content.
    
    Looks for common legend indicators like:
    - "LEGEND"
    - "ABBREV" or "ABBREVIATIONS"
    - "SYMBOLS"
    - "GENERAL NOTES"
    - "NOTES"
    
    Args:
        texts: List of text elements from the document
        
    Returns:
        List of bounding boxes for legend regions
    """
    legend_regions = []
    
    # Common legend indicators
    legend_patterns = [
        r'\bLEGEND\b',
        r'\bABBREV(?:IATIONS?)?\b',
        r'\bSYMBOLS?\b',
        r'\bGENERAL\s+NOTES?\b',
        r'\bNOTES?\b',
        r'\bSCALE\b',
        r'\bREFERENCE\b'
    ]
    
    # Find text elements that match legend patterns
    legend_texts = []
    for text in texts:
        text_content = text.text.upper().strip()
        for pattern in legend_patterns:
            if re.search(pattern, text_content, re.IGNORECASE):
                legend_texts.append(text)
                break
    
    # Group nearby legend texts into regions
    for legend_text in legend_texts:
        bbox = BBox(
            x1=legend_text.bbox[0],
            y1=legend_text.bbox[1],
            x2=legend_text.bbox[2],
            y2=legend_text.bbox[3]
        )
        
        # Expand bounding box to include nearby text
        expanded_bbox = _expand_bbox_for_legend(bbox, texts)
        legend_regions.append(expanded_bbox)
    
    # Merge overlapping regions
    merged_regions = _merge_overlapping_bboxes(legend_regions)
    
    logger.info(f"Found {len(merged_regions)} legend regions")
    return merged_regions


def sample_symbol_snippets(
    vectors: List[VectorEl], 
    texts: List[TextEl], 
    regions: List[BBox]
) -> List[SymbolSnippet]:
    """
    Sample symbol snippets from legend regions.
    
    Args:
        vectors: List of vector elements
        texts: List of text elements
        regions: List of legend region bounding boxes
        
    Returns:
        List of symbol snippets with metadata
    """
    snippets = []
    
    for region in regions:
        # Find vectors within the legend region
        region_vectors = _filter_vectors_in_region(vectors, region)
        
        # Find texts within the legend region
        region_texts = _filter_texts_in_region(texts, region)
        
        # Group vectors and texts into symbol snippets
        symbol_groups = _group_symbols_in_region(region_vectors, region_texts, region)
        
        for group in symbol_groups:
            snippet = _create_symbol_snippet(group, region)
            if snippet:
                snippets.append(snippet)
    
    logger.info(f"Created {len(snippets)} symbol snippets")
    return snippets


def _expand_bbox_for_legend(bbox: BBox, texts: List[TextEl]) -> BBox:
    """Expand bounding box to include nearby legend content."""
    # Define expansion distance (in points)
    expansion_distance = 100.0
    
    # Find all texts within expansion distance
    nearby_texts = []
    for text in texts:
        text_center_x = (text.bbox[0] + text.bbox[2]) / 2
        text_center_y = (text.bbox[1] + text.bbox[3]) / 2
        
        bbox_center_x = (bbox.x1 + bbox.x2) / 2
        bbox_center_y = (bbox.y1 + bbox.y2) / 2
        
        distance = math.sqrt((text_center_x - bbox_center_x)**2 + (text_center_y - bbox_center_y)**2)
        
        if distance <= expansion_distance:
            nearby_texts.append(text)
    
    if not nearby_texts:
        return bbox
    
    # Calculate expanded bounding box
    min_x = min(bbox.x1, min(text.bbox[0] for text in nearby_texts))
    min_y = min(bbox.y1, min(text.bbox[1] for text in nearby_texts))
    max_x = max(bbox.x2, max(text.bbox[2] for text in nearby_texts))
    max_y = max(bbox.y2, max(text.bbox[3] for text in nearby_texts))
    
    return BBox(min_x, min_y, max_x, max_y)


def _merge_overlapping_bboxes(bboxes: List[BBox]) -> List[BBox]:
    """Merge overlapping bounding boxes."""
    if not bboxes:
        return []
    
    # Sort by x coordinate
    sorted_bboxes = sorted(bboxes, key=lambda b: b.x1)
    merged = [sorted_bboxes[0]]
    
    for bbox in sorted_bboxes[1:]:
        last_merged = merged[-1]
        
        # Check if they overlap
        if bbox.overlaps(last_merged):
            # Merge the bounding boxes
            merged_bbox = BBox(
                x1=min(bbox.x1, last_merged.x1),
                y1=min(bbox.y1, last_merged.y1),
                x2=max(bbox.x2, last_merged.x2),
                y2=max(bbox.y2, last_merged.y2)
            )
            merged[-1] = merged_bbox
        else:
            merged.append(bbox)
    
    return merged


def _filter_vectors_in_region(vectors: List[VectorEl], region: BBox) -> List[VectorEl]:
    """Filter vectors that are within the legend region."""
    region_vectors = []
    
    for vector in vectors:
        # Check if any point of the vector is within the region
        for point in vector.points:
            if region.contains(point[0], point[1]):
                region_vectors.append(vector)
                break
    
    return region_vectors


def _filter_texts_in_region(texts: List[TextEl], region: BBox) -> List[TextEl]:
    """Filter texts that are within the legend region."""
    region_texts = []
    
    for text in texts:
        # Check if text bounding box overlaps with region
        text_bbox = BBox(
            x1=text.bbox[0],
            y1=text.bbox[1],
            x2=text.bbox[2],
            y2=text.bbox[3]
        )
        
        if region.overlaps(text_bbox):
            region_texts.append(text)
    
    return region_texts


def _group_symbols_in_region(
    vectors: List[VectorEl], 
    texts: List[TextEl], 
    region: BBox
) -> List[Dict[str, Any]]:
    """Group vectors and texts into symbol groups within a region."""
    groups = []
    
    # Simple grouping: each vector with nearby texts
    for vector in vectors:
        group = {
            'vectors': [vector],
            'texts': [],
            'bbox': _calculate_group_bbox([vector], [])
        }
        
        # Find nearby texts
        for text in texts:
            if _is_text_near_vector(text, vector):
                group['texts'].append(text)
        
        # Update group bounding box
        group['bbox'] = _calculate_group_bbox(group['vectors'], group['texts'])
        
        groups.append(group)
    
    return groups


def _is_text_near_vector(text: TextEl, vector: VectorEl) -> bool:
    """Check if text is near a vector element."""
    # Define proximity threshold
    proximity_threshold = 50.0
    
    # Get text center
    text_center_x = (text.bbox[0] + text.bbox[2]) / 2
    text_center_y = (text.bbox[1] + text.bbox[3]) / 2
    
    # Check distance to vector points
    for point in vector.points:
        distance = math.sqrt(
            (text_center_x - point[0])**2 + (text_center_y - point[1])**2
        )
        if distance <= proximity_threshold:
            return True
    
    return False


def _calculate_group_bbox(vectors: List[VectorEl], texts: List[TextEl]) -> BBox:
    """Calculate bounding box for a group of vectors and texts."""
    if not vectors and not texts:
        return BBox(0, 0, 0, 0)
    
    min_x = float('inf')
    min_y = float('inf')
    max_x = float('-inf')
    max_y = float('-inf')
    
    # Include vector points
    for vector in vectors:
        for point in vector.points:
            min_x = min(min_x, point[0])
            min_y = min(min_y, point[1])
            max_x = max(max_x, point[0])
            max_y = max(max_y, point[1])
    
    # Include text bounding boxes
    for text in texts:
        min_x = min(min_x, text.bbox[0])
        min_y = min(min_y, text.bbox[1])
        max_x = max(max_x, text.bbox[2])
        max_y = max(max_y, text.bbox[3])
    
    return BBox(min_x, min_y, max_x, max_y)


def _create_symbol_snippet(group: Dict[str, Any], region: BBox) -> Optional[SymbolSnippet]:
    """Create a symbol snippet from a group of vectors and texts."""
    try:
        vectors = group['vectors']
        texts = group['texts']
        bbox = group['bbox']
        
        if not vectors:
            return None
        
        # Analyze stroke patterns
        stroke_pattern = _analyze_stroke_pattern(vectors)
        
        # Calculate stroke width statistics
        stroke_width_stats = _calculate_stroke_width_stats(vectors)
        
        # Determine shape hints
        shape_hints = _determine_shape_hints(vectors)
        
        # Extract adjacent text
        adjacent_text = [text.text for text in texts]
        
        return SymbolSnippet(
            vectors=vectors,
            texts=texts,
            bbox=bbox,
            stroke_pattern=stroke_pattern,
            stroke_width_stats=stroke_width_stats,
            shape_hints=shape_hints,
            adjacent_text=adjacent_text
        )
        
    except Exception as e:
        logger.error(f"Error creating symbol snippet: {e}")
        return None


def _analyze_stroke_pattern(vectors: List[VectorEl]) -> str:
    """Analyze stroke pattern from vectors."""
    # This is a simplified implementation
    # In practice, you'd analyze the actual stroke patterns
    
    for vector in vectors:
        if vector.kind == "line":
            return "solid"
        elif vector.kind == "polyline":
            return "dashed"
        elif vector.kind == "polygon":
            return "solid"
    
    return "unknown"


def _calculate_stroke_width_stats(vectors: List[VectorEl]) -> Dict[str, float]:
    """Calculate stroke width statistics."""
    widths = [vector.stroke_w for vector in vectors if vector.stroke_w > 0]
    
    if not widths:
        return {"min": 0.0, "max": 0.0, "mean": 0.0}
    
    return {
        "min": min(widths),
        "max": max(widths),
        "mean": sum(widths) / len(widths)
    }


def _determine_shape_hints(vectors: List[VectorEl]) -> List[str]:
    """Determine shape hints from vectors."""
    hints = []
    
    for vector in vectors:
        if vector.kind == "circle":
            hints.append("circle")
        elif vector.kind == "ellipse":
            hints.append("ellipse")
        elif vector.kind == "rect":
            hints.append("rectangle")
        elif vector.kind == "line":
            hints.append("line")
        elif vector.kind == "polyline":
            hints.append("polyline")
        elif vector.kind == "polygon":
            hints.append("polygon")
    
    return list(set(hints))  # Remove duplicates
