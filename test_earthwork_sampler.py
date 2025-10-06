#!/usr/bin/env python3
"""
Simple test script for earthwork surface sampler functionality.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.services.earthwork_surface import (
    load_surface_from_pdf, make_ground_sampler, sample_ground_along_centerline
)
from backend.app.services.profiles.parser import parse_profile_gl
from shapely.geometry import LineString

def test_surface_sampling():
    """Test surface sampling functionality."""
    print("Testing surface sampling...")
    
    # Test 1: Load surface from PDF
    surface = load_surface_from_pdf("test_file.pdf")
    assert surface is not None
    assert surface.source_type == "contours"
    print("✅ Surface loading works")
    
    # Test 2: Ground sampler with profile GL
    profile_gl = [(0.0, 100.0), (100.0, 95.0), (200.0, 90.0)]
    sampler, source = make_ground_sampler(profile_gl=profile_gl)
    assert source == "profile"
    assert sampler(0.0) == 100.0
    assert sampler(100.0) == 95.0
    assert sampler(200.0) == 90.0
    print("✅ Profile GL sampling works")
    
    # Test 3: Ground sampler with constant fallback
    sampler, source = make_ground_sampler(constant=85.5)
    assert source == "constant"
    assert sampler(0.0) == 85.5
    assert sampler(100.0) == 85.5
    print("✅ Constant fallback works")
    
    # Test 4: Surface sampling along centerline
    centerline = LineString([(0, 0), (100, 0)])
    def mock_sampler(station: float) -> float:
        return 100.0 - station * 0.1
    
    samples = sample_ground_along_centerline(centerline, mock_sampler, n_samples=5)
    assert len(samples) == 5
    assert samples[0] == (0.0, 100.0)
    assert samples[-1] == (100.0, 90.0)
    print("✅ Centerline sampling works")
    
    print("All surface sampling tests passed! ✅")

def test_profile_parsing():
    """Test profile parsing functionality."""
    print("Testing profile parsing...")
    
    # Test 1: Parse GL profile
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
    print("✅ GL profile parsing works")
    
    print("All profile parsing tests passed! ✅")

def test_discipline_integration():
    """Test discipline extractor integration."""
    print("Testing discipline integration...")
    
    # Test sanitary network integration
    from backend.app.services.detectors.sanitary import attach_labels
    
    class MockPipe:
        def __init__(self):
            self.id = "test_pipe"
            self.mat = "pvc"
            self.dia_in = 8.0
            self.avg_depth_ft = None
            self.extra = {}
    
    pipe = MockPipe()
    
    # Test with profile GL data
    sheet_data = {
        "texts": [
            {"text": "0+00 100.0", "x": 0, "y": 0},
            {"text": "100 95.0", "x": 100, "y": 0}
        ]
    }
    
    pipes = attach_labels([pipe], [], file_ref="test.pdf", sheet_data=sheet_data)
    
    assert len(pipes) == 1
    assert pipes[0].extra.get("_ground_source") == "profile"
    assert pipes[0].avg_depth_ft is not None
    print("✅ Discipline integration works")
    
    print("All discipline integration tests passed! ✅")

if __name__ == "__main__":
    print("🧪 Testing Earthwork Surface Sampler & Profile Parser")
    print("=" * 60)
    
    try:
        test_surface_sampling()
        print()
        test_profile_parsing()
        print()
        test_discipline_integration()
        print()
        print("🎉 All tests passed! Earthwork surface sampler is working correctly.")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
