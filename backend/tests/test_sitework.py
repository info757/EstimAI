"""Tests for sitework measurement functions."""
import pytest
from unittest.mock import Mock

from app.services.detectors.sitework import (
    measure_curb_lf, measure_sidewalk_sf, measure_silt_fence_lf,
    count_inlet_protections, measure_pavement_sf, measure_landscaping_sf,
    _get_curb_symbols, _get_sidewalk_symbols, _get_silt_fence_symbols,
    _is_curb, _is_sidewalk, _is_silt_fence, _calculate_vector_length,
    _get_sidewalk_width, _calculate_polygon_area
)
from app.services.ingest.extract import VectorEl, TextEl
from app.domain.networks import Node, NodeType


class TestSiteworkMeasurements:
    """Test sitework measurement functions."""
    
    def test_measure_curb_lf(self):
        """Test measuring curb length."""
        # Create test vectors
        vectors = [
            VectorEl("line", [(0.0, 0.0), (100.0, 0.0)], (0, 0, 0, 255), (0, 0, 0, 0), 1.0, [], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]),
            VectorEl("line", [(100.0, 0.0), (200.0, 0.0)], (0, 0, 0, 255), (0, 0, 0, 0), 1.0, [], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        ]
        
        symbol_map = {
            "symbols": {
                "Curb": {
                    "layer_hint": ["CURB"],
                    "vector": {"stroke_min": 0.5, "stroke_max": 2.0}
                }
            }
        }
        
        length = measure_curb_lf(vectors, symbol_map)
        assert length == 200.0  # 100 + 100
    
    def test_measure_sidewalk_sf(self):
        """Test measuring sidewalk area."""
        # Create test vectors
        vectors = [
            VectorEl("line", [(0.0, 0.0), (100.0, 0.0)], (0, 0, 0, 255), (0, 0, 0, 0), 1.0, [], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        ]
        
        symbol_map = {
            "symbols": {
                "Sidewalk": {
                    "layer_hint": ["SIDEWALK"],
                    "vector": {"stroke_min": 0.5, "stroke_max": 2.0}
                }
            }
        }
        
        # Test with default width
        area = measure_sidewalk_sf(vectors, symbol_map, default_width_ft=5.0)
        assert area == 500.0  # 100 * 5.0
        
        # Test without default width
        area = measure_sidewalk_sf(vectors, symbol_map)
        assert area == 500.0  # 100 * 5.0 (default)
    
    def test_measure_silt_fence_lf(self):
        """Test measuring silt fence length."""
        # Create test vectors
        vectors = [
            VectorEl("line", [(0.0, 0.0), (50.0, 0.0)], (0, 0, 0, 255), (0, 0, 0, 0), 1.0, [], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]),
            VectorEl("line", [(50.0, 0.0), (100.0, 0.0)], (0, 0, 0, 255), (0, 0, 0, 0), 1.0, [], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        ]
        
        symbol_map = {
            "symbols": {
                "Silt Fence": {
                    "layer_hint": ["SILT_FENCE"],
                    "vector": {"stroke_min": 0.5, "stroke_max": 2.0}
                }
            }
        }
        
        length = measure_silt_fence_lf(vectors, symbol_map)
        assert length == 100.0  # 50 + 50
    
    def test_count_inlet_protections(self):
        """Test counting inlet protection devices."""
        # Create test nodes
        nodes = [
            Node(id="node-1", node_type=NodeType.INLET, x_ft=0.0, y_ft=0.0),
            Node(id="node-2", node_type=NodeType.INLET, x_ft=100.0, y_ft=0.0)
        ]
        
        # Create test texts
        texts = [
            TextEl("INLET PROTECTION", (0.0, 0.0, 50.0, 20.0), []),
            TextEl("SILT SOCK", (100.0, 0.0, 150.0, 20.0), []),
            TextEl("Some other text", (200.0, 0.0, 250.0, 20.0), [])
        ]
        
        count = count_inlet_protections(nodes, texts)
        assert count == 2  # Two protection devices found
    
    def test_measure_pavement_sf(self):
        """Test measuring pavement area."""
        # Create test vectors
        vectors = [
            VectorEl("polygon", [(0.0, 0.0), (100.0, 0.0), (100.0, 50.0), (0.0, 50.0), (0.0, 0.0)], (0, 0, 0, 255), (0, 0, 0, 0), 1.0, [], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        ]
        
        symbol_map = {
            "symbols": {
                "Pavement": {
                    "layer_hint": ["PAVEMENT"],
                    "vector": {"stroke_min": 0.5, "stroke_max": 2.0}
                }
            }
        }
        
        area = measure_pavement_sf(vectors, symbol_map)
        assert area == 5000.0  # 100 * 50
    
    def test_measure_landscaping_sf(self):
        """Test measuring landscaping area."""
        # Create test vectors
        vectors = [
            VectorEl("polygon", [(0.0, 0.0), (50.0, 0.0), (50.0, 25.0), (0.0, 25.0), (0.0, 0.0)], (0, 0, 0, 255), (0, 0, 0, 0), 1.0, [], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        ]
        
        symbol_map = {
            "symbols": {
                "Landscaping": {
                    "layer_hint": ["LANDSCAPING"],
                    "vector": {"stroke_min": 0.5, "stroke_max": 2.0}
                }
            }
        }
        
        area = measure_landscaping_sf(vectors, symbol_map)
        assert area == 1250.0  # 50 * 25


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_get_curb_symbols(self):
        """Test getting curb symbols."""
        symbol_map = {
            "symbols": {
                "Curb": {
                    "layer_hint": ["CURB"],
                    "vector": {"stroke_min": 0.5, "stroke_max": 2.0}
                },
                "Sidewalk": {
                    "layer_hint": ["SIDEWALK"],
                    "vector": {"stroke_min": 0.5, "stroke_max": 2.0}
                }
            }
        }
        
        curb_symbols = _get_curb_symbols(symbol_map)
        assert "Curb" in curb_symbols
        assert "Sidewalk" not in curb_symbols
    
    def test_get_sidewalk_symbols(self):
        """Test getting sidewalk symbols."""
        symbol_map = {
            "symbols": {
                "Curb": {
                    "layer_hint": ["CURB"],
                    "vector": {"stroke_min": 0.5, "stroke_max": 2.0}
                },
                "Sidewalk": {
                    "layer_hint": ["SIDEWALK"],
                    "vector": {"stroke_min": 0.5, "stroke_max": 2.0}
                }
            }
        }
        
        sidewalk_symbols = _get_sidewalk_symbols(symbol_map)
        assert "Sidewalk" in sidewalk_symbols
        assert "Curb" not in sidewalk_symbols
    
    def test_get_silt_fence_symbols(self):
        """Test getting silt fence symbols."""
        symbol_map = {
            "symbols": {
                "Silt Fence": {
                    "layer_hint": ["SILT_FENCE"],
                    "vector": {"stroke_min": 0.5, "stroke_max": 2.0}
                },
                "Curb": {
                    "layer_hint": ["CURB"],
                    "vector": {"stroke_min": 0.5, "stroke_max": 2.0}
                }
            }
        }
        
        silt_fence_symbols = _get_silt_fence_symbols(symbol_map)
        assert "Silt Fence" in silt_fence_symbols
        assert "Curb" not in silt_fence_symbols
    
    def test_is_curb(self):
        """Test checking if vector is curb."""
        vector = VectorEl("line", [(0.0, 0.0), (100.0, 0.0)], (0, 0, 0, 255), (0, 0, 0, 0), 1.0, [], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        
        curb_symbols = {
            "Curb": {
                "layer_hint": ["CURB"],
                "vector": {"stroke_min": 0.5, "stroke_max": 2.0}
            }
        }
        
        assert _is_curb(vector, curb_symbols) == True
        
        # Test with empty symbols
        assert _is_curb(vector, {}) == True  # Should match line pattern
    
    def test_is_sidewalk(self):
        """Test checking if vector is sidewalk."""
        vector = VectorEl("line", [(0.0, 0.0), (100.0, 0.0)], (0, 0, 0, 255), (0, 0, 0, 0), 1.0, [], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        
        sidewalk_symbols = {
            "Sidewalk": {
                "layer_hint": ["SIDEWALK"],
                "vector": {"stroke_min": 0.5, "stroke_max": 2.0}
            }
        }
        
        assert _is_sidewalk(vector, sidewalk_symbols) == True
        
        # Test with empty symbols
        assert _is_sidewalk(vector, {}) == True  # Should match line pattern
    
    def test_is_silt_fence(self):
        """Test checking if vector is silt fence."""
        vector = VectorEl("line", [(0.0, 0.0), (100.0, 0.0)], (0, 0, 0, 255), (0, 0, 0, 0), 1.0, [], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        
        silt_fence_symbols = {
            "Silt Fence": {
                "layer_hint": ["SILT_FENCE"],
                "vector": {"stroke_min": 0.5, "stroke_max": 2.0}
            }
        }
        
        assert _is_silt_fence(vector, silt_fence_symbols) == True
        
        # Test with empty symbols
        assert _is_silt_fence(vector, {}) == True  # Should match line pattern
    
    def test_calculate_vector_length(self):
        """Test calculating vector length."""
        vector = VectorEl("line", [(0.0, 0.0), (3.0, 4.0)], (0, 0, 0, 255), (0, 0, 0, 0), 1.0, [], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        
        length = _calculate_vector_length(vector)
        assert length == 5.0  # 3-4-5 triangle
        
        # Test with single point
        vector_single = VectorEl("line", [(0.0, 0.0)], (0, 0, 0, 255), (0, 0, 0, 0), 1.0, [], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        length_single = _calculate_vector_length(vector_single)
        assert length_single == 0.0
    
    def test_get_sidewalk_width(self):
        """Test getting sidewalk width."""
        vector = VectorEl("line", [(0.0, 0.0), (100.0, 0.0)], (0, 0, 0, 255), (0, 0, 0, 0), 1.0, [], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        
        # Test with default width
        width = _get_sidewalk_width(vector, default_width_ft=6.0)
        assert width == 6.0
        
        # Test without default width
        width = _get_sidewalk_width(vector)
        assert width == 5.0  # Default value
    
    def test_calculate_polygon_area(self):
        """Test calculating polygon area."""
        # Test rectangle
        points = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0), (0.0, 0.0)]
        area = _calculate_polygon_area(points)
        assert area == 50.0  # 10 * 5
        
        # Test triangle
        points_triangle = [(0.0, 0.0), (10.0, 0.0), (5.0, 10.0), (0.0, 0.0)]
        area_triangle = _calculate_polygon_area(points_triangle)
        assert area_triangle == 50.0  # 0.5 * 10 * 10
        
        # Test with insufficient points
        points_insufficient = [(0.0, 0.0), (10.0, 0.0)]
        area_insufficient = _calculate_polygon_area(points_insufficient)
        assert area_insufficient == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
