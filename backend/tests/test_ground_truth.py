"""Ground truth comparison tests for deterministic validation.

This module provides tests to compare agent results against golden reference
data to ensure consistent and accurate takeoff results.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient

from backend.app.app import create_app


def load_golden_reference() -> Dict[str, Any]:
    """Load the golden reference metrics."""
    golden_path = Path(__file__).parent / "golden_reference.json"
    with open(golden_path) as f:
        return json.load(f)


def check_tolerance(actual: float, expected: float, tolerance_pct: float, metric_name: str) -> tuple[bool, str]:
    """Check if actual value is within tolerance of expected value.
    
    Returns:
        Tuple of (passed, message)
    """
    if expected == 0:
        passed = actual == 0
        message = f"{metric_name}: {actual} (expected exactly 0)"
    else:
        diff_pct = abs(actual - expected) / expected * 100
        passed = diff_pct <= tolerance_pct
        message = f"{metric_name}: {actual} vs {expected} (±{tolerance_pct}% = {diff_pct:.2f}%)"
    
    return passed, message


@pytest.mark.skipif(
    os.getenv("ESTIMAI_SEED") != "42",
    reason="Ground truth tests require ESTIMAI_SEED=42 for reproducibility"
)
@pytest.mark.ground_truth
def test_ground_truth_comparison():
    """Compare agent results against golden reference with tolerances.
    
    This test verifies:
    1. Pipe count matches exactly
    2. Total LF within ±3%
    3. Depth stats within ±5%
    4. Trench volume within ±5%
    5. Depth buckets within ±3%
    """
    # Load golden reference
    golden = load_golden_reference()
    expected = golden["expected_metrics"]
    
    # Get PDF path
    pdf_path = Path(golden["pdf_file"])
    if not pdf_path.exists():
        pytest.skip(f"Golden PDF not found: {pdf_path}")
    
    # Create test client
    app = create_app()
    client = TestClient(app)
    
    # Run agent takeoff
    with open(pdf_path, "rb") as f:
        response = client.post(
            "/v1/agent/takeoff",
            files={"file": f},
            data={"session_id": "ground_truth_test"}
        )
    
    assert response.status_code == 200, f"Agent failed: {response.text}"
    result = response.json()
    
    # Check that agent completed successfully
    assert result.get("proposed_review") is not None, "Agent did not produce a proposal"
    assert result.get("error") is None, f"Agent returned error: {result.get('error')}"
    
    # Extract metrics from result
    summary = result.get("summary", {})
    payload = result.get("proposed_review", {}).get("payload", {})
    networks = payload.get("networks", {})
    
    # Collect all test results
    all_checks = []
    
    # 1. Check total pipes (exact match required)
    pipes_total_actual = summary.get("pipes_total", 0)
    pipes_total_expected = expected["pipes_total"]["value"]
    passed, msg = check_tolerance(
        pipes_total_actual,
        pipes_total_expected,
        expected["pipes_total"]["tolerance_pct"],
        "Total Pipes"
    )
    all_checks.append((passed, msg))
    
    # 2. Check total LF across all networks
    total_lf_actual = 0
    for network_name, network_data in networks.items():
        pipes = network_data.get("pipes", [])
        for pipe in pipes:
            total_lf_actual += pipe.get("length_ft", 0)
    
    passed, msg = check_tolerance(
        total_lf_actual,
        expected["total_length_lf"]["value"],
        expected["total_length_lf"]["tolerance_pct"],
        "Total LF"
    )
    all_checks.append((passed, msg))
    
    # 3. Check per-network metrics
    for network_name, network_expected in expected["networks"].items():
        if network_name in networks:
            network_data = networks[network_name]
            pipes = network_data.get("pipes", [])
            
            # Check pipe count
            pipe_count_actual = len(pipes)
            pipe_count_expected = network_expected["pipe_count"]
            passed, msg = check_tolerance(
                pipe_count_actual,
                pipe_count_expected,
                0,  # Exact match for count
                f"{network_name.title()} Pipe Count"
            )
            all_checks.append((passed, msg))
            
            # Check total LF for this network
            network_lf = sum(p.get("length_ft", 0) for p in pipes)
            passed, msg = check_tolerance(
                network_lf,
                network_expected["total_lf"],
                network_expected["tolerance_pct"],
                f"{network_name.title()} Total LF"
            )
            all_checks.append((passed, msg))
    
    # 4. Check depth statistics (aggregate across all pipes)
    all_depths = []
    total_trench_cy = 0
    
    for network_name, network_data in networks.items():
        pipes = network_data.get("pipes", [])
        for pipe in pipes:
            if pipe.get("avg_depth_ft"):
                all_depths.append(pipe["avg_depth_ft"])
            extra = pipe.get("extra", {})
            total_trench_cy += extra.get("trench_volume_cy", 0)
    
    if all_depths:
        avg_depth_actual = sum(all_depths) / len(all_depths)
        min_depth_actual = min(all_depths)
        max_depth_actual = max(all_depths)
        
        # Check average depth
        passed, msg = check_tolerance(
            avg_depth_actual,
            expected["depth_stats"]["avg_depth_ft"]["value"],
            expected["depth_stats"]["avg_depth_ft"]["tolerance_pct"],
            "Average Depth"
        )
        all_checks.append((passed, msg))
        
        # Check min depth
        passed, msg = check_tolerance(
            min_depth_actual,
            expected["depth_stats"]["min_depth_ft"]["value"],
            expected["depth_stats"]["min_depth_ft"]["tolerance_pct"],
            "Min Depth"
        )
        all_checks.append((passed, msg))
        
        # Check max depth
        passed, msg = check_tolerance(
            max_depth_actual,
            expected["depth_stats"]["max_depth_ft"]["value"],
            expected["depth_stats"]["max_depth_ft"]["tolerance_pct"],
            "Max Depth"
        )
        all_checks.append((passed, msg))
    
    # 5. Check trench volume
    passed, msg = check_tolerance(
        total_trench_cy,
        expected["trench_volume_cy"]["value"],
        expected["trench_volume_cy"]["tolerance_pct"],
        "Total Trench Volume (CY)"
    )
    all_checks.append((passed, msg))
    
    # 6. Check depth buckets (aggregate from all pipes)
    depth_buckets_actual = {
        "d_0_5": 0,
        "d_5_8": 0,
        "d_8_12": 0,
        "d_12_plus": 0
    }
    
    for network_name, network_data in networks.items():
        pipes = network_data.get("pipes", [])
        for pipe in pipes:
            extra = pipe.get("extra", {})
            buckets_lf = extra.get("buckets_lf", {})
            for bucket_name, lf in buckets_lf.items():
                if bucket_name in depth_buckets_actual:
                    depth_buckets_actual[bucket_name] += lf
    
    for bucket_name, bucket_expected in expected["depth_buckets"].items():
        bucket_actual = depth_buckets_actual.get(bucket_name, 0)
        passed, msg = check_tolerance(
            bucket_actual,
            bucket_expected["value"],
            bucket_expected["tolerance_pct"],
            f"Depth Bucket {bucket_name.replace('_', '-').upper()}"
        )
        all_checks.append((passed, msg))
    
    # Print all check results
    print("\n" + "="*80)
    print("GROUND TRUTH COMPARISON RESULTS")
    print("="*80)
    
    passed_count = sum(1 for passed, _ in all_checks if passed)
    total_count = len(all_checks)
    
    for passed, msg in all_checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {msg}")
    
    print("="*80)
    print(f"Results: {passed_count}/{total_count} checks passed")
    print("="*80)
    
    # Assert that all checks passed
    failed_checks = [msg for passed, msg in all_checks if not passed]
    assert len(failed_checks) == 0, f"\n{len(failed_checks)} checks failed:\n" + "\n".join(failed_checks)


@pytest.mark.ground_truth
def test_ground_truth_with_seed_check():
    """Verify that ESTIMAI_SEED is set for deterministic results."""
    seed = os.getenv("ESTIMAI_SEED")
    assert seed is not None, "ESTIMAI_SEED must be set for ground truth tests"
    assert seed == "42", f"ESTIMAI_SEED must be 42 for golden reference, got: {seed}"
    print(f"✅ ESTIMAI_SEED={seed} - Deterministic mode enabled")


if __name__ == "__main__":
    # Allow running this test directly
    pytest.main([__file__, "-v", "-s", "-m", "ground_truth"])

