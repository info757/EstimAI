"""
Test surface sampling utilities for ground elevation.

Tests straight and curved centerlines, interpolation accuracy,
and fallback strategies for ground elevation sampling.
"""
import pytest
import numpy as np
from shapely.geometry import LineString, Point
from backend.app.services.earthwork_surface import (
    load_surface_from_pdf, make_ground_sampler, sample_ground_along_centerline,
    validate_surface_sampling, create_ground_level_function
)


class TestSurfaceSampling:
    """Test surface sampling functionality."""
    
    def test_load_surface_from_pdf_mock(self):
        """Test loading surface from PDF (mock implementation)."""
        surface = load_surface_from_pdf("test_file.pdf")
        
        assert surface is not None
        assert surface.source_type == "contours"
        assert surface.elev_func is not None
        assert surface.sample_along is not None
        assert surface.metadata["file"] == "test_file.pdf"
    
    def test_load_surface_from_pdf_nonexistent(self):
        """Test loading surface from nonexistent PDF."""
        surface = load_surface_from_pdf("nonexistent.pdf")
        
        # Should return None for nonexistent files
        assert surface is None
    
    def test_make_ground_sampler_profile_priority(self):
        """Test ground sampler with profile GL data (highest priority)."""
        profile_gl = [(0.0, 100.0), (100.0, 95.0), (200.0, 90.0)]
        
        sampler, source = make_ground_sampler(
            profile_gl=profile_gl,
            surface=None,
            constant=50.0
        )
        
        assert source == "profile"
        assert sampler(0.0) == 100.0
        assert sampler(100.0) == 95.0
        assert sampler(200.0) == 90.0
        assert abs(sampler(50.0) - 97.5) < 0.1  # Interpolated value
    
    def test_make_ground_sampler_surface_fallback(self):
        """Test ground sampler with surface fallback."""
        # Mock surface
        class MockSurface:
            def __init__(self):
                self.elev_func = lambda x, y: 100.0 - x * 0.1
                self.sample_along = lambda line: [(0.0, 100.0), (100.0, 90.0)]
        
        surface = MockSurface()
        
        sampler, source = make_ground_sampler(
            profile_gl=None,
            surface=surface,
            constant=50.0
        )
        
        assert source == "surface"
        # Surface sampler would need centerline for real sampling
        # For now, just verify it returns a function
        assert callable(sampler)
    
    def test_make_ground_sampler_constant_fallback(self):
        """Test ground sampler with constant fallback."""
        sampler, source = make_ground_sampler(
            profile_gl=None,
            surface=None,
            constant=85.5
        )
        
        assert source == "constant"
        assert sampler(0.0) == 85.5
        assert sampler(100.0) == 85.5
        assert sampler(1000.0) == 85.5
    
    def test_make_ground_sampler_final_fallback(self):
        """Test ground sampler with final fallback (no data)."""
        sampler, source = make_ground_sampler(
            profile_gl=None,
            surface=None,
            constant=None
        )
        
        assert source == "constant"
        assert sampler(0.0) == 0.0
        assert sampler(100.0) == 0.0
    
    def test_sample_ground_along_centerline_straight(self):
        """Test sampling along straight centerline."""
        # Create straight line
        centerline = LineString([(0, 0), (100, 0)])
        
        def mock_sampler(station: float) -> float:
            return 100.0 - station * 0.1
        
        samples = sample_ground_along_centerline(centerline, mock_sampler, n_samples=5)
        
        assert len(samples) == 5
        assert samples[0] == (0.0, 100.0)  # Start
        assert samples[-1] == (100.0, 90.0)  # End
        assert all(isinstance(s[0], float) for s in samples)  # Station values
        assert all(isinstance(s[1], float) for s in samples)  # Elevation values
    
    def test_sample_ground_along_centerline_curved(self):
        """Test sampling along curved centerline."""
        # Create curved line (arc)
        import math
        coords = []
        for i in range(21):  # 20 segments
            angle = i * math.pi / 20  # 0 to π
            x = 50 * math.cos(angle)
            y = 50 * math.sin(angle)
            coords.append((x, y))
        
        centerline = LineString(coords)
        
        def mock_sampler(station: float) -> float:
            return 100.0 - station * 0.05
        
        samples = sample_ground_along_centerline(centerline, mock_sampler, n_samples=10)
        
        assert len(samples) == 10
        assert samples[0][0] == 0.0  # Start station
        assert samples[-1][0] == centerline.length  # End station
        assert all(s[0] <= s[1] for s in zip(samples[:-1], samples[1:]))  # Monotonic stationing
    
    def test_sample_ground_along_centerline_empty(self):
        """Test sampling along empty centerline."""
        centerline = LineString([])
        
        def mock_sampler(station: float) -> float:
            return 100.0
        
        samples = sample_ground_along_centerline(centerline, mock_sampler)
        
        assert samples == []
    
    def test_validate_surface_sampling_valid(self):
        """Test validation of valid surface sampling."""
        samples = [
            (0.0, 100.0),
            (25.0, 99.5),
            (50.0, 99.0),
            (75.0, 98.5),
            (100.0, 98.0)
        ]
        
        assert validate_surface_sampling(samples, tolerance_ft=0.2) == True
    
    def test_validate_surface_sampling_non_monotonic(self):
        """Test validation of non-monotonic stationing."""
        samples = [
            (0.0, 100.0),
            (50.0, 99.0),
            (25.0, 98.5),  # Non-monotonic stationing
            (75.0, 98.0),
            (100.0, 97.5)
        ]
        
        assert validate_surface_sampling(samples, tolerance_ft=0.2) == False
    
    def test_validate_surface_sampling_large_change(self):
        """Test validation with large elevation changes."""
        samples = [
            (0.0, 100.0),
            (25.0, 50.0),  # Large drop
            (50.0, 49.0),
            (75.0, 48.0),
            (100.0, 47.0)
        ]
        
        assert validate_surface_sampling(samples, tolerance_ft=0.2) == False
    
    def test_validate_surface_sampling_insufficient_points(self):
        """Test validation with insufficient points."""
        samples = [(0.0, 100.0)]
        
        assert validate_surface_sampling(samples, tolerance_ft=0.2) == True  # Single point is valid
    
    def test_create_ground_level_function(self):
        """Test creating ground level function from profile points."""
        profile_points = [(0.0, 100.0), (50.0, 95.0), (100.0, 90.0)]
        
        ground_func = create_ground_level_function(profile_points)
        
        assert ground_func(0.0) == 100.0
        assert ground_func(50.0) == 95.0
        assert ground_func(100.0) == 90.0
        assert abs(ground_func(25.0) - 97.5) < 0.1  # Interpolated
        assert abs(ground_func(75.0) - 92.5) < 0.1  # Interpolated
    
    def test_create_ground_level_function_empty(self):
        """Test creating ground level function with empty profile."""
        ground_func = create_ground_level_function([])
        
        assert ground_func(0.0) == 0.0
        assert ground_func(100.0) == 0.0
    
    def test_create_ground_level_function_single_point(self):
        """Test creating ground level function with single point."""
        profile_points = [(50.0, 95.0)]
        
        ground_func = create_ground_level_function(profile_points)
        
        assert ground_func(0.0) == 95.0
        assert ground_func(50.0) == 95.0
        assert ground_func(100.0) == 95.0
    
    def test_ground_sampler_interpolation_accuracy(self):
        """Test interpolation accuracy within tolerance."""
        profile_gl = [(0.0, 100.0), (100.0, 90.0)]
        
        sampler, _ = make_ground_sampler(profile_gl=profile_gl)
        
        # Test interpolation at various stations
        assert abs(sampler(25.0) - 97.5) < 0.1
        assert abs(sampler(50.0) - 95.0) < 0.1
        assert abs(sampler(75.0) - 92.5) < 0.1
    
    def test_ground_sampler_extrapolation(self):
        """Test extrapolation beyond profile range."""
        profile_gl = [(0.0, 100.0), (100.0, 90.0)]
        
        sampler, _ = make_ground_sampler(profile_gl=profile_gl)
        
        # Extrapolate beyond last point
        expected_150 = 90.0 + (150.0 - 100.0) * (90.0 - 100.0) / (100.0 - 0.0)
        assert abs(sampler(150.0) - expected_150) < 0.1
    
    def test_surface_sampling_tolerance_checks(self):
        """Test surface sampling with various tolerance settings."""
        samples = [
            (0.0, 100.0),
            (25.0, 99.8),
            (50.0, 99.6),
            (75.0, 99.4),
            (100.0, 99.2)
        ]
        
        # Should pass with reasonable tolerance
        assert validate_surface_sampling(samples, tolerance_ft=1.0) == True
        
        # Should fail with very strict tolerance
        assert validate_surface_sampling(samples, tolerance_ft=0.01) == False


