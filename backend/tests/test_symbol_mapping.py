"""Tests for symbol mapping functionality."""
import pytest
import json
from unittest.mock import Mock, patch

from backend.app.services.detectors.symbol_map import (
    build_symbol_map_via_llm, get_symbol_by_name, get_symbols_by_layer,
    get_symbols_by_shape, export_symbol_map, import_symbol_map,
    _prepare_snippets_data, _create_system_prompt, _create_user_prompt,
    _create_response_schema, _validate_symbol_map
)
from backend.app.services.detectors.legend import SymbolSnippet, BBox
from backend.app.services.ingest.extract import VectorEl, TextEl


class TestSymbolMapping:
    """Test symbol mapping functionality."""
    
    def test_prepare_snippets_data(self):
        """Test preparing snippets data for LLM."""
        # Create test snippets
        vectors = [
            VectorEl("line", [(0.0, 0.0), (10.0, 10.0)], (0, 0, 0, 255), (0, 0, 0, 0), 1.0, [], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        ]
        texts = [
            TextEl("Sample text", (5.0, 5.0, 15.0, 15.0), [])
        ]
        
        snippet = SymbolSnippet(
            vectors=vectors,
            texts=texts,
            bbox=BBox(0.0, 0.0, 15.0, 15.0),
            stroke_pattern="solid",
            stroke_width_stats={"min": 1.0, "max": 1.0, "mean": 1.0},
            shape_hints=["line"],
            adjacent_text=["Sample text"]
        )
        
        snippets_data = _prepare_snippets_data([snippet])
        
        assert len(snippets_data) == 1
        snippet_data = snippets_data[0]
        assert "vectors" in snippet_data
        assert "texts" in snippet_data
        assert snippet_data["stroke_pattern"] == "solid"
        assert snippet_data["stroke_width_stats"]["min"] == 1.0
        assert snippet_data["shape_hints"] == ["line"]
        assert snippet_data["adjacent_text"] == ["Sample text"]
    
    def test_create_system_prompt(self):
        """Test system prompt creation."""
        prompt = _create_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "construction drawing" in prompt.lower()
        assert "symbol" in prompt.lower()
    
    def test_create_user_prompt(self):
        """Test user prompt creation."""
        snippets_data = [{"test": "data"}]
        notes_text = "Test notes"
        
        prompt = _create_user_prompt(snippets_data, notes_text)
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "Test notes" in prompt
        assert "test" in prompt  # From snippets_data
    
    def test_create_response_schema(self):
        """Test response schema creation."""
        schema = _create_response_schema()
        assert isinstance(schema, dict)
        assert "type" in schema
        assert "properties" in schema
        assert "symbols" in schema["properties"]
    
    def test_validate_symbol_map_valid(self):
        """Test validating a valid symbol map."""
        symbol_map = {
            "symbols": {
                "Test Symbol": {
                    "layer_hint": ["LAYER1"],
                    "vector": {
                        "double_line": False,
                        "stroke_min": 1.0,
                        "stroke_max": 2.0
                    }
                }
            }
        }
        
        validated = _validate_symbol_map(symbol_map)
        assert "symbols" in validated
        assert "Test Symbol" in validated["symbols"]
        assert validated["symbols"]["Test Symbol"]["layer_hint"] == ["LAYER1"]
    
    def test_validate_symbol_map_invalid(self):
        """Test validating an invalid symbol map."""
        # Test with non-dictionary
        result = _validate_symbol_map("invalid")
        assert result == {}
        
        # Test with missing symbols key
        result = _validate_symbol_map({"invalid": "data"})
        assert result == {}
        
        # Test with invalid symbols
        result = _validate_symbol_map({"symbols": "invalid"})
        assert result == {}
    
    def test_validate_symbol_map_missing_fields(self):
        """Test validating symbol map with missing fields."""
        symbol_map = {
            "symbols": {
                "Test Symbol": {
                    "vector": {}
                }
            }
        }
        
        validated = _validate_symbol_map(symbol_map)
        assert "symbols" in validated
        assert "Test Symbol" in validated["symbols"]
        
        symbol_data = validated["symbols"]["Test Symbol"]
        assert "layer_hint" in symbol_data
        assert "vector" in symbol_data
        assert symbol_data["layer_hint"] == []  # Default value
        assert symbol_data["vector"]["double_line"] == False  # Default value
        assert symbol_data["vector"]["stroke_min"] == 0.5  # Default value
        assert symbol_data["vector"]["stroke_max"] == 5.0  # Default value
    
    @patch('app.services.detectors.symbol_map.complete_json_with_schema')
    def test_build_symbol_map_via_llm(self, mock_complete_json):
        """Test building symbol map via LLM."""
        # Mock LLM response
        mock_response = {
            "symbols": {
                "Test Symbol": {
                    "layer_hint": ["LAYER1"],
                    "vector": {
                        "double_line": False,
                        "stroke_min": 1.0,
                        "stroke_max": 2.0
                    }
                }
            }
        }
        mock_complete_json.return_value = mock_response
        
        # Create test snippets
        snippet = SymbolSnippet(
            vectors=[],
            texts=[],
            bbox=BBox(0.0, 0.0, 10.0, 10.0),
            stroke_pattern="solid",
            stroke_width_stats={"min": 1.0, "max": 1.0, "mean": 1.0},
            shape_hints=["line"],
            adjacent_text=[]
        )
        
        result = build_symbol_map_via_llm([snippet], "Test notes")
        
        assert "symbols" in result
        assert "Test Symbol" in result["symbols"]
        mock_complete_json.assert_called_once()
    
    @patch('app.services.detectors.symbol_map.complete_json_with_schema')
    def test_build_symbol_map_via_llm_error(self, mock_complete_json):
        """Test building symbol map via LLM with error."""
        mock_complete_json.side_effect = Exception("LLM error")
        
        snippet = SymbolSnippet(
            vectors=[],
            texts=[],
            bbox=BBox(0.0, 0.0, 10.0, 10.0),
            stroke_pattern="solid",
            stroke_width_stats={"min": 1.0, "max": 1.0, "mean": 1.0},
            shape_hints=["line"],
            adjacent_text=[]
        )
        
        result = build_symbol_map_via_llm([snippet], "Test notes")
        assert result == {}


class TestSymbolMapQueries:
    """Test symbol map query functions."""
    
    def test_get_symbol_by_name(self):
        """Test getting symbol by name."""
        symbol_map = {
            "symbols": {
                "Test Symbol": {
                    "layer_hint": ["LAYER1"],
                    "vector": {"double_line": False}
                }
            }
        }
        
        symbol = get_symbol_by_name(symbol_map, "Test Symbol")
        assert symbol is not None
        assert symbol["layer_hint"] == ["LAYER1"]
        
        # Test non-existent symbol
        symbol = get_symbol_by_name(symbol_map, "Non-existent")
        assert symbol is None
        
        # Test invalid symbol map
        symbol = get_symbol_by_name({}, "Test Symbol")
        assert symbol is None
    
    def test_get_symbols_by_layer(self):
        """Test getting symbols by layer."""
        symbol_map = {
            "symbols": {
                "Symbol 1": {
                    "layer_hint": ["LAYER1", "LAYER2"]
                },
                "Symbol 2": {
                    "layer_hint": ["LAYER2"]
                },
                "Symbol 3": {
                    "layer_hint": ["LAYER3"]
                }
            }
        }
        
        symbols = get_symbols_by_layer(symbol_map, "LAYER2")
        assert "Symbol 1" in symbols
        assert "Symbol 2" in symbols
        assert "Symbol 3" not in symbols
        
        # Test non-existent layer
        symbols = get_symbols_by_layer(symbol_map, "NON_EXISTENT")
        assert symbols == []
        
        # Test invalid symbol map
        symbols = get_symbols_by_layer({}, "LAYER1")
        assert symbols == []
    
    def test_get_symbols_by_shape(self):
        """Test getting symbols by shape."""
        symbol_map = {
            "symbols": {
                "Symbol 1": {
                    "layer_hint": ["LAYER1"],
                    "shape": {"circle": 1, "line": 0}
                },
                "Symbol 2": {
                    "layer_hint": ["LAYER1"],
                    "shape": {"line": 1, "circle": 0}
                },
                "Symbol 3": {
                    "layer_hint": ["LAYER1"],
                    "shape": {"triangle": 1}
                }
            }
        }
        
        symbols = get_symbols_by_shape(symbol_map, "circle")
        assert "Symbol 1" in symbols
        assert "Symbol 2" not in symbols
        assert "Symbol 3" not in symbols
        
        symbols = get_symbols_by_shape(symbol_map, "line")
        assert "Symbol 2" in symbols
        assert "Symbol 1" not in symbols
        assert "Symbol 3" not in symbols
        
        # Test non-existent shape
        symbols = get_symbols_by_shape(symbol_map, "square")
        assert symbols == []
        
        # Test invalid symbol map
        symbols = get_symbols_by_shape({}, "circle")
        assert symbols == []


class TestSymbolMapIO:
    """Test symbol map import/export functionality."""
    
    def test_export_symbol_map(self):
        """Test exporting symbol map to file."""
        symbol_map = {
            "symbols": {
                "Test Symbol": {
                    "layer_hint": ["LAYER1"],
                    "vector": {"double_line": False}
                }
            }
        }
        
        # Test successful export
        with patch('builtins.open', create=True) as mock_open:
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            result = export_symbol_map(symbol_map, "test.json")
            assert result == True
            mock_file.write.assert_called_once()
    
    def test_export_symbol_map_error(self):
        """Test exporting symbol map with error."""
        symbol_map = {"symbols": {}}
        
        # Test export error
        with patch('builtins.open', side_effect=Exception("File error")):
            result = export_symbol_map(symbol_map, "test.json")
            assert result == False
    
    def test_import_symbol_map(self):
        """Test importing symbol map from file."""
        symbol_map = {
            "symbols": {
                "Test Symbol": {
                    "layer_hint": ["LAYER1"],
                    "vector": {"double_line": False}
                }
            }
        }
        
        # Test successful import
        with patch('builtins.open', create=True) as mock_open:
            mock_file = Mock()
            mock_file.read.return_value = json.dumps(symbol_map)
            mock_open.return_value.__enter__.return_value = mock_file
            
            result = import_symbol_map("test.json")
            assert result is not None
            assert "symbols" in result
            assert "Test Symbol" in result["symbols"]
    
    def test_import_symbol_map_error(self):
        """Test importing symbol map with error."""
        # Test file not found
        with patch('builtins.open', side_effect=FileNotFoundError):
            result = import_symbol_map("nonexistent.json")
            assert result is None
        
        # Test JSON parse error
        with patch('builtins.open', create=True) as mock_open:
            mock_file = Mock()
            mock_file.read.return_value = "invalid json"
            mock_open.return_value.__enter__.return_value = mock_file
            
            result = import_symbol_map("test.json")
            assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
