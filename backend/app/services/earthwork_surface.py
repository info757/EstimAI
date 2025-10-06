"""
Earthwork surface sampling utilities for reliable ground elevation.

Provides functions to:
- Load surface data from PDF files (contours, profiles)
- Create ground elevation samplers with multiple fallback strategies
- Sample elevations along pipe centerlines
- Handle profile GL, surface contours, and constant fallbacks
"""
import logging
from typing import Callable, List, Tuple, Optional, Union
from dataclasses import dataclass
import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points

logger = logging.getLogger(__name__)


@dataclass
class Surface:
    """Surface data provider for ground elevation sampling."""
    elev_func: Callable[[float, float], float]  # (x, y) -> elevation
    sample_along: Callable[[LineString], List[Tuple[float, float]]]  # line -> [(s_ft, elev_ft)]
    source_type: str  # "contours", "profile", "constant"
    metadata: dict = None


def load_surface_from_pdf(file_ref: str) -> Optional[Surface]:
    """
    Load surface data from PDF file.
    
    Args:
        file_ref: Path to PDF file or file reference
        
    Returns:
        Surface object with elevation functions, or None if no surface data found
    """
    try:
        # This would integrate with existing PDF processing
        # For now, return a mock surface for testing
        logger.info(f"Loading surface from PDF: {file_ref}")
        
        # Mock surface data - in real implementation, this would:
        # 1. Extract contour lines from PDF vectors
        # 2. Create elevation interpolation from contours
        # 3. Build surface sampling functions
        
        def mock_elev_func(x: float, y: float) -> float:
            """Mock elevation function - in real implementation, interpolate from contours."""
            # Simple mock: elevation decreases with distance from origin
            return 100.0 - (x * 0.1 + y * 0.1)
        
        def mock_sample_along(line: LineString) -> List[Tuple[float, float]]:
            """Mock sampling along line - in real implementation, sample from surface."""
            coords = list(line.coords)
            if len(coords) < 2:
                return []
            
            samples = []
            total_length = line.length
            n_samples = max(10, int(total_length / 10))  # Sample every 10 feet
            
            for i in range(n_samples + 1):
                s_ft = (i / n_samples) * total_length if n_samples > 0 else 0.0
                point = line.interpolate(s_ft)
                elev_ft = mock_elev_func(point.x, point.y)
                samples.append((s_ft, elev_ft))
            
            return samples
        
        return Surface(
            elev_func=mock_elev_func,
            sample_along=mock_sample_along,
            source_type="contours",
            metadata={"file": file_ref, "method": "mock"}
        )
        
    except Exception as e:
        logger.error(f"Failed to load surface from PDF {file_ref}: {e}")
        return None


def make_ground_sampler(
    profile_gl: Optional[List[Tuple[float, float]]] = None,
    surface: Optional[Surface] = None,
    constant: Optional[float] = None
) -> Tuple[Callable[[float], float], str]:
    """
    Create ground elevation sampler with fallback strategy.
    
    Args:
        profile_gl: List of (station_ft, ground_level_ft) tuples from profile
        surface: Surface object for contour-based sampling
        constant: Constant ground elevation fallback
        
    Returns:
        Tuple of (sampler_function, source_type)
        - sampler_function: station_ft -> ground_elevation_ft
        - source_type: "profile", "surface", "constant"
    """
    
    # Priority 1: Profile GL data
    if profile_gl and len(profile_gl) > 1:
        logger.info("Using profile GL data for ground elevation")
        
        def profile_sampler(station_ft: float) -> float:
            """Sample ground elevation from profile GL data."""
            if not profile_gl:
                return constant or 0.0
            
            # Find surrounding stations
            for i in range(len(profile_gl) - 1):
                s1, elev1 = profile_gl[i]
                s2, elev2 = profile_gl[i + 1]
                
                if s1 <= station_ft <= s2:
                    if s2 == s1:
                        return elev1
                    # Linear interpolation
                    ratio = (station_ft - s1) / (s2 - s1)
                    return elev1 + ratio * (elev2 - elev1)
            
            # Extrapolate from last segment
            s1, elev1 = profile_gl[-2]
            s2, elev2 = profile_gl[-1]
            if s2 != s1:
                ratio = (station_ft - s1) / (s2 - s1)
                return elev1 + ratio * (elev2 - elev1)
            
            return profile_gl[-1][1]
        
        return profile_sampler, "profile"
    
    # Priority 2: Surface contours
    if surface and surface.sample_along:
        logger.info("Using surface contours for ground elevation")
        
        def surface_sampler(station_ft: float) -> float:
            """Sample ground elevation from surface contours."""
            # This would need the centerline to sample along
            # For now, return a mock value
            return surface.elev_func(0.0, 0.0)  # Mock implementation
        
        return surface_sampler, "surface"
    
    # Priority 3: Constant fallback
    if constant is not None:
        logger.info(f"Using constant ground elevation: {constant}ft")
        
        def constant_sampler(station_ft: float) -> float:
            """Return constant ground elevation."""
            return constant
        
        return constant_sampler, "constant"
    
    # Final fallback
    logger.warning("No ground elevation data available, using 0.0ft")
    
    def fallback_sampler(station_ft: float) -> float:
        """Fallback ground elevation."""
        return 0.0
    
    return fallback_sampler, "constant"


