"""Symbol mapping utilities using LLM assistance."""
import json
import logging
from typing import Dict, Any, List, Optional

from ..detectors.legend import SymbolSnippet
from ...agents.llm_gateway import complete_json_with_schema

logger = logging.getLogger(__name__)


def build_symbol_map_via_llm(snippets: List[SymbolSnippet], notes_text: str) -> Dict[str, Any]:
    """
    Build symbol map using LLM assistance.
    
    Args:
        snippets: List of symbol snippets from legend regions
        notes_text: Additional notes text from the document
        
    Returns:
        Symbol map dictionary with symbol definitions
    """
    try:
        # Prepare input data for LLM
        snippets_data = _prepare_snippets_data(snippets)
        
        # Create system prompt
        system_prompt = _create_system_prompt()
        
        # Create user prompt
        user_prompt = _create_user_prompt(snippets_data, notes_text)
        
        # Define response schema
        response_schema = _create_response_schema()
        
        # Call LLM
        result = complete_json_with_schema(system_prompt, user_prompt, response_schema)
        
        # Validate and clean the result
        validated_result = _validate_symbol_map(result)
        
        logger.info(f"Generated symbol map with {len(validated_result)} symbols")
        return validated_result
        
    except Exception as e:
        logger.error(f"Error building symbol map via LLM: {e}")
        # Return empty symbol map on error
        return {}


def _prepare_snippets_data(snippets: List[SymbolSnippet]) -> List[Dict[str, Any]]:
    """Prepare symbol snippets data for LLM input."""
    snippets_data = []
    
    for snippet in snippets:
        snippet_data = {
            "vectors": [],
            "texts": [],
            "stroke_pattern": snippet.stroke_pattern,
            "stroke_width_stats": snippet.stroke_width_stats,
            "shape_hints": snippet.shape_hints,
            "adjacent_text": snippet.adjacent_text
        }
        
        # Add vector information
        for vector in snippet.vectors:
            vector_data = {
                "kind": vector.kind,
                "stroke_rgba": vector.stroke_rgba,
                "fill_rgba": vector.fill_rgba,
                "stroke_w": vector.stroke_w,
                "ocg_names": vector.ocg_names
            }
            snippet_data["vectors"].append(vector_data)
        
        # Add text information
        for text in snippet.texts:
            text_data = {
                "text": text.text,
                "bbox": text.bbox,
                "ocg_names": text.ocg_names
            }
            snippet_data["texts"].append(text_data)
        
        snippets_data.append(snippet_data)
    
    return snippets_data


def _create_system_prompt() -> str:
    """Create system prompt for symbol mapping."""
    return """You are a construction drawing expert specializing in symbol recognition and mapping.

Your task is to analyze symbol snippets from construction drawings and create a comprehensive symbol map that can be used for automated detection and classification.

For each symbol, you should identify:
1. The symbol name/type
2. Layer hints (which CAD layers it typically appears on)
3. Vector characteristics (line patterns, shapes, etc.)
4. Text patterns that might accompany the symbol
5. Any other distinguishing features

Focus on common construction symbols like:
- Utilities (water, sewer, storm, gas, electric)
- Infrastructure (roads, curbs, sidewalks)
- Landscaping (trees, shrubs, grass)
- Structures (buildings, fences, walls)
- Equipment (hydrants, valves, meters)

Return a structured JSON response with symbol definitions."""


def _create_user_prompt(snippets_data: List[Dict[str, Any]], notes_text: str) -> str:
    """Create user prompt for symbol mapping."""
    prompt = f"""Analyze the following symbol snippets from a construction drawing legend and create a symbol map.

Symbol Snippets:
{json.dumps(snippets_data, indent=2)}

Additional Notes:
{notes_text}

For each symbol, provide:
- Symbol name (descriptive and consistent)
- Layer hints (typical CAD layers where this symbol appears)
- Vector characteristics (line patterns, shapes, stroke properties)
- Text patterns (regex patterns for associated text)
- Any other distinguishing features

Focus on symbols that are commonly used in construction drawings and can be reliably detected."""

    return prompt


