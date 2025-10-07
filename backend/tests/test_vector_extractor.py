"""Tests for Apryse vector extractor."""
import pytest
import os
from pathlib import Path

from backend.app.services.extract.apryse_vectors import (
    VectorExtractor,
    ApryseUnavailable,
    create_extractor,
    extract_all,
)


def test_apryse_unavailable_when_disabled():
    """Test that ApryseUnavailable is raised when APR_USE_APRYSE=0."""
    # This test should pass even without Apryse
    if os.getenv("APR_USE_APRYSE") != "1":
        with pytest.raises(ApryseUnavailable):
            VectorExtractor("test.pdf")


@pytest.mark.skipif(
    os.getenv("APR_USE_APRYSE") != "1",
    reason="Requires APR_USE_APRYSE=1"
)
def test_vector_extractor_init():
    """Test VectorExtractor initialization with a real PDF."""
    pdf_path = Path("samples/bid_test.pdf")
    
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found: {pdf_path}")
    
    extractor = VectorExtractor(str(pdf_path))
    assert extractor.pdf_path == pdf_path
    assert extractor._doc is None  # Lazy load
    extractor.close()


@pytest.mark.skipif(
    os.getenv("APR_USE_APRYSE") != "1",
    reason="Requires APR_USE_APRYSE=1"
)
def test_load_scale():
    """Test scale loading from PDF."""
    pdf_path = Path("samples/bid_test.pdf")
    
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found: {pdf_path}")
    
    extractor = VectorExtractor(str(pdf_path))
    scale = extractor.load_scale(page_num=0)
    
    # Should have positive conversion factors
    assert scale.points_per_foot > 0
    assert scale.inches_per_foot > 0
    assert scale.scale_text is not None
    assert scale.source in ["scale_bar", "viewport", "assumed"]
    
    # Cached on second call
    scale2 = extractor.load_scale(page_num=0)
    assert scale is scale2
    
    extractor.close()


@pytest.mark.skipif(
    os.getenv("APR_USE_APRYSE") != "1",
    reason="Requires APR_USE_APRYSE=1"
)
def test_extract_all_convenience():
    """Test the extract_all convenience function."""
    pdf_path = Path("samples/bid_test.pdf")
    
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found: {pdf_path}")
    
    data = extract_all(str(pdf_path), page_num=0)
    
    assert "scale" in data
    assert "lines" in data
    assert "texts" in data
    assert "page_num" in data
    assert "pdf_file" in data
    
    # Verify data structure
    assert isinstance(data["lines"], list)
    assert isinstance(data["texts"], list)
    assert data["scale"]["points_per_foot"] > 0


@pytest.mark.skipif(
    os.getenv("APR_USE_APRYSE") != "1",
    reason="Requires APR_USE_APRYSE=1"
)
def test_extract_layer_lines():
    """Test extracting lines from specific layers."""
    pdf_path = Path("samples/bid_test.pdf")
    
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found: {pdf_path}")
    
    extractor = VectorExtractor(str(pdf_path))
    
    # Extract all lines (no layer filter)
    all_lines = extractor.extract_layer_lines([], page_num=0)
    assert isinstance(all_lines, list)
    
    # Each line should have required fields
    if all_lines:
        line = all_lines[0]
        assert line.id is not None
        assert line.points is not None
        assert line.length_ft >= 0
        assert line.bbox is not None
        assert len(line.bbox) == 4
    
    extractor.close()


@pytest.mark.skipif(
    os.getenv("APR_USE_APRYSE") != "1",
    reason="Requires APR_USE_APRYSE=1"
)
def test_extract_text_annotations():
    """Test extracting text annotations."""
    pdf_path = Path("samples/bid_test.pdf")
    
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found: {pdf_path}")
    
    extractor = VectorExtractor(str(pdf_path))
    texts = extractor.extract_text_annotations(page_num=0)
    
    assert isinstance(texts, list)
    
    # Each text should have required fields
    if texts:
        text = texts[0]
        assert text.text is not None
        assert text.x is not None
        assert text.y is not None
        assert text.bbox is not None
        assert len(text.bbox) == 4
    
    extractor.close()


def test_factory_function():
    """Test create_extractor factory function."""
    pdf_path = Path("samples/bid_test.pdf")
    
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found: {pdf_path}")
    
    if os.getenv("APR_USE_APRYSE") != "1":
        with pytest.raises(ApryseUnavailable):
            create_extractor(str(pdf_path))
    else:
        extractor = create_extractor(str(pdf_path))
        assert isinstance(extractor, VectorExtractor)
        extractor.close()

