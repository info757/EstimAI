"""
Depth calculation utilities for pipe trench analysis.

Provides functions to:
- Look up pipe outside diameters by material and size
- Sample depth along pipe runs using ground profiles
- Calculate trench volumes and depth statistics
- Validate minimum cover requirements
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
import math


# Global config storage
_od_lookup: Dict[str, Dict[str, float]] = {}
_trench_defaults: Dict[str, any] = {}


def init_depth_config(base_dir: str = "config") -> None:
    """Initialize depth calculation configuration from JSON files."""
    global _od_lookup, _trench_defaults
    
    base_path = Path(base_dir)
    
    # Load OD lookup table
    od_file = base_path / "pipes" / "od_lookup.json"
    if od_file.exists():
        with open(od_file, 'r') as f:
            _od_lookup = json.load(f)
    else:
        # Fallback defaults
        _od_lookup = {
            "pvc": {"4": 4.5, "6": 6.625, "8": 8.625, "10": 10.75, "12": 12.75},
            "rcp": {"12": 12.0, "15": 15.0, "18": 18.0, "21": 21.0, "24": 24.0}
        }
    
    # Load trench defaults
    trench_file = base_path / "pipes" / "trench_defaults.json"
    if trench_file.exists():
        with open(trench_file, 'r') as f:
            _trench_defaults = json.load(f)
    else:
        # Fallback defaults
        _trench_defaults = {
            "bedding_clearance_ft": 0.5,
            "side_slope_m_per_ft": 0.5,
            "use_shoring_box": True,
            "min_cover_ft": {"water": 3.0, "sewer": 2.5, "storm": 1.5}
        }


def od_ft(material: str, dia_in: float) -> float:
    """
    Get outside diameter in feet for a given material and nominal diameter.
    
    Args:
        material: Pipe material (pvc, rcp, hdp, ductile_iron)
        dia_in: Nominal diameter in inches
        
    Returns:
        Outside diameter in feet
    """
    if not _od_lookup:
        init_depth_config()
    
    material_lower = material.lower()
    dia_str = str(int(dia_in))
    
    if material_lower in _od_lookup and dia_str in _od_lookup[material_lower]:
        od_inches = _od_lookup[material_lower][dia_str]
        return od_inches / 12.0  # Convert to feet
    
    # Fallback: assume OD is 1.2x nominal diameter
    return (dia_in * 1.2) / 12.0


@dataclass
class DepthSample:
    """Single depth sample along a pipe run."""
    station: float  # Station along pipe (0.0 to 1.0)
    invert_ft: float  # Pipe invert elevation
    ground_ft: float  # Ground surface elevation
    depth_ft: float  # Depth from ground to invert
    cover_ft: float  # Cover from ground to pipe crown
    trench_width_ft: float  # Calculated trench width
    trench_area_sf: float  # Trench cross-sectional area


def sample_depth_along_run(
    s_profile: List[Tuple[float, float]],  # [(station, invert_elevation)]
    ground_at_s: callable,  # Function: station -> ground_elevation
    material: str,
    dia_in: float,
    n_samples: int = 20
) -> List[DepthSample]:
    """
    Sample depth along a pipe run using ground profile and pipe invert.
    
    Args:
        s_profile: List of (station, invert_elevation) tuples
        ground_at_s: Function to get ground elevation at station
        material: Pipe material for OD lookup
        dia_in: Nominal pipe diameter in inches
        n_samples: Number of samples to take along run
        
    Returns:
        List of DepthSample objects
    """
    if not s_profile:
        return []
    
    # Get pipe outside diameter
    pipe_od_ft = od_ft(material, dia_in)
    
    # Calculate trench parameters
    bedding_clearance = _trench_defaults.get("bedding_clearance_ft", 0.5)
    side_slope = _trench_defaults.get("side_slope_m_per_ft", 0.5)
    
    samples = []
    
    for i in range(n_samples):
        station = i / (n_samples - 1) if n_samples > 1 else 0.0
        
        # Interpolate invert elevation
        invert_ft = _interpolate_elevation(s_profile, station)
        
        # Get ground elevation
        ground_ft = ground_at_s(station)
        
        # Calculate depth and cover
        depth_ft = ground_ft - invert_ft
        cover_ft = depth_ft - (pipe_od_ft / 2)  # Cover to pipe crown
        
        # Calculate trench dimensions
        trench_width_ft = pipe_od_ft + (2 * bedding_clearance)
        trench_area_sf = _calculate_trench_area(
            pipe_od_ft, depth_ft, bedding_clearance, side_slope
        )
        
        samples.append(DepthSample(
            station=station,
            invert_ft=invert_ft,
            ground_ft=ground_ft,
            depth_ft=depth_ft,
            cover_ft=cover_ft,
            trench_width_ft=trench_width_ft,
            trench_area_sf=trench_area_sf
        ))
    
    return samples


@dataclass
class DepthSummary:
    """Summary statistics for pipe depth analysis."""
    min_depth_ft: float
    max_depth_ft: float
    avg_depth_ft: float
    p95_depth_ft: float
    buckets_lf: Dict[str, float]  # {"0-5": 100.0, "5-8": 50.0, "8-12": 25.0, "12+": 10.0}
    trench_volume_cy: float
    cover_ok: bool
    deep_excavation: bool


def summarize_depth(samples: List[DepthSample], discipline: str) -> DepthSummary:
    """
    Summarize depth statistics from samples.
    
    Args:
        samples: List of DepthSample objects
        discipline: Pipe discipline (water, sewer, storm)
        
    Returns:
        DepthSummary with statistics and flags
    """
    if not samples:
        return DepthSummary(
            min_depth_ft=0.0, max_depth_ft=0.0, avg_depth_ft=0.0, p95_depth_ft=0.0,
            buckets_lf={}, trench_volume_cy=0.0, cover_ok=True, deep_excavation=False
        )
    
    # Calculate basic statistics
    depths = [s.depth_ft for s in samples]
    min_depth_ft = min(depths)
    max_depth_ft = max(depths)
    avg_depth_ft = sum(depths) / len(depths)
    
    # Calculate P95 depth
    sorted_depths = sorted(depths)
    p95_index = int(len(sorted_depths) * 0.95)
    p95_depth_ft = sorted_depths[p95_index] if p95_index < len(sorted_depths) else max_depth_ft
    
    # Calculate depth buckets (assuming equal spacing)
    total_length = 1.0  # Normalized length
    segment_length = total_length / len(samples)
    
    buckets_lf = {"0-5": 0.0, "5-8": 0.0, "8-12": 0.0, "12+": 0.0}
    
    for sample in samples:
        depth = sample.depth_ft
        if depth < 5.0:
            buckets_lf["0-5"] += segment_length
        elif depth < 8.0:
            buckets_lf["5-8"] += segment_length
        elif depth < 12.0:
            buckets_lf["8-12"] += segment_length
        else:
            buckets_lf["12+"] += segment_length
    
    # Calculate total trench volume
    total_area_sf = sum(s.trench_area_sf for s in samples)
    trench_volume_cy = total_area_sf / 27.0  # Convert SF to CY
    
    # Check cover requirements
    min_cover_ft = _trench_defaults.get("min_cover_ft", {}).get(discipline, 1.5)
    cover_ok = all(s.cover_ft >= min_cover_ft for s in samples)
    
    # Check for deep excavation (OSHA requirements)
    deep_excavation = max_depth_ft > 5.0
    
    return DepthSummary(
        min_depth_ft=min_depth_ft,
        max_depth_ft=max_depth_ft,
        avg_depth_ft=avg_depth_ft,
        p95_depth_ft=p95_depth_ft,
        buckets_lf=buckets_lf,
        trench_volume_cy=trench_volume_cy,
        cover_ok=cover_ok,
        deep_excavation=deep_excavation
    )


def _interpolate_elevation(s_profile: List[Tuple[float, float]], station: float) -> float:
    """Interpolate elevation at given station along profile."""
    if not s_profile:
        return 0.0
    
    if len(s_profile) == 1:
        return s_profile[0][1]
    
    # Find surrounding stations
    for i in range(len(s_profile) - 1):
        s1, elev1 = s_profile[i]
        s2, elev2 = s_profile[i + 1]
        
        if s1 <= station <= s2:
            # Linear interpolation
            if s2 == s1:
                return elev1
            ratio = (station - s1) / (s2 - s1)
            return elev1 + ratio * (elev2 - elev1)
    
    # Extrapolate from last segment
    s1, elev1 = s_profile[-2]
    s2, elev2 = s_profile[-1]
    if s2 != s1:
        ratio = (station - s1) / (s2 - s1)
        return elev1 + ratio * (elev2 - elev1)
    
    return s_profile[-1][1]


def _calculate_trench_area(
    od_ft: float,
    depth_ft: float,
    bedding_clearance: float,
    side_slope: float
) -> float:
    """Calculate trench cross-sectional area in square feet."""
    # Trench bottom width
    bottom_width = od_ft + (2 * bedding_clearance)
    
    # Trench top width (accounting for side slopes)
    top_width = bottom_width + (2 * depth_ft * side_slope)
    
    # Trapezoidal area
    area = (bottom_width + top_width) / 2 * depth_ft
    
    return area