def _create_response_schema() -> Dict[str, Any]:
    """Create JSON schema for symbol map response."""
    return {
        "type": "object",
        "properties": {
            "symbols": {
                "type": "object",
                "patternProperties": {
                    "^[A-Za-z0-9_\\s]+$": {
                        "type": "object",
                        "properties": {
                            "layer_hint": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Typical CAD layers where this symbol appears"
                            },
                            "vector": {
                                "type": "object",
                                "properties": {
                                    "double_line": {"type": "boolean"},
                                    "stroke_min": {"type": "number"},
                                    "stroke_max": {"type": "number"},
                                    "dash": {
                                        "type": "array",
                                        "items": {"type": "number"},
                                        "description": "Dash pattern [dash_length, gap_length]"
                                    },
                                    "color_hint": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Typical colors for this symbol"
                                    }
                                },
                                "additionalProperties": False
                            },
                            "shape": {
                                "type": "object",
                                "properties": {
                                    "circle": {"type": "number"},
                                    "triangle": {"type": "number"},
                                    "square": {"type": "number"},
                                    "line": {"type": "number"},
                                    "polygon": {"type": "number"}
                                },
                                "additionalProperties": False
                            },
                            "text_regex": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Regex patterns for associated text"
                            },
                            "description": {
                                "type": "string",
                                "description": "Human-readable description of the symbol"
                            }
                        },
                        "required": ["layer_hint", "vector"],
                        "additionalProperties": False
                    }
                },
                "additionalProperties": False
            }
        },
        "required": ["symbols"],
        "additionalProperties": False
    }


def _validate_symbol_map(symbol_map: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and clean the symbol map."""
    if not isinstance(symbol_map, dict):
        logger.warning("Invalid symbol map: not a dictionary")
        return {}
    
    if "symbols" not in symbol_map:
        logger.warning("Invalid symbol map: missing 'symbols' key")
        return {}
    
    symbols = symbol_map["symbols"]
    if not isinstance(symbols, dict):
        logger.warning("Invalid symbol map: 'symbols' is not a dictionary")
        return {}
    
    # Clean and validate each symbol
    cleaned_symbols = {}
    for symbol_name, symbol_data in symbols.items():
        if not isinstance(symbol_data, dict):
            logger.warning(f"Invalid symbol data for '{symbol_name}': not a dictionary")
            continue
        
        # Ensure required fields
        if "layer_hint" not in symbol_data:
            symbol_data["layer_hint"] = []
        if "vector" not in symbol_data:
            symbol_data["vector"] = {}
        
        # Validate layer_hint
        if not isinstance(symbol_data["layer_hint"], list):
            symbol_data["layer_hint"] = []
        
        # Validate vector data
        if not isinstance(symbol_data["vector"], dict):
            symbol_data["vector"] = {}
        
        # Add default values for common fields
        if "double_line" not in symbol_data["vector"]:
            symbol_data["vector"]["double_line"] = False
        
        if "stroke_min" not in symbol_data["vector"]:
            symbol_data["vector"]["stroke_min"] = 0.5
        
        if "stroke_max" not in symbol_data["vector"]:
            symbol_data["vector"]["stroke_max"] = 5.0
        
        cleaned_symbols[symbol_name] = symbol_data
    
    return {"symbols": cleaned_symbols}


def get_symbol_by_name(symbol_map: Dict[str, Any], symbol_name: str) -> Optional[Dict[str, Any]]:
    """Get symbol definition by name."""
    if "symbols" not in symbol_map:
        return None
    
    symbols = symbol_map["symbols"]
    return symbols.get(symbol_name)


def get_symbols_by_layer(symbol_map: Dict[str, Any], layer_name: str) -> List[str]:
    """Get symbol names that typically appear on a specific layer."""
    if "symbols" not in symbol_map:
        return []
    
    symbols = symbol_map["symbols"]
    matching_symbols = []
    
    for symbol_name, symbol_data in symbols.items():
        layer_hints = symbol_data.get("layer_hint", [])
        if layer_name in layer_hints:
            matching_symbols.append(symbol_name)
    
    return matching_symbols


def get_symbols_by_shape(symbol_map: Dict[str, Any], shape_type: str) -> List[str]:
    """Get symbol names that have a specific shape characteristic."""
    if "symbols" not in symbol_map:
        return []
    
    symbols = symbol_map["symbols"]
    matching_symbols = []
    
    for symbol_name, symbol_data in symbols.items():
        shape_data = symbol_data.get("shape", {})
        if shape_data.get(shape_type, 0) > 0:
            matching_symbols.append(symbol_name)
    
    return matching_symbols


def export_symbol_map(symbol_map: Dict[str, Any], file_path: str) -> bool:
    """Export symbol map to JSON file."""
    try:
        with open(file_path, 'w') as f:
            json.dump(symbol_map, f, indent=2)
        logger.info(f"Symbol map exported to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error exporting symbol map: {e}")
        return False


def import_symbol_map(file_path: str) -> Optional[Dict[str, Any]]:
    """Import symbol map from JSON file."""
    try:
        with open(file_path, 'r') as f:
            symbol_map = json.load(f)
        
        # Validate the imported symbol map
        validated_map = _validate_symbol_map(symbol_map)
        logger.info(f"Symbol map imported from {file_path}")
        return validated_map
    except Exception as e:
        logger.error(f"Error importing symbol map: {e}")
        return None
