"""
Earthwork surface estimation utilities.

This module provides functions to estimate earthwork quantities
from surface contours and TIN analysis, with robust profile parsing
and elevation sampling capabilities.
"""
import json
import math
import re
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from shapely.geometry import LineString, Point
from shapely.ops import transform
import numpy as np


@dataclass
class SurfaceProfile:
    """Surface profile data with elevation sampling capabilities."""
    contours: List[Dict[str, Any]]
    scale_info: Optional[Any]
    bounds: Tuple[float, float, float, float]  # minx, miny, maxx, maxy
    elevation_range: Tuple[float, float]  # min_elev, max_elev


@dataclass
class ProfilePoint:
    """Point along a profile with station and elevation."""
    station: float
    elevation: float
    x: float
    y: float


def load_surface_from_pdf(
    vectors: List[Dict[str, Any]], 
    scale_info: Optional[Any] = None,
    bounds: Optional[Tuple[float, float, float, float]] = None
) -> SurfaceProfile:
    """
    Load surface data from PDF vectors and create elevation sampling functions.
    
    Args:
        vectors: List of vector elements from PDF
        scale_info: Scale information for coordinate conversion
        bounds: Optional bounds (minx, miny, maxx, maxy) for surface area
        
    Returns:
        SurfaceProfile with elevation sampling capabilities
    """
    # Extract contour lines from vectors
    contours = []
    for vector in vectors:
        if vector.get('type') == 'line' and _is_contour_line(vector):
            contours.append(vector)
    
    # Calculate bounds if not provided
    if bounds is None:
        bounds = _calculate_bounds(contours)
    
    # Calculate elevation range
    elevation_range = _calculate_elevation_range(contours)
    
    return SurfaceProfile(
        contours=contours,
        scale_info=scale_info,
        bounds=bounds,
        elevation_range=elevation_range
    )


def create_elevation_sampler(profile: SurfaceProfile) -> Callable[[float, float], float]:
    """
    Create an elevation sampling function from surface profile.
    
    Args:
        profile: SurfaceProfile with contour data
        
    Returns:
        Callable function elev(x, y) that returns elevation at point
    """
    def elev(x: float, y: float) -> float:
        """
        Get elevation at point (x, y) using nearest contour interpolation.
        
        Args:
            x, y: Coordinates in PDF space
            
        Returns:
            Elevation at point, or interpolated value
        """
        if not profile.contours:
            return 0.0  # Default elevation if no contours
        
        # Find nearest contour lines
        nearest_contours = _find_nearest_contours(profile.contours, x, y, max_distance=50.0)
        
        if not nearest_contours:
            return 0.0  # Default if no nearby contours
        
        # Interpolate elevation from nearest contours
        return _interpolate_elevation_from_contours(nearest_contours, x, y)
    
    return elev


def sample_along_centerline(
    centerline: LineString, 
    elevation_sampler: Callable[[float, float], float],
    sample_spacing: float = 10.0
) -> List[Tuple[float, float]]:
    """
    Sample elevation along a centerline.
    
    Args:
        centerline: Shapely LineString representing the centerline
        elevation_sampler: Function to get elevation at (x, y)
        sample_spacing: Distance between samples along centerline
        
    Returns:
        List of (station, elevation) tuples
    """
    samples = []
    
    # Calculate total length
    total_length = centerline.length
    
    # Sample along the line
    num_samples = max(2, int(total_length / sample_spacing) + 1)
    
    for i in range(num_samples):
        # Calculate station along line
        station = (i / (num_samples - 1)) * total_length
        
        # Get point along line
        point = centerline.interpolate(station)
        
        # Sample elevation
        elevation = elevation_sampler(point.x, point.y)
        
        samples.append((station, elevation))
    
    return samples


