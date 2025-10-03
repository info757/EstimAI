"""Tests for scale inference and coordinate transformation utilities."""
import pytest
import math
from unittest.mock import Mock, patch

from backend.app.services.ingest.scale import (
    ScaleInfo, infer_scale_text, infer_scale_bar, compute_user_to_world,
    parse_scale_string, to_world, len_world, create_scale_info
)


class TestScaleInference:
    """Test scale inference functions."""
    
    def test_parse_scale_string_inch_feet(self):
        """Test parsing inch-feet scale strings."""
        # Test various formats
        assert parse_scale_string('1" = 50\'') == 50.0
        assert parse_scale_string('1" = 50') == 50.0
        assert parse_scale_string('1 inch = 50 feet') == 50.0
        assert parse_scale_string('1 in = 50 ft') == 50.0
        assert parse_scale_string('2" = 100\'') == 50.0
        assert parse_scale_string('1" = 25\'') == 25.0
    
    def test_parse_scale_string_ratio(self):
        """Test parsing ratio scale strings."""
        assert parse_scale_string('1:1000') == 1000.0
        assert parse_scale_string('1:500') == 500.0
        assert parse_scale_string('2:1000') == 500.0
    
    def test_parse_scale_string_invalid(self):
        """Test parsing invalid scale strings."""
        assert parse_scale_string('invalid scale') is None
        assert parse_scale_string('') is None
        assert parse_scale_string('1 inch = feet') is None
    
    def test_parse_scale_string_decimal(self):
        """Test parsing decimal scale values."""
        assert parse_scale_string('1" = 50.5\'') == 50.5
        assert parse_scale_string('1.5" = 75\'') == 50.0
        assert parse_scale_string('1:1000.5') == 1000.5
    
    @patch('app.services.ingest.scale.Page')
    def test_infer_scale_text(self, mock_page_class):
        """Test scale inference from text."""
        mock_page = Mock()
        mock_page.GetText.return_value = "SCALE 1\" = 50'"
        
        result = infer_scale_text(mock_page)
        assert result == "1\" = 50'"
    
    @patch('app.services.ingest.scale.Page')
    def test_infer_scale_text_no_scale(self, mock_page_class):
        """Test scale inference when no scale found."""
        mock_page = Mock()
        mock_page.GetText.return_value = "Some random text without scale"
        
        result = infer_scale_text(mock_page)
        assert result is None
    
    @patch('app.services.ingest.scale.Page')
    def test_infer_scale_text_multiple_patterns(self, mock_page_class):
        """Test scale inference with multiple patterns."""
        mock_page = Mock()
        mock_page.GetText.return_value = "Drawing title\nSCALE 1\" = 100'\nSome notes"
        
        result = infer_scale_text(mock_page)
        assert result == "1\" = 100'"
    
    @patch('app.services.ingest.scale.Page')
    def test_infer_scale_bar(self, mock_page_class):
        """Test scale bar inference."""
        mock_page = Mock()
        
        result = infer_scale_bar(mock_page)
        # Currently returns None as implementation is simplified
        assert result is None
    
    @patch('app.services.ingest.scale.Page')
    def test_compute_user_to_world(self, mock_page_class):
        """Test user-to-world matrix computation."""
        mock_page = Mock()
        mock_page.GetPageWidth.return_value = 612.0  # 8.5" at 72 DPI
        mock_page.GetPageHeight.return_value = 792.0  # 11" at 72 DPI
        
        # Test with scale
        matrix = compute_user_to_world(mock_page, '1" = 50\'')
        assert matrix[0][0] == 50.0  # x scale
        assert matrix[1][1] == 50.0  # y scale
        assert matrix[0][2] == 0.0  # x translation
        assert matrix[1][2] == 0.0  # y translation
    
    @patch('app.services.ingest.scale.Page')
    def test_compute_user_to_world_no_scale(self, mock_page_class):
        """Test user-to-world matrix without scale."""
        mock_page = Mock()
        mock_page.GetPageWidth.return_value = 612.0
        mock_page.GetPageHeight.return_value = 792.0
        
        # Test without scale
        matrix = compute_user_to_world(mock_page, None)
        assert matrix[0][0] == 1.0  # identity matrix
        assert matrix[1][1] == 1.0
        assert matrix[0][2] == 0.0
        assert matrix[1][2] == 0.0


