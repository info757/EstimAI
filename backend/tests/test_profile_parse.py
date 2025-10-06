"""
Test profile parsing utilities for ground level and invert profiles.

Tests parsing of GL and invert profiles from sheet data with gold fixtures.
"""
import pytest
from backend.app.services.profiles.parser import (
    parse_profile_gl, parse_invert_profile, parse_profile_data,
    validate_profile_points, interpolate_profile_elevation,
    ProfilePoint, ProfileData
)


class TestProfileGLParsing:
    """Test ground level profile parsing."""
    
    def test_parse_profile_gl_basic(self):
        """Test parsing basic GL profile from text elements."""
        sheet_data = {
            "texts": [
                {"text": "0+00 100.0", "x": 0, "y": 0},
                {"text": "100 95.0", "x": 100, "y": 0},
                {"text": "200 90.0", "x": 200, "y": 0}
            ]
        }
        
        gl_points = parse_profile_gl(sheet_data)
        
        assert gl_points is not None
        assert len(gl_points) == 3
        assert gl_points[0] == (0.0, 100.0)
        assert gl_points[1] == (100.0, 95.0)
        assert gl_points[2] == (200.0, 90.0)
    
    def test_parse_profile_gl_sta_el_format(self):
        """Test parsing GL profile with STA EL format."""
        sheet_data = {
            "texts": [
                {"text": "STA 0+00 EL 100.0", "x": 0, "y": 0},
                {"text": "STA 100 EL 95.0", "x": 100, "y": 0},
                {"text": "STA 200 EL 90.0", "x": 200, "y": 0}
            ]
        }
        
        gl_points = parse_profile_gl(sheet_data)
        
        assert gl_points is not None
        assert len(gl_points) == 3
        assert gl_points[0] == (0.0, 100.0)
        assert gl_points[1] == (100.0, 95.0)
        assert gl_points[2] == (200.0, 90.0)
    
    def test_parse_profile_gl_gl_format(self):
        """Test parsing GL profile with GL format."""
        sheet_data = {
            "texts": [
                {"text": "0+00 GL 100.0", "x": 0, "y": 0},
                {"text": "100 GL 95.0", "x": 100, "y": 0},
                {"text": "200 GL 90.0", "x": 200, "y": 0}
            ]
        }
        
        gl_points = parse_profile_gl(sheet_data)
        
        assert gl_points is not None
        assert len(gl_points) == 3
        assert gl_points[0] == (0.0, 100.0)
        assert gl_points[1] == (100.0, 95.0)
        assert gl_points[2] == (200.0, 90.0)
    
    def test_parse_profile_gl_mixed_formats(self):
        """Test parsing GL profile with mixed formats."""
        sheet_data = {
            "texts": [
                {"text": "0+00 100.0", "x": 0, "y": 0},
                {"text": "STA 100 EL 95.0", "x": 100, "y": 0},
                {"text": "200 GL 90.0", "x": 200, "y": 0}
            ]
        }
        
        gl_points = parse_profile_gl(sheet_data)
        
        assert gl_points is not None
        assert len(gl_points) == 3
        assert gl_points[0] == (0.0, 100.0)
        assert gl_points[1] == (100.0, 95.0)
        assert gl_points[2] == (200.0, 90.0)
    
    def test_parse_profile_gl_insufficient_points(self):
        """Test parsing GL profile with insufficient points."""
        sheet_data = {
            "texts": [
                {"text": "0+00 100.0", "x": 0, "y": 0}
            ]
        }
        
        gl_points = parse_profile_gl(sheet_data)
        
        assert gl_points is None
    
    def test_parse_profile_gl_no_matching_text(self):
        """Test parsing GL profile with no matching text."""
        sheet_data = {
            "texts": [
                {"text": "Some other text", "x": 0, "y": 0},
                {"text": "More text", "x": 100, "y": 0}
            ]
        }
        
        gl_points = parse_profile_gl(sheet_data)
        
        assert gl_points is None
    
    def test_parse_profile_gl_invalid_numbers(self):
        """Test parsing GL profile with invalid numbers."""
        sheet_data = {
            "texts": [
                {"text": "0+00 100.0", "x": 0, "y": 0},
                {"text": "100 invalid", "x": 100, "y": 0},
                {"text": "200 90.0", "x": 200, "y": 0}
            ]
        }
        
        gl_points = parse_profile_gl(sheet_data)
        
        # Should still parse valid points
        assert gl_points is not None
        assert len(gl_points) == 2
        assert gl_points[0] == (0.0, 100.0)
        assert gl_points[1] == (200.0, 90.0)


