"""
Sitework quantification utilities.

This module provides functions to measure sitework quantities
like curb, sidewalk, silt fence, and inlet protection.
"""
from typing import List, Dict, Any, Optional
import math


def measure_curb_lf(vectors: List[Dict[str, Any]], scale_info: Optional[Any] = None) -> float:
    """
    Measure curb length in linear feet.
    """
    # Mock implementation - in real version this would analyze vectors
    # Look for curb-like lines (typically parallel to roads)
    curb_length = 0.0
    
    for vector in vectors:
        if vector.get("type") == "line":
            x1, y1 = vector.get("x1", 0), vector.get("y1", 0)
            x2, y2 = vector.get("x2", 0), vector.get("y2", 0)
            
            # Calculate length
            length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            
            # If it's a reasonable length for curb (10-500 feet)
            if 10 <= length <= 500:
                curb_length += length
    
    # Apply scale if available
    if scale_info and hasattr(scale_info, 'scale_factor'):
        curb_length *= scale_info.scale_factor
    
    return round(curb_length, 2)


def measure_sidewalk_sf(vectors: List[Dict[str, Any]], scale_info: Optional[Any] = None) -> float:
    """
    Measure sidewalk area in square feet.
    """
    # Mock implementation - in real version this would analyze vectors
    sidewalk_area = 0.0
    
    for vector in vectors:
        if vector.get("type") == "line":
            x1, y1 = vector.get("x1", 0), vector.get("y1", 0)
            x2, y2 = vector.get("x2", 0), vector.get("y2", 0)
            
            # Calculate length
            length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            
            # If it's a reasonable length for sidewalk (10-200 feet)
            if 10 <= length <= 200:
                # Assume 4-foot wide sidewalk
                width = 4.0
                area = length * width
                sidewalk_area += area
    
    # Apply scale if available
    if scale_info and hasattr(scale_info, 'scale_factor'):
        sidewalk_area *= (scale_info.scale_factor ** 2)
    
    return round(sidewalk_area, 2)


def measure_silt_fence_lf(vectors: List[Dict[str, Any]], scale_info: Optional[Any] = None) -> float:
    """
    Measure silt fence length in linear feet.
    """
    # Mock implementation - in real version this would analyze vectors
    silt_fence_length = 0.0
    
    for vector in vectors:
        if vector.get("type") == "line":
            x1, y1 = vector.get("x1", 0), vector.get("y1", 0)
            x2, y2 = vector.get("x2", 0), vector.get("y2", 0)
            
            # Calculate length
            length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            
            # If it's a reasonable length for silt fence (20-1000 feet)
            if 20 <= length <= 1000:
                silt_fence_length += length
    
    # Apply scale if available
    if scale_info and hasattr(scale_info, 'scale_factor'):
        silt_fence_length *= scale_info.scale_factor
    
    return round(silt_fence_length, 2)


def count_inlet_protections(vectors: List[Dict[str, Any]], texts: List[Dict[str, Any]]) -> int:
    """
    Count inlet protection devices.
    """
    # Mock implementation - in real version this would analyze vectors and text
    count = 0
    
    # Look for text indicating inlet protection
    protection_keywords = ["inlet protection", "inlet prot", "sediment control"]
    
    for text_elem in texts:
        text = text_elem.get("text", "").lower()
        if any(keyword in text for keyword in protection_keywords):
            count += 1
    
    # Also count circles that might represent inlet protection
    for vector in vectors:
        if vector.get("type") == "circle":
            x1, y1 = vector.get("x1", 0), vector.get("y1", 0)
            x2, y2 = vector.get("x2", 0), vector.get("y2", 0)
            
            # Check if it's a reasonable size for inlet protection
            radius = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            if 5 <= radius <= 20:  # Reasonable size for inlet protection
                count += 1
    
    return count
