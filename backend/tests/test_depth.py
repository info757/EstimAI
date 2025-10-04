"""
Unit tests for depth calculation utilities.

Tests depth sampling, trench volume calculations, and bucket analysis
using synthetic profiles and ground functions.
"""
import pytest
from backend.app.services.detectors.depth import (
    init_depth_config, od_ft, sample_depth_along_run, summarize_depth
)


def test_od_ft_lookup():
    """Test outside diameter lookup for different materials."""
    init_depth_config()
    
    # Test PVC pipe
    od = od_ft("pvc", 12.0)
    assert od > 0
    assert od < 2.0  # Should be reasonable for 12" pipe
    
    # Test RCP pipe
    od = od_ft("rcp", 15.0)
    assert od > 0
    assert od < 2.0  # Should be reasonable for 15" pipe
    
    # Test fallback for unknown material
    od = od_ft("unknown", 8.0)
    assert od > 0
    assert od < 2.0  # Should use fallback calculation


def test_sample_depth_along_run():
    """Test depth sampling along pipe run with synthetic profile."""
    init_depth_config()
    
    # Create synthetic s-profile (station -> invert elevation)
    s_profile = [
        (0.0, 100.0),    # Start at elevation 100ft
        (50.0, 98.0),    # Midpoint at elevation 98ft
        (100.0, 96.0)    # End at elevation 96ft (4ft drop)
    ]
    
    # Linear ground profile function
    def ground_at_s(station: float) -> float:
        return 102.0 - (station * 0.02)  # Ground drops 2ft over 100ft run
    
    # Sample depth along run
    samples = sample_depth_along_run(
        s_profile, ground_at_s, "pvc", 12.0, n_samples=10
    )
    
    assert len(samples) == 10
    
    # Check that depths are reasonable
    for sample in samples:
        assert sample.depth_ft > 0
        assert sample.depth_ft < 10  # Should be reasonable depth
        assert sample.cover_ft > 0
        assert sample.trench_area_sf > 0


def test_summarize_depth():
    """Test depth summary calculation with synthetic samples."""
    from backend.app.services.detectors.depth import DepthSample
    
    # Create synthetic depth samples
    samples = [
        DepthSample(station=0.0, invert_ft=100.0, ground_ft=102.0, depth_ft=2.0, cover_ft=1.5, trench_area_sf=10.0),
        DepthSample(station=25.0, invert_ft=99.0, ground_ft=101.5, depth_ft=2.5, cover_ft=2.0, trench_area_sf=12.0),
        DepthSample(station=50.0, invert_ft=98.0, ground_ft=101.0, depth_ft=3.0, cover_ft=2.5, trench_area_sf=14.0),
        DepthSample(station=75.0, invert_ft=97.0, ground_ft=100.5, depth_ft=3.5, cover_ft=3.0, trench_area_sf=16.0),
        DepthSample(station=100.0, invert_ft=96.0, ground_ft=100.0, depth_ft=4.0, cover_ft=3.5, trench_area_sf=18.0),
    ]
    
    # Calculate summary
    summary = summarize_depth(samples, "storm")
    
    # Check depth statistics
    assert summary.min_depth_ft == 2.0
    assert summary.max_depth_ft == 4.0
    assert summary.avg_depth_ft == 3.0
    assert summary.p95_depth_ft >= 3.0
    
    # Check buckets (should have some in each range)
    assert summary.buckets_lf["0-5"] > 0
    assert summary.buckets_lf["5-8"] == 0  # No samples in 5-8ft range
    assert summary.buckets_lf["8-12"] == 0
    assert summary.buckets_lf["12+"] == 0
    
    # Check trench volume (should be reasonable)
    assert summary.trench_volume_cy > 0
    assert summary.trench_volume_cy < 100  # Should be reasonable for 100ft pipe
    
    # Check validation flags
    assert summary.cover_ok is True  # All samples have good cover
    assert summary.deep_excavation is False  # No samples >= 12ft


def test_summarize_depth_deep_excavation():
    """Test depth summary with deep excavation samples."""
    from backend.app.services.detectors.depth import DepthSample
    
    # Create samples with deep excavation
    samples = [
        DepthSample(station=0.0, invert_ft=100.0, ground_ft=102.0, depth_ft=2.0, cover_ft=1.5, trench_area_sf=10.0),
        DepthSample(station=50.0, invert_ft=90.0, ground_ft=102.0, depth_ft=12.0, cover_ft=11.5, trench_area_sf=30.0),
        DepthSample(station=100.0, invert_ft=100.0, ground_ft=102.0, depth_ft=2.0, cover_ft=1.5, trench_area_sf=10.0),
    ]
    
    summary = summarize_depth(samples, "sanitary")
    
    # Check that deep excavation is flagged
    assert summary.deep_excavation is True
    assert summary.max_depth_ft == 12.0
    
    # Check buckets (should have some in 12+ range)
    assert summary.buckets_lf["12+"] > 0


def test_summarize_depth_low_cover():
    """Test depth summary with low cover samples."""
    from backend.app.services.detectors.depth import DepthSample
    
    # Create samples with low cover
    samples = [
        DepthSample(station=0.0, invert_ft=100.0, ground_ft=101.0, depth_ft=1.0, cover_ft=0.5, trench_area_sf=8.0),
        DepthSample(station=50.0, invert_ft=99.0, ground_ft=101.0, depth_ft=2.0, cover_ft=1.5, trench_area_sf=10.0),
        DepthSample(station=100.0, invert_ft=98.0, ground_ft=101.0, depth_ft=3.0, cover_ft=2.5, trench_area_sf=12.0),
    ]
    
    summary = summarize_depth(samples, "water")
    
    # Check that low cover is flagged
    assert summary.cover_ok is False
    assert summary.min_depth_ft == 1.0


def test_empty_samples():
    """Test depth summary with empty samples list."""
    from backend.app.services.detectors.depth import DepthSummary
    
    # Empty samples should return default summary
    summary = summarize_depth([], "storm")
    
    assert summary.min_depth_ft == 0.0
    assert summary.max_depth_ft == 0.0
    assert summary.avg_depth_ft == 0.0
    assert summary.p95_depth_ft == 0.0
    assert summary.buckets_lf["0-5"] == 0.0
    assert summary.trench_volume_cy == 0.0
    assert summary.cover_ok is True
    assert summary.deep_excavation is False


def test_trench_volume_calculation():
    """Test trench volume calculation with known values."""
    from backend.app.services.detectors.depth import DepthSample
    
    # Create samples with known trench areas
    samples = [
        DepthSample(station=0.0, invert_ft=100.0, ground_ft=102.0, depth_ft=2.0, cover_ft=1.5, trench_area_sf=10.0),
        DepthSample(station=50.0, invert_ft=99.0, ground_ft=101.0, depth_ft=2.0, cover_ft=1.5, trench_area_sf=10.0),
        DepthSample(station=100.0, invert_ft=98.0, ground_ft=100.0, depth_ft=2.0, cover_ft=1.5, trench_area_sf=10.0),
    ]
    
    summary = summarize_depth(samples, "storm")
    
    # Trench volume should be calculated from areas
    # Each sample has 10 sf over 50ft = 500 cf = ~18.5 cy
    expected_volume = 3 * 10.0 * 50.0 / 27.0  # 3 segments * 10 sf * 50 ft / 27 cf per cy
    assert abs(summary.trench_volume_cy - expected_volume) < 1.0  # Within 1 cy tolerance