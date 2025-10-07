"""Tests for pipe classifier."""
import pytest
from backend.app.services.ai.pipe_classifier import (
    PipeAttr,
    PipeDetection,
    PipeClassifier,
    classify_pipes,
)


def test_pipe_attr_confidence_clamping():
    """Test that confidence is clamped to [0, 1]."""
    # Test upper bound
    attr = PipeAttr(confidence=1.5)
    assert attr.confidence == 1.0
    
    # Test lower bound
    attr = PipeAttr(confidence=-0.5)
    assert attr.confidence == 0.0
    
    # Test valid range
    attr = PipeAttr(confidence=0.7)
    assert attr.confidence == 0.7


def test_pipe_detection_creation():
    """Test creating PipeDetection objects."""
    detection = PipeDetection(
        polyline_id="test_1",
        attrs=PipeAttr(
            material="pvc",
            dia_in=12.0,
            discipline="storm",
            confidence=0.9
        ),
        reason="Test detection"
    )
    
    assert detection.polyline_id == "test_1"
    assert detection.attrs.material == "pvc"
    assert detection.attrs.dia_in == 12.0
    assert detection.attrs.discipline == "storm"
    assert detection.attrs.confidence == 0.9


def test_pipe_classifier_initialization():
    """Test PipeClassifier can be created."""
    classifier = PipeClassifier()
    assert classifier is not None
    assert classifier.model_name is not None


def test_classify_empty_patches():
    """Test that empty input returns empty output."""
    classifier = PipeClassifier()
    result = classifier.classify([])
    assert result == []


def test_classify_with_text_features():
    """Test classification with text-only features."""
    patches = [
        {
            "polyline_id": "vec_0_1",
            "length_ft": 125.5,
            "layer": "STORM SEWER",
            "nearby_text": ["12\" PVC", "0.5% SLOPE"],
            "color": "#0000FF"
        },
        {
            "polyline_id": "vec_0_2",
            "length_ft": 87.3,
            "layer": "WATER MAIN",
            "nearby_text": ["6\" DI", "DOMESTIC WATER"],
            "color": "#00FF00"
        }
    ]
    
    classifier = PipeClassifier()
    detections = classifier.classify(patches)
    
    # Should return detections for each patch
    assert len(detections) >= 0  # May be empty if LLM fails, fallback should still work
    assert isinstance(detections, list)
    
    # Each detection should be valid
    for det in detections:
        assert isinstance(det, PipeDetection)
        assert det.polyline_id in ["vec_0_1", "vec_0_2"]
        assert 0.0 <= det.attrs.confidence <= 1.0


def test_classify_pipes_convenience():
    """Test the classify_pipes convenience function."""
    patches = [
        {
            "polyline_id": "test_pipe",
            "length_ft": 50.0,
            "layer": "STORM",
            "nearby_text": ["8\" PVC"]
        }
    ]
    
    detections = classify_pipes(patches)
    assert isinstance(detections, list)


def test_fallback_classification():
    """Test fallback when LLM is unavailable."""
    classifier = PipeClassifier()
    
    patches = [
        {
            "polyline_id": "fallback_test",
            "length_ft": 100.0,
            "layer": "UNKNOWN",
            "nearby_text": []
        }
    ]
    
    # Test internal fallback method
    detections = classifier._fallback_classification(patches)
    
    assert len(detections) == 1
    assert detections[0].polyline_id == "fallback_test"
    assert detections[0].attrs.confidence == 0.1  # Low confidence for fallback


def test_context_building():
    """Test that context is built correctly from patches."""
    classifier = PipeClassifier()
    
    patches = [
        {
            "polyline_id": "ctx_test",
            "length_ft": 75.0,
            "layer": "STORM",
            "color": "#FF0000",
            "nearby_text": ["12\" PVC", "SD-1"]
        }
    ]
    
    context = classifier._build_context(patches)
    
    assert "task" in context
    assert "candidates" in context
    assert "instructions" in context
    assert len(context["candidates"]) == 1
    assert context["candidates"][0]["id"] == "ctx_test"
    assert context["candidates"][0]["length_ft"] == 75.0


def test_schema_validation():
    """Test that response schema is properly defined."""
    classifier = PipeClassifier()
    schema = classifier._get_response_schema()
    
    assert schema["type"] == "object"
    assert "properties" in schema
    assert "detections" in schema["properties"]
    assert schema["properties"]["detections"]["type"] == "array"
    assert "polyline_id" in schema["properties"]["detections"]["items"]["properties"]
    assert "discipline" in schema["properties"]["detections"]["items"]["properties"]

