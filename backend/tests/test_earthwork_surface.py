"""
Unit tests for earthwork surface sampling and profile parsing.

Tests elevation sampling, centerline analysis, and profile parsing
with tolerance checks for straight and curved centerlines.
"""
import pytest
import math
from shapely.geometry import LineString, Point
from backend.app.services.detectors.earthwork_surface import (
    load_surface_from_pdf,
    create_elevation_sampler,
    sample_along_centerline,
    parse_profile_from_text,
    create_ground_level_function,
    SurfaceProfile,
    ProfilePoint
)


def test_load_surface_from_pdf():
    """Test loading surface data from PDF vectors."""
    # Create mock contour vectors
    vectors = [
        {
            'type': 'line',
            'points': [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)],
            'attributes': {'elevation': 100.0},
            'closed': True
        },
        {
            'type': 'line',
            'points': [(10, 10), (90, 10), (90, 90), (10, 90), (10, 10)],
            'attributes': {'elevation': 105.0},
            'closed': True
        },
        {
            'type': 'line',
            'points': [(20, 20), (80, 20), (80, 80), (20, 80), (20, 20)],
            'attributes': {'elevation': 110.0},
            'closed': True
        }
    ]
    
    # Load surface profile
    profile = load_surface_from_pdf(vectors)
    
    assert len(profile.contours) == 3
    assert profile.bounds == (0.0, 0.0, 100.0, 100.0)
    assert profile.elevation_range == (100.0, 110.0)


def test_create_elevation_sampler():
    """Test creating elevation sampling function."""
    # Create mock surface profile
    contours = [
        {
            'points': [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)],
            'attributes': {'elevation': 100.0}
        },
        {
            'points': [(50, 50), (100, 50), (100, 100), (50, 100), (50, 50)],
            'attributes': {'elevation': 110.0}
        }
    ]
    
    profile = SurfaceProfile(
        contours=contours,
        scale_info=None,
        bounds=(0.0, 0.0, 100.0, 100.0),
        elevation_range=(100.0, 110.0)
    )
    
    # Create elevation sampler
    elev = create_elevation_sampler(profile)
    
    # Test sampling at various points
    assert elev(0, 0) == 100.0  # Should be exactly on first contour
    assert elev(75, 75) == 110.0  # Should be exactly on second contour
    
    # Test interpolation
    elevation = elev(25, 25)  # Should be interpolated
    assert 100.0 <= elevation <= 110.0


def test_sample_along_centerline_straight():
    """Test sampling along a straight centerline."""
    # Create straight centerline
    centerline = LineString([(0, 0), (100, 0)])
    
    # Create mock elevation sampler
    def mock_elev(x, y):
        return 100.0 + x * 0.1  # Linear elevation increase
    
    # Sample along centerline
    samples = sample_along_centerline(centerline, mock_elev, sample_spacing=20.0)
    
    assert len(samples) >= 5  # Should have at least 5 samples
    assert samples[0][0] == 0.0  # First station should be 0
    assert samples[-1][0] == 100.0  # Last station should be 100
    
    # Check that elevations increase along the line
    for i in range(len(samples) - 1):
        assert samples[i][1] <= samples[i + 1][1]


def test_sample_along_centerline_curved():
    """Test sampling along a curved centerline."""
    # Create curved centerline (arc)
    points = []
    for i in range(21):  # 20 segments
        angle = i * math.pi / 20  # 0 to π
        x = 50 + 50 * math.cos(angle)
        y = 50 + 50 * math.sin(angle)
        points.append((x, y))
    
    centerline = LineString(points)
    
    # Create mock elevation sampler
    def mock_elev(x, y):
        return 100.0 + math.sqrt((x - 50)**2 + (y - 50)**2) * 0.1
    
    # Sample along centerline
    samples = sample_along_centerline(centerline, mock_elev, sample_spacing=10.0)
    
    assert len(samples) >= 10  # Should have multiple samples
    assert samples[0][0] == 0.0  # First station should be 0
    
    # Check that elevations are reasonable
    for station, elevation in samples:
        assert 100.0 <= elevation <= 110.0


