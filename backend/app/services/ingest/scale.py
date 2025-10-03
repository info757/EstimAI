"""Scale inference and coordinate transformation utilities."""
import re
import math
from typing import Optional, List, Tuple
from dataclasses import dataclass

from .pdfnet_runtime import Page


@dataclass
class ScaleInfo:
    """Scale information for coordinate transformation."""
    scale_str: Optional[str]  # Raw scale string like "1\" = 50'"
    units: str  # Target units (e.g., "feet", "meters")
    user_to_world: List[List[float]]  # 3x3 transformation matrix


def infer_scale_text(page: Page) -> Optional[str]:
    """
    Infer scale from text annotations on the page.
    
    Looks for common scale patterns like:
    - "1\" = 50'"
    - "SCALE 1\"=100'"
    - "1:1000"
    - "1 inch = 50 feet"
    
    Args:
        page: PDFNet Page object
        
    Returns:
        Scale string if found, None otherwise
    """
    try:
        # Get text content from the page
        text = page.GetText()
        if not text:
            return None
        
        # Common scale patterns
        patterns = [
            r'SCALE\s+([0-9]+["\"]?\s*=\s*[0-9]+[\'"]?)',  # SCALE 1" = 50'
            r'([0-9]+["\"]?\s*=\s*[0-9]+[\'"]?)',  # 1" = 50'
            r'([0-9]+:\s*[0-9]+)',  # 1:1000
            r'([0-9]+\s*inch(?:es)?\s*=\s*[0-9]+\s*feet?)',  # 1 inch = 50 feet
            r'([0-9]+\s*in\s*=\s*[0-9]+\s*ft)',  # 1 in = 50 ft
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Return the first match
                return matches[0].strip()
        
        return None
        
    except Exception as e:
        print(f"Error inferring scale from text: {e}")
        return None


def infer_scale_bar(page: Page) -> Optional[float]:
    """
    Infer scale from scale bar graphics on the page.
    
    Looks for common scale bar patterns and measures their length.
    
    Args:
        page: PDFNet Page object
        
    Returns:
        Scale factor (units per inch) if found, None otherwise
    """
    try:
        # This is a simplified implementation
        # In practice, you'd need to:
        # 1. Find scale bar graphics (lines with text labels)
        # 2. Measure their length in user coordinates
        # 3. Parse the associated text to get the real-world distance
        # 4. Calculate the scale factor
        
        # For now, return None as this requires more complex graphics analysis
        # A full implementation would involve:
        # - Finding line elements that look like scale bars
        # - Finding nearby text elements with distance labels
        # - Measuring the line length and correlating with the text
        
        return None
        
    except Exception as e:
        print(f"Error inferring scale from bar: {e}")
        return None


def compute_user_to_world(page: Page, scale_text_or_bar: Optional[str]) -> List[List[float]]:
    """
    Compute transformation matrix from user coordinates to world coordinates.
    
    Args:
        page: PDFNet Page object
        scale_text_or_bar: Scale string or bar measurement
        
    Returns:
        3x3 transformation matrix
    """
    try:
        # Get page dimensions and default matrix
        page_width = page.GetPageWidth()
        page_height = page.GetPageHeight()
        
        # Start with identity matrix
        matrix = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ]
        
        if scale_text_or_bar:
            # Parse scale string to get scale factor
            scale_factor = parse_scale_string(scale_text_or_bar)
            if scale_factor:
                # Apply scale transformation
                matrix[0][0] = scale_factor  # x scale
                matrix[1][1] = scale_factor  # y scale
        
        return matrix
        
    except Exception as e:
        print(f"Error computing user-to-world matrix: {e}")
        # Return identity matrix on error
        return [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ]


def parse_scale_string(scale_str: str) -> Optional[float]:
    """
    Parse scale string to extract scale factor.
    
    Args:
        scale_str: Scale string like "1\" = 50'" or "1:1000"
        
    Returns:
        Scale factor (units per inch) if parseable, None otherwise
    """
    try:
        # Pattern: 1" = 50' or 1 inch = 50 feet
        inch_feet_pattern = r'([0-9]+(?:\.\d+)?)\s*["\"]?\s*=\s*([0-9]+(?:\.\d+)?)\s*[\'"]?'
        match = re.search(inch_feet_pattern, scale_str)
        if match:
            inches = float(match.group(1))
            feet = float(match.group(2))
            return feet / inches  # feet per inch
        
        # Pattern: 1:1000 (ratio)
        ratio_pattern = r'([0-9]+(?:\.\d+)?)\s*:\s*([0-9]+(?:\.\d+)?)'
        match = re.search(ratio_pattern, scale_str)
        if match:
            numerator = float(match.group(1))
            denominator = float(match.group(2))
            return denominator / numerator
        
        # Pattern: 1 inch = 50 feet (explicit units)
        explicit_pattern = r'([0-9]+(?:\.\d+)?)\s*inch(?:es)?\s*=\s*([0-9]+(?:\.\d+)?)\s*feet?'
        match = re.search(explicit_pattern, scale_str, re.IGNORECASE)
        if match:
            inches = float(match.group(1))
            feet = float(match.group(2))
            return feet / inches
        
        return None
        
    except Exception as e:
        print(f"Error parsing scale string '{scale_str}': {e}")
        return None


def to_world(pt_user: Tuple[float, float], matrix: List[List[float]]) -> Tuple[float, float]:
    """
    Transform user coordinate point to world coordinates.
    
    Args:
        pt_user: (x, y) in user coordinates
        matrix: 3x3 transformation matrix
        
    Returns:
        (x, y) in world coordinates
    """
    x, y = pt_user
    
    # Apply transformation: [x', y', 1] = [x, y, 1] * matrix
    x_world = x * matrix[0][0] + y * matrix[0][1] + matrix[0][2]
    y_world = x * matrix[1][0] + y * matrix[1][1] + matrix[1][2]
    
    return (x_world, y_world)


def len_world(polyline_user: List[Tuple[float, float]], matrix: List[List[float]]) -> float:
    """
    Calculate world length of a polyline.
    
    Args:
        polyline_user: List of (x, y) points in user coordinates
        matrix: 3x3 transformation matrix
        
    Returns:
        Total length in world coordinates
    """
    if len(polyline_user) < 2:
        return 0.0
    
    total_length = 0.0
    
    for i in range(len(polyline_user) - 1):
        pt1 = to_world(polyline_user[i], matrix)
        pt2 = to_world(polyline_user[i + 1], matrix)
        
        # Calculate distance between consecutive points
        dx = pt2[0] - pt1[0]
        dy = pt2[1] - pt1[1]
        segment_length = math.sqrt(dx * dx + dy * dy)
        
        total_length += segment_length
    
    return total_length


def create_scale_info(page: Page) -> ScaleInfo:
    """
    Create ScaleInfo object for a page.
    
    Args:
        page: PDFNet Page object
        
    Returns:
        ScaleInfo object with inferred scale information
    """
    # Try to infer scale from text first
    scale_text = infer_scale_text(page)
    
    # If no text scale found, try scale bar
    if not scale_text:
        scale_bar = infer_scale_bar(page)
        if scale_bar:
            scale_text = f"1 inch = {scale_bar} feet"
    
    # Compute transformation matrix
    matrix = compute_user_to_world(page, scale_text)
    
    # Determine units (default to feet for construction drawings)
    units = "feet"
    if scale_text and "meter" in scale_text.lower():
        units = "meters"
    
    return ScaleInfo(
        scale_str=scale_text,
        units=units,
        user_to_world=matrix
    )