class TestInvertProfileParsing:
    """Test invert profile parsing."""
    
    def test_parse_invert_profile_basic(self):
        """Test parsing basic invert profile."""
        sheet_data = {
            "texts": [
                {"text": "INV 95.0", "x": 0, "y": 0},
                {"text": "INV 90.0", "x": 100, "y": 0},
                {"text": "INV 85.0", "x": 200, "y": 0}
            ]
        }
        
        invert_points = parse_invert_profile(sheet_data)
        
        assert invert_points is not None
        assert len(invert_points) == 3
        assert invert_points[0] == (0.0, 95.0)  # Station from x-coordinate
        assert invert_points[1] == (100.0, 90.0)
        assert invert_points[2] == (200.0, 85.0)
    
    def test_parse_invert_profile_invert_format(self):
        """Test parsing invert profile with INVERT format."""
        sheet_data = {
            "texts": [
                {"text": "INVERT 95.0", "x": 0, "y": 0},
                {"text": "INVERT 90.0", "x": 100, "y": 0},
                {"text": "INVERT 85.0", "x": 200, "y": 0}
            ]
        }
        
        invert_points = parse_invert_profile(sheet_data)
        
        assert invert_points is not None
        assert len(invert_points) == 3
        assert invert_points[0] == (0.0, 95.0)
        assert invert_points[1] == (100.0, 90.0)
        assert invert_points[2] == (200.0, 85.0)
    
    def test_parse_invert_profile_i_format(self):
        """Test parsing invert profile with I format."""
        sheet_data = {
            "texts": [
                {"text": "I 95.0", "x": 0, "y": 0},
                {"text": "I 90.0", "x": 100, "y": 0},
                {"text": "I 85.0", "x": 200, "y": 0}
            ]
        }
        
        invert_points = parse_invert_profile(sheet_data)
        
        assert invert_points is not None
        assert len(invert_points) == 3
        assert invert_points[0] == (0.0, 95.0)
        assert invert_points[1] == (100.0, 90.0)
        assert invert_points[2] == (200.0, 85.0)
    
    def test_parse_invert_profile_insufficient_points(self):
        """Test parsing invert profile with insufficient points."""
        sheet_data = {
            "texts": [
                {"text": "INV 95.0", "x": 0, "y": 0}
            ]
        }
        
        invert_points = parse_invert_profile(sheet_data)
        
        assert invert_points is None
    
    def test_parse_invert_profile_no_matching_text(self):
        """Test parsing invert profile with no matching text."""
        sheet_data = {
            "texts": [
                {"text": "Some other text", "x": 0, "y": 0},
                {"text": "More text", "x": 100, "y": 0}
            ]
        }
        
        invert_points = parse_invert_profile(sheet_data)
        
        assert invert_points is None