class TestGroundSamplerIntegration:
    """Test integration of ground sampler with discipline extractors."""
    
    def test_sanitary_ground_sampler_integration(self):
        """Test sanitary network with ground sampler integration."""
        from backend.app.services.detectors.sanitary import attach_labels
        
        # Mock pipe
        class MockPipe:
            def __init__(self):
                self.id = "test_pipe"
                self.mat = "pvc"
                self.dia_in = 8.0
                self.avg_depth_ft = None
                self.extra = {}
        
        pipe = MockPipe()
        
        # Mock profile GL data
        sheet_data = {
            "texts": [
                {"text": "0+00 100.0", "x": 0, "y": 0},
                {"text": "100 95.0", "x": 100, "y": 0}
            ]
        }
        
        # Test with profile GL data
        pipes = attach_labels([pipe], [], file_ref="test.pdf", sheet_data=sheet_data)
        
        assert len(pipes) == 1
        assert pipes[0].extra.get("_ground_source") == "profile"
        assert pipes[0].avg_depth_ft is not None
    
    def test_storm_ground_sampler_integration(self):
        """Test storm network with ground sampler integration."""
        from backend.app.services.detectors.storm import attach_labels
        
        # Mock pipe
        class MockPipe:
            def __init__(self):
                self.id = "test_pipe"
                self.mat = "pvc"
                self.dia_in = 12.0
                self.avg_depth_ft = None
                self.extra = {}
        
        pipe = MockPipe()
        
        # Test with constant fallback
        pipes = attach_labels([pipe], [], file_ref=None, sheet_data=None)
        
        assert len(pipes) == 1
        assert pipes[0].extra.get("_ground_source") == "constant"
        assert pipes[0].avg_depth_ft is not None
    
    def test_water_ground_sampler_integration(self):
        """Test water network with ground sampler integration."""
        from backend.app.services.detectors.water import attach_labels
        
        # Mock pipe
        class MockPipe:
            def __init__(self):
                self.id = "test_pipe"
                self.mat = "ductile_iron"
                self.dia_in = 6.0
                self.avg_depth_ft = None
                self.extra = {}
        
        pipe = MockPipe()
        
        # Test with surface data
        pipes = attach_labels([pipe], [], file_ref="test.pdf", sheet_data=None)
        
        assert len(pipes) == 1
        assert pipes[0].extra.get("_ground_source") == "surface"
        assert pipes[0].avg_depth_ft is not None
