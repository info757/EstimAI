"""
Scale detection and coordinate conversion utilities.

This module provides functions to detect scale information from PDFs
and convert between coordinate systems.
"""
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import math


@dataclass
class ScaleInfo:
    """Scale information for coordinate conversion."""
    scale_text: Optional[str] = None
    scale_factor: Optional[float] = None  # feet per unit
    units: str = "ft"


def infer_scale_text(texts: List[Dict[str, Any]]) -> Optional[ScaleInfo]:
    """
    Infer scale from text elements containing scale information.
    """
    scale_patterns = [
        r'1["\']?\s*=\s*(\d+)\s*["\']?',  # 1" = 50'
        r'(\d+)\s*["\']?\s*=\s*(\d+)\s*["\']?',  # 50" = 100'
        r'scale\s*:?\s*1["\']?\s*=\s*(\d+)',  # Scale: 1" = 50'
        r'(\d+)\s*ft\s*per\s*inch',  # 50 ft per inch
    ]
    
    for text_elem in texts:
        text = text_elem.get("text", "").strip()
        if not text:
            continue
            
        for pattern in scale_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    if len(match.groups()) == 1:
                        # Pattern like "1\" = 50'"
                        scale_factor = float(match.group(1))
                    else:
                        # Pattern like "50\" = 100'"
                        scale_factor = float(match.group(2)) / float(match.group(1))
                    
                    return ScaleInfo(
                        scale_text=text,
                        scale_factor=scale_factor,
                        units="ft"
                    )
                except (ValueError, ZeroDivisionError):
                    continue
    
    return None


def infer_scale_bar(vectors: List[Dict[str, Any]]) -> Optional[ScaleInfo]:
    """
    Infer scale from scale bar vectors.
    """
    # Look for scale bar patterns in vectors
    # This is a simplified implementation
    for vector in vectors:
        if vector.get("type") == "line":
            # Check if this could be a scale bar
            x1, y1 = vector.get("x1", 0), vector.get("y1", 0)
            x2, y2 = vector.get("x2", 0), vector.get("y2", 0)
            
            length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            
            # If it's a reasonable length for a scale bar
            if 50 <= length <= 200:
                # Assume 1 inch = 50 feet (common scale)
                return ScaleInfo(
                    scale_text="1\" = 50' (estimated from scale bar)",
                    scale_factor=50.0,
                    units="ft"
                )
    
    return None


def compute_user_to_world(scale_info: ScaleInfo) -> float:
    """
    Compute conversion factor from user units to world units.
    """
    if scale_info.scale_factor is None:
        return 1.0  # No scale information
    
    return scale_info.scale_factor


def to_world(user_value: float, scale_info: ScaleInfo) -> float:
    """
    Convert user value to world units.
    """
    factor = compute_user_to_world(scale_info)
    return user_value * factor


def len_world(p1: Tuple[float, float], p2: Tuple[float, float], scale_info: ScaleInfo) -> float:
    """
    Calculate world length between two points.
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    user_length = math.sqrt(dx * dx + dy * dy)
    return to_world(user_length, scale_info)