def parse_profile_from_text(
    text_elements: List[Dict[str, Any]], 
    scale_info: Optional[Any] = None
) -> Optional[List[ProfilePoint]]:
    """
    Parse ground level profile from text elements.
    
    Args:
        text_elements: List of text elements from PDF
        scale_info: Scale information for coordinate conversion
        
    Returns:
        List of ProfilePoint objects, or None if no profile found
    """
    profile_points = []
    
    # Look for profile text patterns
    for text_elem in text_elements:
        text = text_elem.get('text', '').strip()
        
        # Check for elevation patterns
        elevation_match = _extract_elevation_from_text(text)
        if elevation_match:
            x = text_elem.get('x', 0)
            y = text_elem.get('y', 0)
            elevation = elevation_match
            
            # Calculate station if possible
            station = _calculate_station_from_position(x, y, text_elements)
            
            profile_points.append(ProfilePoint(
                station=station,
                elevation=elevation,
                x=x,
                y=y
            ))
    
    if not profile_points:
        return None
    
    # Sort by station
    profile_points.sort(key=lambda p: p.station)
    
    return profile_points


def create_ground_level_function(
    profile_points: List[ProfilePoint]
) -> Callable[[float], float]:
    """
    Create a ground level function from profile points.
    
    Args:
        profile_points: List of ProfilePoint objects
        
    Returns:
        Callable function ground_level(station) that returns elevation
    """
    if not profile_points:
        return lambda s: 0.0  # Default ground level
    
    def ground_level(station: float) -> float:
        """
        Get ground level elevation at station.
        
        Args:
            station: Station along alignment
            
        Returns:
            Ground level elevation
        """
        if len(profile_points) == 1:
            return profile_points[0].elevation
        
        # Find surrounding points
        for i in range(len(profile_points) - 1):
            if profile_points[i].station <= station <= profile_points[i + 1].station:
                # Linear interpolation
                p1 = profile_points[i]
                p2 = profile_points[i + 1]
                
                if p2.station == p1.station:
                    return p1.elevation
                
                t = (station - p1.station) / (p2.station - p1.station)
                return p1.elevation + t * (p2.elevation - p1.elevation)
        
        # Extrapolate if outside range
        if station < profile_points[0].station:
            return profile_points[0].elevation
        else:
            return profile_points[-1].elevation
    
    return ground_level


def _is_contour_line(vector: Dict[str, Any]) -> bool:
    """Check if vector represents a contour line."""
    # Look for contour indicators in the vector data
    if vector.get('type') != 'line':
        return False
    
    # Check for elevation labels or contour patterns
    if 'elevation' in vector.get('attributes', {}):
        return True
    
    # Check for contour-like properties
    if vector.get('closed', False) and vector.get('points'):
        return True
    
    return False


def _calculate_bounds(contours: List[Dict[str, Any]]) -> Tuple[float, float, float, float]:
    """Calculate bounds from contour lines."""
    if not contours:
        return (0.0, 0.0, 1000.0, 1000.0)  # Default bounds
    
    minx = miny = float('inf')
    maxx = maxy = float('-inf')
    
    for contour in contours:
        points = contour.get('points', [])
        for point in points:
            x, y = point[0], point[1]
            minx = min(minx, x)
            miny = min(miny, y)
            maxx = max(maxx, x)
            maxy = max(maxy, y)
    
    return (minx, miny, maxx, maxy)


def _calculate_elevation_range(contours: List[Dict[str, Any]]) -> Tuple[float, float]:
    """Calculate elevation range from contours."""
    if not contours:
        return (0.0, 100.0)  # Default range
    
    elevations = []
    for contour in contours:
        if 'elevation' in contour.get('attributes', {}):
            elevations.append(contour['attributes']['elevation'])
    
    if not elevations:
        return (0.0, 100.0)  # Default range
    
    return (min(elevations), max(elevations))


def _find_nearest_contours(
    contours: List[Dict[str, Any]], 
    x: float, 
    y: float, 
    max_distance: float
) -> List[Dict[str, Any]]:
    """Find contour lines near a point."""
    nearest = []
    
    for contour in contours:
        points = contour.get('points', [])
        if not points:
            continue
        
        # Calculate minimum distance to contour
        min_dist = float('inf')
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            
            # Distance from point to line segment
            dist = _point_to_line_distance(x, y, p1[0], p1[1], p2[0], p2[1])
            min_dist = min(min_dist, dist)
        
        if min_dist <= max_distance:
            nearest.append(contour)
    
    return nearest


