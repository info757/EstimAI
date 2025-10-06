"""
Profile parsing utilities for ground level and invert profiles.

Provides functions to extract and parse profile data from PDF sheets,
including ground level (GL) profiles and pipe invert profiles.
"""
import logging
import re
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProfilePoint:
    """Single point in a profile."""
    station_ft: float
    elevation_ft: float
    text: str = ""
    confidence: float = 1.0


@dataclass
class ProfileData:
    """Parsed profile data."""
    points: List[ProfilePoint]
    profile_type: str  # "ground_level", "invert", "unknown"
    source_sheet: str
    metadata: Dict[str, Any] = None


def parse_profile_gl(sheet: Dict[str, Any]) -> Optional[List[Tuple[float, float]]]:
    """
    Parse ground level profile from sheet data.
    
    Args:
        sheet: Sheet data containing text elements and vectors
        
    Returns:
        List of (station_ft, ground_level_ft) tuples, or None if no GL profile found
    """
    try:
        logger.info("Parsing ground level profile from sheet")
        
        # Extract text elements that might contain profile data
        text_elements = sheet.get("texts", [])
        vectors = sheet.get("vectors", [])
        
        # Look for profile-related text patterns
        gl_points = []
        
        for text_elem in text_elements:
            text = text_elem.get("text", "").strip()
            if not text:
                continue
            
            # Look for station/elevation patterns
            # Common patterns: "0+00 95.2", "100 94.8", "STA 0+00 EL 95.2"
            station_elev_patterns = [
                r'(\d+(?:\+\d+)?)\s+(\d+\.?\d*)',  # "100 95.2"
                r'STA\s+(\d+(?:\+\d+)?)\s+EL\s+(\d+\.?\d*)',  # "STA 100 EL 95.2"
                r'(\d+(?:\+\d+)?)\s+GL\s+(\d+\.?\d*)',  # "100 GL 95.2"
            ]
            
            for pattern in station_elev_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        station_str = match[0].replace('+', '')  # Remove + from station
                        station_ft = float(station_str)
                        elevation_ft = float(match[1])
                        
                        gl_points.append((station_ft, elevation_ft))
                        logger.debug(f"Found GL point: {station_ft}ft -> {elevation_ft}ft")
                    except ValueError:
                        continue
        
        # Sort by station
        gl_points.sort(key=lambda x: x[0])
        
        if len(gl_points) >= 2:
            logger.info(f"Parsed {len(gl_points)} ground level points")
            return gl_points
        else:
            logger.warning("Insufficient ground level points found")
            return None
            
    except Exception as e:
        logger.error(f"Failed to parse ground level profile: {e}")
        return None


def parse_invert_profile(sheet: Dict[str, Any]) -> Optional[List[Tuple[float, float]]]:
    """
    Parse pipe invert profile from sheet data.
    
    Args:
        sheet: Sheet data containing text elements and vectors
        
    Returns:
        List of (station_ft, invert_elevation_ft) tuples, or None if no invert profile found
    """
    try:
        logger.info("Parsing invert profile from sheet")
        
        # Extract text elements that might contain invert data
        text_elements = sheet.get("texts", [])
        
        invert_points = []
        
        for text_elem in text_elements:
            text = text_elem.get("text", "").strip()
            if not text:
                continue
            
            # Look for invert-related text patterns
            # Common patterns: "INV 95.2", "INVERT 95.2", "I 95.2"
            invert_patterns = [
                r'INV\s+(\d+\.?\d*)',  # "INV 95.2"
                r'INVERT\s+(\d+\.?\d*)',  # "INVERT 95.2"
                r'I\s+(\d+\.?\d*)',  # "I 95.2"
            ]
            
            for pattern in invert_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        elevation_ft = float(match)
                        
                        # Try to extract station from context or use position
                        station_ft = _extract_station_from_context(text_elem, text)
                        
                        invert_points.append((station_ft, elevation_ft))
                        logger.debug(f"Found invert point: {station_ft}ft -> {elevation_ft}ft")
                    except ValueError:
                        continue
        
        # Sort by station
        invert_points.sort(key=lambda x: x[0])
        
        if len(invert_points) >= 2:
            logger.info(f"Parsed {len(invert_points)} invert points")
            return invert_points
        else:
            logger.warning("Insufficient invert points found")
            return None
            
    except Exception as e:
        logger.error(f"Failed to parse invert profile: {e}")
        return None