def test_parse_profile_from_text():
    """Test parsing ground level profile from text elements."""
    # Create mock text elements with elevation data
    text_elements = [
        {'text': 'EL. 100.0', 'x': 0, 'y': 0},
        {'text': 'ELEV 105.5', 'x': 50, 'y': 0},
        {'text': '110.0 FT', 'x': 100, 'y': 0},
        {'text': 'Some other text', 'x': 25, 'y': 0},  # Should be ignored
        {'text': 'EL. 115.2', 'x': 150, 'y': 0}
    ]
    
    # Parse profile
    profile_points = parse_profile_from_text(text_elements)
    
    assert profile_points is not None
    assert len(profile_points) == 4  # Should find 4 elevation points
    
    # Check that points are sorted by station
    for i in range(len(profile_points) - 1):
        assert profile_points[i].station <= profile_points[i + 1].station
    
    # Check specific elevations
    elevations = [p.elevation for p in profile_points]
    assert 100.0 in elevations
    assert 105.5 in elevations
    assert 110.0 in elevations
    assert 115.2 in elevations


def test_create_ground_level_function():
    """Test creating ground level function from profile points."""
    # Create mock profile points
    profile_points = [
        ProfilePoint(station=0.0, elevation=100.0, x=0, y=0),
        ProfilePoint(station=50.0, elevation=105.0, x=50, y=0),
        ProfilePoint(station=100.0, elevation=110.0, x=100, y=0)
    ]
    
    # Create ground level function
    ground_level = create_ground_level_function(profile_points)
    
    # Test interpolation
    assert ground_level(0.0) == 100.0
    assert ground_level(50.0) == 105.0
    assert ground_level(100.0) == 110.0
    
    # Test interpolation between points
    assert ground_level(25.0) == 102.5  # Midpoint between 100 and 105
    assert ground_level(75.0) == 107.5  # Midpoint between 105 and 110
    
    # Test extrapolation
    assert ground_level(-10.0) == 100.0  # Should use first point
    assert ground_level(150.0) == 110.0  # Should use last point


def test_tolerance_checks():
    """Test tolerance checks for elevation sampling."""
    # Create mock surface with known elevations
    contours = [
        {
            'points': [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)],
            'attributes': {'elevation': 100.0}
        }
    ]
    
    profile = SurfaceProfile(
        contours=contours,
        scale_info=None,
        bounds=(0.0, 0.0, 100.0, 100.0),
        elevation_range=(100.0, 100.0)
    )
    
    elev = create_elevation_sampler(profile)
    
    # Test sampling at known points
    assert abs(elev(0, 0) - 100.0) < 0.1  # Should be close to 100
    assert abs(elev(50, 50) - 100.0) < 0.1  # Should be close to 100
    assert abs(elev(100, 100) - 100.0) < 0.1  # Should be close to 100


def test_elevation_sampling_edge_cases():
    """Test elevation sampling with edge cases."""
    # Test with no contours
    empty_profile = SurfaceProfile(
        contours=[],
        scale_info=None,
        bounds=(0.0, 0.0, 100.0, 100.0),
        elevation_range=(0.0, 0.0)
    )
    
    elev = create_elevation_sampler(empty_profile)
    assert elev(50, 50) == 0.0  # Should return default elevation
    
    # Test with single contour
    single_contour = SurfaceProfile(
        contours=[{
            'points': [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)],
            'attributes': {'elevation': 100.0}
        }],
        scale_info=None,
        bounds=(0.0, 0.0, 100.0, 100.0),
        elevation_range=(100.0, 100.0)
    )
    
    elev = create_elevation_sampler(single_contour)
    assert abs(elev(50, 50) - 100.0) < 0.1


