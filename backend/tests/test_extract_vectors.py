"""Tests for vector and text extraction utilities."""
import pytest
from unittest.mock import Mock, patch

from backend.app.services.ingest.extract import (
    VectorEl, TextEl, extract_vectors, extract_text,
    _extract_vector_from_element, _extract_path_element,
    _extract_rect_element, _extract_circle_element,
    _extract_ellipse_element
)


class TestVectorEl:
    """Test VectorEl dataclass."""
    
    def test_vector_el_creation(self):
        """Test VectorEl creation."""
        vector = VectorEl(
            kind="line",
            points=[(0.0, 0.0), (10.0, 10.0)],
            stroke_rgba=(255, 0, 0, 255),
            fill_rgba=(0, 0, 0, 0),
            stroke_w=2.0,
            ocg_names=["layer1"],
            xform=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        )
        
        assert vector.kind == "line"
        assert vector.points == [(0.0, 0.0), (10.0, 10.0)]
        assert vector.stroke_rgba == (255, 0, 0, 255)
        assert vector.fill_rgba == (0, 0, 0, 0)
        assert vector.stroke_w == 2.0
        assert vector.ocg_names == ["layer1"]


class TestTextEl:
    """Test TextEl dataclass."""
    
    def test_text_el_creation(self):
        """Test TextEl creation."""
        text = TextEl(
            text="Sample text",
            bbox=(10.0, 20.0, 100.0, 30.0),
            ocg_names=["text_layer"]
        )
        
        assert text.text == "Sample text"
        assert text.bbox == (10.0, 20.0, 100.0, 30.0)
        assert text.ocg_names == ["text_layer"]


class TestVectorExtraction:
    """Test vector extraction functions."""
    
    @patch('app.services.ingest.extract.Page')
    def test_extract_vectors_empty_page(self, mock_page_class):
        """Test vector extraction from empty page."""
        mock_page = Mock()
        mock_page.GetFirstElement.return_value = None
        
        vectors = extract_vectors(mock_page)
        assert vectors == []
    
    @patch('app.services.ingest.extract.Page')
    def test_extract_vectors_with_elements(self, mock_page_class):
        """Test vector extraction with elements."""
        # Mock page with elements
        mock_element1 = Mock()
        mock_element1.GetType.return_value = "Path"
        mock_element1.GetNext.return_value = None
        
        mock_page = Mock()
        mock_page.GetFirstElement.return_value = mock_element1
        
        # Mock the extraction function
        with patch('app.services.ingest.extract._extract_vector_from_element') as mock_extract:
            mock_vector = VectorEl(
                kind="line",
                points=[(0.0, 0.0), (10.0, 10.0)],
                stroke_rgba=(0, 0, 0, 255),
                fill_rgba=(0, 0, 0, 0),
                stroke_w=1.0,
                ocg_names=[],
                xform=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
            )
            mock_extract.return_value = mock_vector
            
            vectors = extract_vectors(mock_page)
            assert len(vectors) == 1
            assert vectors[0].kind == "line"
    
    def test_extract_vector_from_element_path(self):
        """Test extracting vector from path element."""
        mock_element = Mock()
        mock_element.GetType.return_value = "Path"
        mock_element.GetPathData.return_value = "M 0 0 L 10 10"
        
        with patch('app.services.ingest.extract._extract_path_element') as mock_extract_path:
            mock_vector = VectorEl(
                kind="line",
                points=[(0.0, 0.0), (10.0, 10.0)],
                stroke_rgba=(0, 0, 0, 255),
                fill_rgba=(0, 0, 0, 0),
                stroke_w=1.0,
                ocg_names=[],
                xform=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
            )
            mock_extract_path.return_value = mock_vector
            
            result = _extract_vector_from_element(mock_element)
            assert result == mock_vector
    
    def test_extract_vector_from_element_rect(self):
        """Test extracting vector from rectangle element."""
        mock_element = Mock()
        mock_element.GetType.return_value = "Rect"
        mock_element.GetBBox.return_value = (0.0, 0.0, 10.0, 10.0)
        
        with patch('app.services.ingest.extract._extract_rect_element') as mock_extract_rect:
            mock_vector = VectorEl(
                kind="rect",
                points=[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)],
                stroke_rgba=(0, 0, 0, 255),
                fill_rgba=(0, 0, 0, 0),
                stroke_w=1.0,
                ocg_names=[],
                xform=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
            )
            mock_extract_rect.return_value = mock_vector
            
            result = _extract_vector_from_element(mock_element)
            assert result == mock_vector
    
    def test_extract_vector_from_element_circle(self):
        """Test extracting vector from circle element."""
        mock_element = Mock()
        mock_element.GetType.return_value = "Circle"
        mock_element.GetCenter.return_value = (5.0, 5.0)
        mock_element.GetRadius.return_value = 5.0
        
        with patch('app.services.ingest.extract._extract_circle_element') as mock_extract_circle:
            mock_vector = VectorEl(
                kind="circle",
                points=[(10.0, 5.0), (5.0, 10.0), (0.0, 5.0), (5.0, 0.0), (10.0, 5.0)],
                stroke_rgba=(0, 0, 0, 255),
                fill_rgba=(0, 0, 0, 0),
                stroke_w=1.0,
                ocg_names=[],
                xform=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
            )
            mock_extract_circle.return_value = mock_vector
            
            result = _extract_vector_from_element(mock_element)
            assert result == mock_vector
    
    def test_extract_vector_from_element_ellipse(self):
        """Test extracting vector from ellipse element."""
        mock_element = Mock()
        mock_element.GetType.return_value = "Ellipse"
        mock_element.GetBBox.return_value = (0.0, 0.0, 10.0, 5.0)
        
        with patch('app.services.ingest.extract._extract_ellipse_element') as mock_extract_ellipse:
            mock_vector = VectorEl(
                kind="ellipse",
                points=[(5.0, 2.5), (10.0, 2.5), (5.0, 5.0), (0.0, 2.5), (5.0, 2.5)],
                stroke_rgba=(0, 0, 0, 255),
                fill_rgba=(0, 0, 0, 0),
                stroke_w=1.0,
                ocg_names=[],
                xform=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
            )
            mock_extract_ellipse.return_value = mock_vector
            
            result = _extract_vector_from_element(mock_element)
            assert result == mock_vector
    
    def test_extract_vector_from_element_unknown(self):
        """Test extracting vector from unknown element type."""
        mock_element = Mock()
        mock_element.GetType.return_value = "Unknown"
        
        result = _extract_vector_from_element(mock_element)
        assert result is None