def _extract_station_from_context(text_elem: Dict[str, Any], text: str) -> float:
    """Extract station from text context or element position."""
    try:
        # Look for station in the same text element
        station_patterns = [
            r'(\d+(?:\+\d+)?)',  # Station format
            r'STA\s+(\d+(?:\+\d+)?)',  # "STA 100"
        ]
        
        for pattern in station_patterns:
            matches = re.findall(pattern, text)
            if matches:
                station_str = matches[0].replace('+', '')
                return float(station_str)
        
        # Fallback: use x-coordinate as station
        x = text_elem.get("x", 0.0)
        return x
        
    except Exception:
        return 0.0


def parse_profile_data(sheet: Dict[str, Any]) -> ProfileData:
    """
    Parse all profile data from a sheet.
    
    Args:
        sheet: Sheet data containing text elements and vectors
        
    Returns:
        ProfileData object with parsed profile information
    """
    try:
        logger.info("Parsing profile data from sheet")
        
        # Try to parse ground level profile
        gl_points = parse_profile_gl(sheet)
        
        # Try to parse invert profile
        invert_points = parse_invert_profile(sheet)
        
        # Determine profile type and points
        if gl_points and len(gl_points) >= 2:
            points = [ProfilePoint(s, e, f"GL {s} {e}") for s, e in gl_points]
            profile_type = "ground_level"
        elif invert_points and len(invert_points) >= 2:
            points = [ProfilePoint(s, e, f"INV {s} {e}") for s, e in invert_points]
            profile_type = "invert"
        else:
            points = []
            profile_type = "unknown"
        
        return ProfileData(
            points=points,
            profile_type=profile_type,
            source_sheet=sheet.get("name", "unknown"),
            metadata={
                "gl_points": len(gl_points) if gl_points else 0,
                "invert_points": len(invert_points) if invert_points else 0,
                "total_text_elements": len(sheet.get("texts", []))
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to parse profile data: {e}")
        return ProfileData(
            points=[],
            profile_type="unknown",
            source_sheet=sheet.get("name", "unknown"),
            metadata={"error": str(e)}
        )


def validate_profile_points(points: List[Tuple[float, float]]) -> bool:
    """
    Validate profile points for consistency.
    
    Args:
        points: List of (station, elevation) tuples
        
    Returns:
        True if profile is valid, False otherwise
    """
    if len(points) < 2:
        return False
    
    # Check for monotonic stationing
    stations = [p[0] for p in points]
    if not all(stations[i] <= stations[i + 1] for i in range(len(stations) - 1)):
        logger.warning("Non-monotonic stationing in profile")
        return False
    
    # Check for reasonable elevation values
    elevations = [p[1] for p in points]
    if any(e < -100 or e > 1000 for e in elevations):  # Reasonable elevation range
        logger.warning("Unreasonable elevation values in profile")
        return False
    
    return True


def interpolate_profile_elevation(
    points: List[Tuple[float, float]], 
    station: float
) -> float:
    """
    Interpolate elevation at a given station from profile points.
    
    Args:
        points: List of (station, elevation) tuples
        station: Station to interpolate at
        
    Returns:
        Interpolated elevation
    """
    if not points:
        return 0.0
    
    if len(points) == 1:
        return points[0][1]
    
    # Find surrounding points
    for i in range(len(points) - 1):
        s1, elev1 = points[i]
        s2, elev2 = points[i + 1]
        
        if s1 <= station <= s2:
            if s2 == s1:
                return elev1
            # Linear interpolation
            ratio = (station - s1) / (s2 - s1)
            return elev1 + ratio * (elev2 - elev1)
    
    # Extrapolate from last segment
    s1, elev1 = points[-2]
    s2, elev2 = points[-1]
    if s2 != s1:
        ratio = (station - s1) / (s2 - s1)
        return elev1 + ratio * (elev2 - elev1)
    
    return points[-1][1]
