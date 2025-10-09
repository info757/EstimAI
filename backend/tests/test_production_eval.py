"""
Tests for production evaluation (without ground truth).
"""

import pytest
from backend.app.services.monitoring.production_eval import (
    check_consistency,
    assess_extraction_quality,
    calculate_overall_confidence,
    evaluate_production_run
)


def test_consistency_checks_pass():
    """Test that good data passes consistency checks."""
    result = {
        "pipes": [
            {
                "discipline": "storm",
                "material": "PVC",
                "dia_in": 12,
                "length_ft": 100.0,
                "invert_in": 420.0,
                "invert_out": 419.0,
                "ground_level": 425.0
            }
        ]
    }
    
    checks = check_consistency(result)
    
    # Should have multiple checks
    assert len(checks) > 0
    
    # Most should pass (score = 1.0)
    passing = [c for c in checks if c[1] == 1.0]
    assert len(passing) > len(checks) * 0.5


def test_consistency_checks_fail():
    """Test that bad data fails consistency checks."""
    result = {
        "pipes": [
            {
                "discipline": "storm",
                "material": "UNKNOWN_MAT",
                "dia_in": 200,  # Very large
                "length_ft": 2.0,  # Very short
                "invert_in": 425.0,  # Flows uphill
                "invert_out": 420.0,
                "ground_level": 410.0  # Negative depth
            }
        ]
    }
    
    checks = check_consistency(result)
    
    # Should have warnings/failures
    warnings = [c for c in checks if c[1] < 1.0]
    assert len(warnings) > 0


def test_quality_assessment():
    """Test quality scoring."""
    result = {
        "pipes": [
            {
                "discipline": "storm",
                "material": "PVC",
                "dia_in": 12,
                "length_ft": 100.0,
                "invert_in": 420.0,
                "invert_out": 419.0,
                "ground_level": 425.0
            },
            {
                "discipline": "sanitary",
                "material": "DI",
                "dia_in": 8,
                "length_ft": 50.0
                # Missing elevations
            }
        ]
    }
    
    pdf_text = "PVC 12 inch storm pipe DI 8 inch sanitary 420.0 419.0 425.0"
    
    scores = assess_extraction_quality(result, pdf_text)
    
    # Should have all quality metrics
    assert "completeness" in scores
    assert "elevation_coverage" in scores
    assert "faithfulness" in scores
    assert "material_coverage" in scores
    assert "diameter_coverage" in scores
    
    # Completeness should be 100% (both pipes have material, dia, length, discipline)
    assert scores["completeness"] == 1.0
    
    # Elevation coverage should be 50% (1 of 2 pipes has elevations)
    assert 0.4 <= scores["elevation_coverage"] <= 0.6
    
    # Material coverage should be 100%
    assert scores["material_coverage"] == 1.0


def test_overall_confidence():
    """Test overall confidence calculation."""
    quality_scores = {
        "completeness": 0.8,
        "elevation_coverage": 0.6,
        "faithfulness": 0.9,
        "material_coverage": 1.0,
        "diameter_coverage": 1.0
    }
    
    consistency_checks = [
        ("check1", 1.0, "OK"),
        ("check2", 1.0, "OK"),
        ("check3", 0.5, "Warning"),
        ("check4", 1.0, "OK")
    ]
    
    confidence = calculate_overall_confidence(quality_scores, consistency_checks)
    
    # Should be high (>0.7) but not perfect due to warning
    assert 0.7 <= confidence <= 0.95


def test_evaluate_production_run():
    """Test full production evaluation."""
    result = {
        "pipes": [
            {
                "discipline": "storm",
                "material": "PVC",
                "dia_in": 12,
                "length_ft": 100.0,
                "invert_in": 420.0,
                "invert_out": 419.0,
                "ground_level": 425.0
            }
        ]
    }
    
    pdf_text = "PVC 12 inch storm pipe 420.0 419.0 425.0"
    
    evaluation = evaluate_production_run(result, pdf_text, confidence_threshold=0.70)
    
    # Should have all components
    assert "confidence" in evaluation
    assert "quality_scores" in evaluation
    assert "consistency_checks" in evaluation
    assert "needs_hitl_review" in evaluation
    assert "flags" in evaluation
    assert "recommendation" in evaluation
    
    # Confidence should be high for good data
    assert evaluation["confidence"] > 0.7
    
    # Should not need HITL review
    assert evaluation["needs_hitl_review"] is False


def test_evaluate_low_confidence():
    """Test that low quality data triggers HITL review."""
    result = {
        "pipes": [
            {
                "discipline": "unknown",
                # Missing most attributes
                "length_ft": 10.0
            }
        ]
    }
    
    pdf_text = ""
    
    evaluation = evaluate_production_run(result, pdf_text, confidence_threshold=0.70)
    
    # Confidence should be low
    assert evaluation["confidence"] < 0.70
    
    # Should need HITL review
    assert evaluation["needs_hitl_review"] is True
    
    # Should have flags
    assert len(evaluation["flags"]) > 0


def test_no_pipes_detected():
    """Test evaluation when no pipes are detected."""
    result = {"pipes": []}
    pdf_text = "Some text"
    
    evaluation = evaluate_production_run(result, pdf_text)
    
    # Should have very low confidence
    assert evaluation["confidence"] == 0.0
    
    # Should need HITL review
    assert evaluation["needs_hitl_review"] is True
    
    # Should have a flag
    assert len(evaluation["flags"]) > 0
    assert any("No pipes" in str(f) for f in evaluation["flags"])


@pytest.mark.benchmark
def test_production_metric_integration():
    """Test that ProductionQualityMetric works in the registry."""
    from backend.app.services.monitoring.metrics_registry import get_metrics_registry
    
    registry = get_metrics_registry()
    
    # Should have production category
    assert "production" in registry.categories
    assert "quality" in registry.categories["production"]
    
    # Test evaluation
    result = {
        "pipes": [
            {
                "discipline": "storm",
                "material": "PVC",
                "dia_in": 12,
                "length_ft": 100.0,
                "invert_in": 420.0,
                "invert_out": 419.0,
                "ground_level": 425.0
            }
        ]
    }
    
    ground_truth = {
        "pdf_text": "PVC 12 inch storm pipe 420.0 419.0 425.0"
    }
    
    scores = registry.evaluate("production", result, ground_truth)
    
    # The metric name is "quality" not "production_quality"
    assert "quality" in scores
    assert 0.0 <= scores["quality"] <= 1.0
    assert scores["quality"] > 0.7  # Should be high for good data