class TestCoordinateTransformation:
    """Test coordinate transformation functions."""
    
    def test_to_world_identity(self):
        """Test coordinate transformation with identity matrix."""
        matrix = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ]
        
        pt_user = (100.0, 200.0)
        pt_world = to_world(pt_user, matrix)
        assert pt_world == (100.0, 200.0)
    
    def test_to_world_scaled(self):
        """Test coordinate transformation with scale."""
        matrix = [
            [50.0, 0.0, 0.0],  # 50x scale
            [0.0, 50.0, 0.0],
            [0.0, 0.0, 1.0]
        ]
        
        pt_user = (1.0, 2.0)
        pt_world = to_world(pt_user, matrix)
        assert pt_world == (50.0, 100.0)
    
    def test_to_world_translated(self):
        """Test coordinate transformation with translation."""
        matrix = [
            [1.0, 0.0, 10.0],  # 10 unit x translation
            [0.0, 1.0, 20.0],   # 20 unit y translation
            [0.0, 0.0, 1.0]
        ]
        
        pt_user = (5.0, 10.0)
        pt_world = to_world(pt_user, matrix)
        assert pt_world == (15.0, 30.0)
    
    def test_len_world_single_segment(self):
        """Test world length calculation for single segment."""
        matrix = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ]
        
        polyline = [(0.0, 0.0), (3.0, 4.0)]  # 3-4-5 triangle
        length = len_world(polyline, matrix)
        assert abs(length - 5.0) < 0.001
    
    def test_len_world_multiple_segments(self):
        """Test world length calculation for multiple segments."""
        matrix = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ]
        
        polyline = [(0.0, 0.0), (3.0, 0.0), (3.0, 4.0)]  # L-shape
        length = len_world(polyline, matrix)
        assert abs(length - 7.0) < 0.001  # 3 + 4
    
    def test_len_world_scaled(self):
        """Test world length calculation with scale."""
        matrix = [
            [2.0, 0.0, 0.0],  # 2x scale
            [0.0, 2.0, 0.0],
            [0.0, 0.0, 1.0]
        ]
        
        polyline = [(0.0, 0.0), (3.0, 4.0)]  # 3-4-5 triangle
        length = len_world(polyline, matrix)
        assert abs(length - 10.0) < 0.001  # 5 * 2
    
    def test_len_world_empty(self):
        """Test world length calculation for empty polyline."""
        matrix = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ]
        
        polyline = []
        length = len_world(polyline, matrix)
        assert length == 0.0
        
        polyline = [(1.0, 1.0)]  # Single point
        length = len_world(polyline, matrix)
        assert length == 0.0


class TestScaleInfo:
    """Test ScaleInfo dataclass and creation."""
    
    def test_scale_info_creation(self):
        """Test ScaleInfo creation."""
        scale_info = ScaleInfo(
            scale_str="1\" = 50'",
            units="feet",
            user_to_world=[[50.0, 0.0, 0.0], [0.0, 50.0, 0.0], [0.0, 0.0, 1.0]]
        )
        
        assert scale_info.scale_str == "1\" = 50'"
        assert scale_info.units == "feet"
        assert scale_info.user_to_world[0][0] == 50.0
    
    @patch('app.services.ingest.scale.infer_scale_text')
    @patch('app.services.ingest.scale.infer_scale_bar')
    @patch('app.services.ingest.scale.compute_user_to_world')
    @patch('app.services.ingest.scale.Page')
    def test_create_scale_info(self, mock_page_class, mock_compute, mock_infer_bar, mock_infer_text):
        """Test create_scale_info function."""
        mock_page = Mock()
        mock_infer_text.return_value = "1\" = 50'"
        mock_infer_bar.return_value = None
        mock_compute.return_value = [[50.0, 0.0, 0.0], [0.0, 50.0, 0.0], [0.0, 0.0, 1.0]]
        
        scale_info = create_scale_info(mock_page)
        
        assert scale_info.scale_str == "1\" = 50'"
        assert scale_info.units == "feet"
        assert scale_info.user_to_world[0][0] == 50.0
    
    @patch('app.services.ingest.scale.infer_scale_text')
    @patch('app.services.ingest.scale.infer_scale_bar')
    @patch('app.services.ingest.scale.compute_user_to_world')
    @patch('app.services.ingest.scale.Page')
    def test_create_scale_info_meters(self, mock_page_class, mock_compute, mock_infer_bar, mock_infer_text):
        """Test create_scale_info with meters."""
        mock_page = Mock()
        mock_infer_text.return_value = "1 inch = 25 meters"
        mock_infer_bar.return_value = None
        mock_compute.return_value = [[25.0, 0.0, 0.0], [0.0, 25.0, 0.0], [0.0, 0.0, 1.0]]
        
        scale_info = create_scale_info(mock_page)
        
        assert scale_info.scale_str == "1 inch = 25 meters"
        assert scale_info.units == "meters"
        assert scale_info.user_to_world[0][0] == 25.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