class TestProfileDataParsing:
    """Test complete profile data parsing."""
    
    def test_parse_profile_data_gl_priority(self):
        """Test parsing profile data with GL priority."""
        sheet_data = {
            "name": "test_sheet",
            "texts": [
                {"text": "0+00 100.0", "x": 0, "y": 0},
                {"text": "100 95.0", "x": 100, "y": 0},
                {"text": "INV 90.0", "x": 0, "y": 0},
                {"text": "INV 85.0", "x": 100, "y": 0}
            ]
        }
        
        profile_data = parse_profile_data(sheet_data)
        
        assert profile_data.profile_type == "ground_level"
        assert len(profile_data.points) == 2
        assert profile_data.source_sheet == "test_sheet"
        assert profile_data.metadata["gl_points"] == 2
        assert profile_data.metadata["invert_points"] == 2
    
    def test_parse_profile_data_invert_fallback(self):
        """Test parsing profile data with invert fallback."""
        sheet_data = {
            "name": "test_sheet",
            "texts": [
                {"text": "INV 90.0", "x": 0, "y": 0},
                {"text": "INV 85.0", "x": 100, "y": 0}
            ]
        }
        
        profile_data = parse_profile_data(sheet_data)
        
        assert profile_data.profile_type == "invert"
        assert len(profile_data.points) == 2
        assert profile_data.source_sheet == "test_sheet"
        assert profile_data.metadata["gl_points"] == 0
        assert profile_data.metadata["invert_points"] == 2
    
    def test_parse_profile_data_no_data(self):
        """Test parsing profile data with no profile data."""
        sheet_data = {
            "name": "test_sheet",
            "texts": [
                {"text": "Some other text", "x": 0, "y": 0}
            ]
        }
        
        profile_data = parse_profile_data(sheet_data)
        
        assert profile_data.profile_type == "unknown"
        assert len(profile_data.points) == 0
        assert profile_data.source_sheet == "test_sheet"
        assert profile_data.metadata["gl_points"] == 0
        assert profile_data.metadata["invert_points"] == 0


class TestProfileValidation:
    """Test profile validation functionality."""
    
    def test_validate_profile_points_valid(self):
        """Test validation of valid profile points."""
        points = [(0.0, 100.0), (50.0, 95.0), (100.0, 90.0)]
        
        assert validate_profile_points(points) == True
    
    def test_validate_profile_points_insufficient(self):
        """Test validation with insufficient points."""
        points = [(0.0, 100.0)]
        
        assert validate_profile_points(points) == False
    
    def test_validate_profile_points_non_monotonic(self):
        """Test validation with non-monotonic stationing."""
        points = [(0.0, 100.0), (50.0, 95.0), (25.0, 90.0)]  # Non-monotonic
        
        assert validate_profile_points(points) == False
    
    def test_validate_profile_points_unreasonable_elevations(self):
        """Test validation with unreasonable elevations."""
        points = [(0.0, 100.0), (50.0, 95.0), (100.0, 2000.0)]  # Too high
        
        assert validate_profile_points(points) == False
    
    def test_validate_profile_points_negative_elevations(self):
        """Test validation with negative elevations."""
        points = [(0.0, 100.0), (50.0, 95.0), (100.0, -200.0)]  # Too low
        
        assert validate_profile_points(points) == False


class TestProfileInterpolation:
    """Test profile interpolation functionality."""
    
    def test_interpolate_profile_elevation_basic(self):
        """Test basic profile interpolation."""
        points = [(0.0, 100.0), (50.0, 95.0), (100.0, 90.0)]
        
        assert interpolate_profile_elevation(points, 0.0) == 100.0
        assert interpolate_profile_elevation(points, 50.0) == 95.0
        assert interpolate_profile_elevation(points, 100.0) == 90.0
        assert abs(interpolate_profile_elevation(points, 25.0) - 97.5) < 0.1
        assert abs(interpolate_profile_elevation(points, 75.0) - 92.5) < 0.1
    
    def test_interpolate_profile_elevation_empty(self):
        """Test interpolation with empty profile."""
        points = []
        
        assert interpolate_profile_elevation(points, 0.0) == 0.0
    
    def test_interpolate_profile_elevation_single_point(self):
        """Test interpolation with single point."""
        points = [(50.0, 95.0)]
        
        assert interpolate_profile_elevation(points, 0.0) == 95.0
        assert interpolate_profile_elevation(points, 50.0) == 95.0
        assert interpolate_profile_elevation(points, 100.0) == 95.0
    
    def test_interpolate_profile_elevation_extrapolation(self):
        """Test interpolation with extrapolation."""
        points = [(0.0, 100.0), (50.0, 95.0)]
        
        # Extrapolate beyond last point
        expected_100 = 95.0 + (100.0 - 50.0) * (95.0 - 100.0) / (50.0 - 0.0)
        assert abs(interpolate_profile_elevation(points, 100.0) - expected_100) < 0.1