def _point_to_line_distance(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate distance from point to line segment."""
    # Vector from line start to point
    dx = px - x1
    dy = py - y1
    
    # Vector along line
    lx = x2 - x1
    ly = y2 - y1
    
    # Project point onto line
    if lx == 0 and ly == 0:
        return math.sqrt(dx*dx + dy*dy)
    
    t = (dx * lx + dy * ly) / (lx * lx + ly * ly)
    t = max(0, min(1, t))  # Clamp to line segment
    
    # Closest point on line
    cx = x1 + t * lx
    cy = y1 + t * ly
    
    # Distance to closest point
    return math.sqrt((px - cx)**2 + (py - cy)**2)


def _interpolate_elevation_from_contours(
    contours: List[Dict[str, Any]], 
    x: float, 
    y: float
) -> float:
    """Interpolate elevation from nearby contours."""
    if not contours:
        return 0.0
    
    # Get elevations from contours
    elevations = []
    weights = []
    
    for contour in contours:
        if 'elevation' in contour.get('attributes', {}):
            elevation = contour['attributes']['elevation']
            points = contour.get('points', [])
            
            if points:
                # Calculate distance to contour
                min_dist = float('inf')
                for i in range(len(points) - 1):
                    p1 = points[i]
                    p2 = points[i + 1]
                    dist = _point_to_line_distance(x, y, p1[0], p1[1], p2[0], p2[1])
                    min_dist = min(min_dist, dist)
                
                # Use inverse distance weighting
                weight = 1.0 / (min_dist + 1.0)  # Add 1 to avoid division by zero
                elevations.append(elevation)
                weights.append(weight)
    
    if not elevations:
        return 0.0
    
    # Weighted average
    total_weight = sum(weights)
    if total_weight == 0:
        return elevations[0]
    
    weighted_sum = sum(e * w for e, w in zip(elevations, weights))
    return weighted_sum / total_weight


def _extract_elevation_from_text(text: str) -> Optional[float]:
    """Extract elevation value from text."""
    # Common elevation patterns
    patterns = [
        r'EL\.?\s*(\d+\.?\d*)',  # EL. 123.45
        r'ELEV\.?\s*(\d+\.?\d*)',  # ELEV. 123.45
        r'(\d+\.?\d*)\s*FT',  # 123.45 FT
        r'(\d+\.?\d*)\s*\'',  # 123.45'
        r'(\d+\.?\d*)\s*"',  # 123.45"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    
    return None


def _calculate_station_from_position(
    x: float, 
    y: float, 
    text_elements: List[Dict[str, Any]]
) -> float:
    """Calculate station from position relative to other text elements."""
    # Simple implementation - in practice this would be more sophisticated
    # For now, use x-coordinate as station
    return x


def estimate_earthwork_from_contours(
    vectors: List[Dict[str, Any]], 
    scale_info: Optional[Any] = None
) -> Optional[Dict[str, float]]:
    """
    Estimate earthwork quantities from contour analysis.
    
    Args:
        vectors: List of vector elements from PDF
        scale_info: Scale information for coordinate conversion
        
    Returns:
        Dictionary with earthwork quantities, or None if insufficient data
    """
    # Load surface profile
    profile = load_surface_from_pdf(vectors, scale_info)
    
    if not profile.contours:
        return None
    
    # Create elevation sampler
    elevation_sampler = create_elevation_sampler(profile)
    
    # Sample surface in grid pattern
    grid_size = 50.0  # Sample every 50 units
    minx, miny, maxx, maxy = profile.bounds
    
    elevations = []
    for x in np.arange(minx, maxx, grid_size):
        for y in np.arange(miny, maxy, grid_size):
            elevation = elevation_sampler(x, y)
            elevations.append(elevation)
    
    if not elevations:
        return None
    
    # Calculate basic statistics
    min_elev = min(elevations)
    max_elev = max(elevations)
    avg_elev = sum(elevations) / len(elevations)
    
    # Estimate earthwork (simplified)
    area_sf = (maxx - minx) * (maxy - miny)
    volume_cy = area_sf * (max_elev - min_elev) / 27.0  # Convert to cubic yards
    
    return {
        'cut_cy': volume_cy * 0.5,  # Assume 50% cut
        'fill_cy': volume_cy * 0.5,  # Assume 50% fill
        'source': 'surface',
        'area_sf': area_sf,
        'min_elevation': min_elev,
        'max_elevation': max_elev,
        'avg_elevation': avg_elev
    }