def test_centerline_sampling_tolerance():
    """Test centerline sampling with tolerance checks."""
    # Create centerline with known length
    centerline = LineString([(0, 0), (100, 0)])
    
    # Create elevation sampler with known pattern
    def mock_elev(x, y):
        return 100.0 + x * 0.1  # Linear increase
    
    # Test different sample spacings
    for spacing in [5.0, 10.0, 20.0, 50.0]:
        samples = sample_along_centerline(centerline, mock_elev, sample_spacing=spacing)
        
        # Check that samples are evenly spaced
        if len(samples) > 1:
            for i in range(len(samples) - 1):
                station_diff = samples[i + 1][0] - samples[i][0]
                assert abs(station_diff - spacing) < 0.1  # Within tolerance
        
        # Check that elevations are reasonable
        for station, elevation in samples:
            expected_elevation = 100.0 + station * 0.1
            assert abs(elevation - expected_elevation) < 0.1


def test_profile_parsing_edge_cases():
    """Test profile parsing with edge cases."""
    # Test with no elevation text
    text_elements = [
        {'text': 'Some text', 'x': 0, 'y': 0},
        {'text': 'More text', 'x': 50, 'y': 0}
    ]
    
    profile_points = parse_profile_from_text(text_elements)
    assert profile_points is None
    
    # Test with single elevation
    text_elements = [
        {'text': 'EL. 100.0', 'x': 0, 'y': 0}
    ]
    
    profile_points = parse_profile_from_text(text_elements)
    assert profile_points is not None
    assert len(profile_points) == 1
    assert profile_points[0].elevation == 100.0


def test_ground_level_function_edge_cases():
    """Test ground level function with edge cases."""
    # Test with no profile points
    ground_level = create_ground_level_function([])
    assert ground_level(0.0) == 0.0
    assert ground_level(100.0) == 0.0
    
    # Test with single profile point
    profile_points = [ProfilePoint(station=0.0, elevation=100.0, x=0, y=0)]
    ground_level = create_ground_level_function(profile_points)
    assert ground_level(0.0) == 100.0
    assert ground_level(100.0) == 100.0  # Should use single point


def test_complex_centerline_sampling():
    """Test sampling along complex centerline geometries."""
    # Create S-curve centerline
    points = []
    for i in range(101):  # 100 segments
        t = i / 100.0
        x = t * 100.0
        y = 50.0 * math.sin(t * math.pi)  # S-curve
        points.append((x, y))
    
    centerline = LineString(points)
    
    # Create elevation sampler
    def mock_elev(x, y):
        return 100.0 + y * 0.1  # Elevation varies with y
    
    # Sample along centerline
    samples = sample_along_centerline(centerline, mock_elev, sample_spacing=10.0)
    
    assert len(samples) >= 10
    assert samples[0][0] == 0.0
    assert samples[-1][0] == centerline.length
    
    # Check that elevations vary with the curve
    elevations = [elev for _, elev in samples]
    assert min(elevations) < max(elevations)  # Should have variation


def test_elevation_interpolation_accuracy():
    """Test accuracy of elevation interpolation."""
    # Create known elevation field
    contours = [
        {
            'points': [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)],
            'attributes': {'elevation': 100.0}
        },
        {
            'points': [(25, 25), (75, 25), (75, 75), (25, 75), (25, 25)],
            'attributes': {'elevation': 110.0}
        }
    ]
    
    profile = SurfaceProfile(
        contours=contours,
        scale_info=None,
        bounds=(0.0, 0.0, 100.0, 100.0),
        elevation_range=(100.0, 110.0)
    )
    
    elev = create_elevation_sampler(profile)
    
    # Test interpolation accuracy
    # Point at center should be closer to inner contour
    center_elevation = elev(50, 50)
    assert 105.0 <= center_elevation <= 110.0
    
    # Point at corner should be closer to outer contour
    corner_elevation = elev(0, 0)
    assert 100.0 <= corner_elevation <= 105.0
