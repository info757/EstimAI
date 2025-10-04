"""
Unit tests for depth calculation utilities.
"""
import pytest
import tempfile
import json
from pathlib import Path
from backend.app.services.detectors.depth import (
    init_depth_config, od_ft, sample_depth_along_run, summarize_depth,
    DepthSample, DepthSummary
)


def test_od_ft_basic():
    """Test basic OD lookup functionality."""
    # Test with fallback values
    result = od_ft("pvc", 8.0)
    assert result > 0
    assert result > 8.0 / 12.0  # Should be larger than nominal diameter
    
    # Test with unknown material
    result = od_ft("unknown", 6.0)
    assert result > 0


def test_od_ft_with_config():
    """Test OD lookup with configuration file."""
    # Create temporary config
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "pipes"
        config_dir.mkdir()
        
        od_config = {
            "pvc": {"8": 8.625, "12": 12.75},
            "rcp": {"12": 12.0, "15": 15.0}
        }
        
        with open(config_dir / "od_lookup.json", 'w') as f:
            json.dump(od_config, f)
        
        # Initialize with temp config
        init_depth_config(temp_dir)
        
        # Test known values
        result = od_ft("pvc", 8.0)
        assert abs(result - (8.625 / 12.0)) < 0.001
        
        result = od_ft("rcp", 12.0)
        assert abs(result - (12.0 / 12.0)) < 0.001


def test_sample_depth_along_run():
    """Test depth sampling along pipe run."""
    # Simple linear profile
    s_profile = [(0.0, 100.0), (1.0, 98.0)]  # 2ft drop over run
    
    # Linear ground function
    def ground_at_s(station):
        return 102.0 - (station * 2.0)  # Ground drops 2ft over run
    
    samples = sample_depth_along_run(
        s_profile, ground_at_s, "pvc", 8.0, n_samples=5
    )
    
    assert len(samples) == 5
    assert samples[0].station == 0.0
    assert samples[-1].station == 1.0
    
    # Check that depths are reasonable
    for sample in samples:
        assert sample.depth_ft > 0
        assert sample.cover_ft > 0
        assert sample.trench_width_ft > 0
        assert sample.trench_area_sf > 0


def test_sample_depth_along_run_empty_profile():
    """Test depth sampling with empty profile."""
    samples = sample_depth_along_run([], lambda s: 100.0, "pvc", 8.0)
    assert len(samples) == 0


def test_sample_depth_along_run_single_point():
    """Test depth sampling with single point profile."""
    s_profile = [(0.5, 100.0)]
    
    def ground_at_s(station):
        return 102.0
    
    samples = sample_depth_along_run(
        s_profile, ground_at_s, "pvc", 8.0, n_samples=3
    )
    
    assert len(samples) == 3
    # All samples should have same values since single point
    assert all(s.invert_ft == 100.0 for s in samples)


def test_summarize_depth():
    """Test depth summary calculation."""
    # Create synthetic samples
    samples = [
        DepthSample(0.0, 100.0, 102.0, 2.0, 1.5, 2.0, 4.0),
        DepthSample(0.5, 99.0, 101.0, 2.0, 1.5, 2.0, 4.0),
        DepthSample(1.0, 98.0, 100.0, 2.0, 1.5, 2.0, 4.0),
    ]
    
    summary = summarize_depth(samples, "storm")
    
    assert summary.min_depth_ft == 2.0
    assert summary.max_depth_ft == 2.0
    assert summary.avg_depth_ft == 2.0
    assert summary.p95_depth_ft == 2.0
    assert summary.trench_volume_cy > 0
    assert summary.cover_ok is True
    assert summary.deep_excavation is False
    
    # Check buckets
    assert "0-5" in summary.buckets_lf
    assert "5-8" in summary.buckets_lf
    assert "8-12" in summary.buckets_lf
    assert "12+" in summary.buckets_lf


def test_summarize_depth_empty():
    """Test depth summary with empty samples."""
    summary = summarize_depth([], "storm")
    
    assert summary.min_depth_ft == 0.0
    assert summary.max_depth_ft == 0.0
    assert summary.avg_depth_ft == 0.0
    assert summary.p95_depth_ft == 0.0
    assert summary.trench_volume_cy == 0.0
    assert summary.cover_ok is True
    assert summary.deep_excavation is False


def test_summarize_depth_deep_excavation():
    """Test depth summary with deep excavation."""
    # Create samples with deep excavation
    samples = [
        DepthSample(0.0, 90.0, 102.0, 12.0, 11.5, 2.0, 24.0),
        DepthSample(1.0, 88.0, 100.0, 12.0, 11.5, 2.0, 24.0),
    ]
    
    summary = summarize_depth(samples, "storm")
    
    assert summary.deep_excavation is True
    assert summary.min_depth_ft == 12.0
    assert summary.max_depth_ft == 12.0


def test_summarize_depth_cover_violation():
    """Test depth summary with cover violations."""
    # Create samples with insufficient cover
    samples = [
        DepthSample(0.0, 100.0, 101.0, 1.0, 0.5, 2.0, 2.0),  # Only 0.5ft cover
        DepthSample(1.0, 99.0, 100.5, 1.5, 1.0, 2.0, 3.0),  # Only 1.0ft cover
    ]
    
    summary = summarize_depth(samples, "storm")  # Requires 1.5ft minimum
    
    assert summary.cover_ok is False


def test_linear_ground_function():
    """Test with simple linear ground function."""
    s_profile = [(0.0, 100.0), (1.0, 95.0)]  # 5ft drop
    
    def linear_ground(station):
        return 105.0 - (station * 3.0)  # Ground drops 3ft
    
    samples = sample_depth_along_run(
        s_profile, linear_ground, "pvc", 12.0, n_samples=10
    )
    
    assert len(samples) == 10
    
    # Check that depths vary along the run
    depths = [s.depth_ft for s in samples]
    assert min(depths) != max(depths)  # Should have variation
    
    # Check interpolation
    assert samples[0].station == 0.0
    assert samples[-1].station == 1.0
    assert samples[0].invert_ft == 100.0
    assert samples[-1].invert_ft == 95.0


def test_trench_area_calculation():
    """Test trench area calculation."""
    s_profile = [(0.0, 100.0), (1.0, 100.0)]
    
    def ground_at_s(station):
        return 105.0  # Constant 5ft depth
    
    samples = sample_depth_along_run(
        s_profile, ground_at_s, "pvc", 8.0, n_samples=5
    )
    
    for sample in samples:
        # Trench area should be positive
        assert sample.trench_area_sf > 0
        
        # Trench width should be reasonable
        assert sample.trench_width_ft > 0.5  # At least pipe OD + clearance