def sample_ground_along_centerline(
    centerline: LineString,
    ground_sampler: Callable[[float], float],
    n_samples: int = 20
) -> List[Tuple[float, float]]:
    """
    Sample ground elevation along a pipe centerline.
    
    Args:
        centerline: Pipe centerline as LineString
        ground_sampler: Function to get ground elevation at station
        n_samples: Number of samples to take
        
    Returns:
        List of (station_ft, elevation_ft) tuples
    """
    if not centerline or centerline.is_empty:
        return []
    
    total_length = centerline.length
    samples = []
    
    for i in range(n_samples):
        station_ft = (i / (n_samples - 1)) * total_length if n_samples > 1 else 0.0
        elevation_ft = ground_sampler(station_ft)
        samples.append((station_ft, elevation_ft))
    
    return samples


def create_ground_level_function(
    profile_points: List[Tuple[float, float]]
) -> Callable[[float], float]:
    """
    Create a ground level function from profile points.
    
    Args:
        profile_points: List of (station, elevation) tuples
        
    Returns:
        Callable function ground_level(station) that returns elevation
    """
    if not profile_points:
        return lambda s: 0.0  # Default ground level
    
    def ground_level(station: float) -> float:
        """
        Get ground level elevation at station.
        
        Args:
            station: Station along profile
            
        Returns:
            Ground level elevation
        """
        if not profile_points:
            return 0.0
        
        # Find surrounding points
        for i in range(len(profile_points) - 1):
            s1, elev1 = profile_points[i]
            s2, elev2 = profile_points[i + 1]
            
            if s1 <= station <= s2:
                if s2 == s1:
                    return elev1
                # Linear interpolation
                ratio = (station - s1) / (s2 - s1)
                return elev1 + ratio * (elev2 - elev1)
        
        # Extrapolate from last segment
        s1, elev1 = profile_points[-2]
        s2, elev2 = profile_points[-1]
        if s2 != s1:
            ratio = (station - s1) / (s2 - s1)
            return elev1 + ratio * (elev2 - elev1)
        
        return profile_points[-1][1]
    
    return ground_level


def validate_surface_sampling(
    samples: List[Tuple[float, float]],
    tolerance_ft: float = 0.2
) -> bool:
    """
    Validate surface sampling results.
    
    Args:
        samples: List of (station, elevation) tuples
        tolerance_ft: Maximum allowed elevation change between samples
        
    Returns:
        True if sampling is valid, False otherwise
    """
    if len(samples) < 2:
        return True
    
    # Check for monotonic stationing
    stations = [s[0] for s in samples]
    if not all(stations[i] <= stations[i + 1] for i in range(len(stations) - 1)):
        logger.warning("Non-monotonic stationing detected")
        return False
    
    # Check for reasonable elevation changes
    elevations = [s[1] for s in samples]
    for i in range(len(elevations) - 1):
        elev_change = abs(elevations[i + 1] - elevations[i])
        if elev_change > tolerance_ft * 10:  # Allow 10x tolerance for large changes
            logger.warning(f"Large elevation change detected: {elev_change:.2f}ft")
            return False
    
    return True