class TestGoldFixtures:
    """Test with gold fixture data."""
    
    def test_gold_fixture_gl_profile(self):
        """Test with gold fixture GL profile data."""
        # Gold fixture: Real-world GL profile data
        sheet_data = {
            "name": "gold_fixture_sheet",
            "texts": [
                {"text": "0+00 100.5", "x": 0, "y": 0},
                {"text": "25 100.2", "x": 25, "y": 0},
                {"text": "50 99.8", "x": 50, "y": 0},
                {"text": "75 99.5", "x": 75, "y": 0},
                {"text": "100 99.2", "x": 100, "y": 0},
                {"text": "125 98.9", "x": 125, "y": 0},
                {"text": "150 98.6", "x": 150, "y": 0}
            ]
        }
        
        gl_points = parse_profile_gl(sheet_data)
        
        assert gl_points is not None
        assert len(gl_points) == 7
        assert gl_points[0] == (0.0, 100.5)
        assert gl_points[-1] == (150.0, 98.6)
        
        # Test interpolation accuracy
        assert abs(interpolate_profile_elevation(gl_points, 37.5) - 99.95) < 0.1
        assert abs(interpolate_profile_elevation(gl_points, 87.5) - 99.35) < 0.1
    
    def test_gold_fixture_invert_profile(self):
        """Test with gold fixture invert profile data."""
        # Gold fixture: Real-world invert profile data
        sheet_data = {
            "name": "gold_fixture_sheet",
            "texts": [
                {"text": "INV 95.0", "x": 0, "y": 0},
                {"text": "INV 94.5", "x": 25, "y": 0},
                {"text": "INV 94.0", "x": 50, "y": 0},
                {"text": "INV 93.5", "x": 75, "y": 0},
                {"text": "INV 93.0", "x": 100, "y": 0}
            ]
        }
        
        invert_points = parse_invert_profile(sheet_data)
        
        assert invert_points is not None
        assert len(invert_points) == 5
        assert invert_points[0] == (0.0, 95.0)
        assert invert_points[-1] == (100.0, 93.0)
        
        # Test interpolation accuracy
        assert abs(interpolate_profile_elevation(invert_points, 12.5) - 94.75) < 0.1
        assert abs(interpolate_profile_elevation(invert_points, 37.5) - 94.25) < 0.1
    
    def test_gold_fixture_mixed_profile(self):
        """Test with gold fixture mixed profile data."""
        # Gold fixture: Mixed GL and invert data
        sheet_data = {
            "name": "gold_fixture_sheet",
            "texts": [
                {"text": "0+00 100.0", "x": 0, "y": 0},
                {"text": "50 99.5", "x": 50, "y": 0},
                {"text": "100 99.0", "x": 100, "y": 0},
                {"text": "INV 95.0", "x": 0, "y": 0},
                {"text": "INV 94.5", "x": 50, "y": 0},
                {"text": "INV 94.0", "x": 100, "y": 0}
            ]
        }
        
        profile_data = parse_profile_data(sheet_data)
        
        assert profile_data.profile_type == "ground_level"  # GL has priority
        assert len(profile_data.points) == 3
        assert profile_data.metadata["gl_points"] == 3
        assert profile_data.metadata["invert_points"] == 3
    
    def test_gold_fixture_validation(self):
        """Test validation with gold fixture data."""
        # Gold fixture: Valid profile data
        points = [(0.0, 100.0), (25.0, 99.5), (50.0, 99.0), (75.0, 98.5), (100.0, 98.0)]
        
        assert validate_profile_points(points) == True
        
        # Test interpolation accuracy
        assert abs(interpolate_profile_elevation(points, 12.5) - 99.75) < 0.1
        assert abs(interpolate_profile_elevation(points, 37.5) - 99.25) < 0.1
        assert abs(interpolate_profile_elevation(points, 62.5) - 98.75) < 0.1
        assert abs(interpolate_profile_elevation(points, 87.5) - 98.25) < 0.1