class TestTextExtraction:
    """Test text extraction functions."""
    
    @patch('app.services.ingest.extract.Page')
    def test_extract_text_empty_page(self, mock_page_class):
        """Test text extraction from empty page."""
        mock_page = Mock()
        mock_page.GetTextData.return_value = None
        
        text_elements = extract_text(mock_page)
        assert text_elements == []
    
    @patch('app.services.ingest.extract.Page')
    def test_extract_text_with_data(self, mock_page_class):
        """Test text extraction with text data."""
        # Mock text data
        mock_text_item1 = Mock()
        mock_text_item1.GetString.return_value = "Sample text 1"
        mock_text_item1.GetBBox.return_value = (10.0, 20.0, 100.0, 30.0)
        
        mock_text_item2 = Mock()
        mock_text_item2.GetString.return_value = "Sample text 2"
        mock_text_item2.GetBBox.return_value = (10.0, 40.0, 100.0, 50.0)
        
        mock_page = Mock()
        mock_page.GetTextData.return_value = [mock_text_item1, mock_text_item2]
        
        # Mock the OCG names function
        with patch('app.services.ingest.extract._get_text_ocg_names') as mock_get_ocg:
            mock_get_ocg.return_value = []
            
            text_elements = extract_text(mock_page)
            assert len(text_elements) == 2
            assert text_elements[0].text == "Sample text 1"
            assert text_elements[0].bbox == (10.0, 20.0, 100.0, 30.0)
            assert text_elements[1].text == "Sample text 2"
            assert text_elements[1].bbox == (10.0, 40.0, 100.0, 50.0)
    
    @patch('app.services.ingest.extract.Page')
    def test_extract_text_with_ocg_names(self, mock_page_class):
        """Test text extraction with OCG names."""
        mock_text_item = Mock()
        mock_text_item.GetString.return_value = "Text with OCG"
        mock_text_item.GetBBox.return_value = (10.0, 20.0, 100.0, 30.0)
        
        mock_page = Mock()
        mock_page.GetTextData.return_value = [mock_text_item]
        
        with patch('app.services.ingest.extract._get_text_ocg_names') as mock_get_ocg:
            mock_get_ocg.return_value = ["layer1", "layer2"]
            
            text_elements = extract_text(mock_page)
            assert len(text_elements) == 1
            assert text_elements[0].ocg_names == ["layer1", "layer2"]


class TestHelperFunctions:
    """Test helper functions for element processing."""
    
    def test_get_stroke_color_default(self):
        """Test default stroke color."""
        from app.services.ingest.extract import _get_stroke_color
        
        mock_element = Mock()
        color = _get_stroke_color(mock_element)
        assert color == (0, 0, 0, 255)  # Black
    
    def test_get_fill_color_default(self):
        """Test default fill color."""
        from app.services.ingest.extract import _get_fill_color
        
        mock_element = Mock()
        color = _get_fill_color(mock_element)
        assert color == (0, 0, 0, 0)  # Transparent
    
    def test_get_stroke_width_default(self):
        """Test default stroke width."""
        from app.services.ingest.extract import _get_stroke_width
        
        mock_element = Mock()
        width = _get_stroke_width(mock_element)
        assert width == 1.0
    
    def test_get_transformation_matrix_default(self):
        """Test default transformation matrix."""
        from app.services.ingest.extract import _get_transformation_matrix
        
        mock_element = Mock()
        matrix = _get_transformation_matrix(mock_element)
        assert matrix == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    
    def test_get_ocg_names_default(self):
        """Test default OCG names."""
        from app.services.ingest.extract import _get_ocg_names
        
        mock_element = Mock()
        ocg_names = _get_ocg_names(mock_element)
        assert ocg_names == []
    
    def test_get_text_ocg_names_default(self):
        """Test default text OCG names."""
        from app.services.ingest.extract import _get_text_ocg_names
        
        mock_text_item = Mock()
        ocg_names = _get_text_ocg_names(mock_text_item)
        assert ocg_names == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
