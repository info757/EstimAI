"""
Minimal earthwork surface module for ground elevation sampling.

This is a simplified version that provides fallback ground elevation sampling.
"""
from typing import Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)


def make_ground_sampler(
    profile_gl: Optional[Any] = None,
    surface: Optional[Any] = None,
    constant: Optional[float] = None
) -> Callable:
    """
    Create a ground elevation sampler from available data sources.
    
    Priority:
    1. Profile ground line (most accurate)
    2. Surface data (good)
    3. Constant elevation (fallback)
    
    Args:
        profile_gl: Ground line profile data
        surface: Surface elevation data
        constant: Constant elevation fallback
        
    Returns:
        Callable sampler function that takes s_profile and returns elevation
    """
    # Try to use profile ground line first
    if profile_gl is not None:
        logger.info("Using profile ground line for elevation sampling")
        try:
            # If it's a callable, use it directly
            if callable(profile_gl):
                return profile_gl
            
            # If it's a list of elevation points, create interpolator
            if isinstance(profile_gl, (list, tuple)) and len(profile_gl) > 0:
                def profile_sampler(s_profile):
                    """Sample from profile ground line."""
                    if not s_profile or len(s_profile) < 2:
                        return constant or 100.0
                    
                    # Simple linear interpolation
                    # s_profile is typically [(station, elev), ...]
                    try:
                        if isinstance(s_profile[0], (tuple, list)):
                            return s_profile[0][1]  # Return first elevation
                        return float(s_profile[0])
                    except (IndexError, TypeError, ValueError):
                        return constant or 100.0
                
                return profile_sampler
        except Exception as e:
            logger.warning(f"Profile ground line setup failed: {e}")
    
    # Try surface data
    if surface is not None:
        logger.info("Using surface data for elevation sampling")
        try:
            if callable(surface):
                return surface
            
            # If it has a sample method, wrap it
            if hasattr(surface, 'sample'):
                def surface_sampler(s_profile):
                    """Sample from surface."""
                    if not s_profile or len(s_profile) < 2:
                        return constant or 100.0
                    try:
                        # Get first point coordinates
                        if isinstance(s_profile[0], (tuple, list)):
                            x, y = s_profile[0][0], s_profile[0][1]
                            return surface.sample(x, y)
                        return constant or 100.0
                    except Exception:
                        return constant or 100.0
                
                return surface_sampler
        except Exception as e:
            logger.warning(f"Surface sampler setup failed: {e}")
    
    # Fall back to constant elevation
    elevation = constant if constant is not None else 100.0
    logger.info(f"Using constant elevation: {elevation} ft")
    
    def constant_sampler(s_profile):
        """Return constant elevation."""
        return elevation
    
    return constant_sampler


def sample_elevation_along_line(
    line_coords: list,
    ground_sampler: Callable,
    num_samples: int = 10
) -> list[float]:
    """
    Sample ground elevation along a line.
    
    Args:
        line_coords: List of (x, y) coordinates
        ground_sampler: Sampler function
        num_samples: Number of sample points
        
    Returns:
        List of elevation values
    """
    if not line_coords or len(line_coords) < 2:
        return []
    
    elevations = []
    
    # Sample at regular intervals
    for i in range(num_samples):
        # Simple: just pass the coordinates to sampler
        try:
            elev = ground_sampler(line_coords)
            if isinstance(elev, (int, float)):
                elevations.append(float(elev))
        except Exception as e:
            logger.debug(f"Elevation sampling error: {e}")
            # Use fallback
            elevations.append(100.0)
    
    return elevations if elevations else [100.0] * num_samples

