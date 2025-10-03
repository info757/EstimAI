"""Tests for LLM gateway functionality."""
import pytest
import json
from unittest.mock import Mock, patch

from backend.app.agents.llm_gateway import (
    complete_json, complete_json_with_schema, validate_json_schema,
    _validate_field
)


class TestLLMGateway:
    """Test LLM gateway functionality."""
    
    @patch('app.agents.llm_gateway.VisionLLM')
    def test_complete_json_success(self, mock_vision_llm):
        """Test successful JSON completion."""
        # Mock LLM response
        mock_llm_instance = Mock()
        mock_llm_instance.infer.return_value = {
            "response": {
                "result": "test response",
                "status": "success"
            }
        }
        mock_vision_llm.return_value = mock_llm_instance
        
        system_prompt = "You are a test assistant."
        user_prompt = "Generate a test response."
        
        result = complete_json(system_prompt, user_prompt)
        
        assert result == {
            "result": "test response",
            "status": "success"
        }
        mock_llm_instance.infer.assert_called_once()
    
    @patch('app.agents.llm_gateway.VisionLLM')
    def test_complete_json_error(self, mock_vision_llm):
        """Test JSON completion with error."""
        mock_llm_instance = Mock()
        mock_llm_instance.infer.side_effect = Exception("LLM error")
        mock_vision_llm.return_value = mock_llm_instance
        
        system_prompt = "You are a test assistant."
        user_prompt = "Generate a test response."
        
        with pytest.raises(RuntimeError, match="LLM completion failed"):
            complete_json(system_prompt, user_prompt)
    
    @patch('app.agents.llm_gateway.VisionLLM')
    def test_complete_json_missing_response(self, mock_vision_llm):
        """Test JSON completion with missing response field."""
        mock_llm_instance = Mock()
        mock_llm_instance.infer.return_value = {"invalid": "data"}
        mock_vision_llm.return_value = mock_llm_instance
        
        system_prompt = "You are a test assistant."
        user_prompt = "Generate a test response."
        
        with pytest.raises(RuntimeError, match="LLM response missing 'response' field"):
            complete_json(system_prompt, user_prompt)
    
    @patch('app.agents.llm_gateway.VisionLLM')
    def test_complete_json_with_schema_success(self, mock_vision_llm):
        """Test successful JSON completion with custom schema."""
        # Mock LLM response
        mock_llm_instance = Mock()
        mock_llm_instance.infer.return_value = {
            "response": {
                "symbols": {
                    "Test Symbol": {
                        "layer_hint": ["LAYER1"],
                        "vector": {"double_line": False}
                    }
                }
            }
        }
        mock_vision_llm.return_value = mock_llm_instance
        
        system_prompt = "You are a symbol mapping assistant."
        user_prompt = "Map these symbols."
        response_schema = {
            "type": "object",
            "properties": {
                "symbols": {"type": "object"}
            }
        }
        
        result = complete_json_with_schema(system_prompt, user_prompt, response_schema)
        
        assert "symbols" in result
        assert "Test Symbol" in result["symbols"]
        mock_llm_instance.infer.assert_called_once()
    
    @patch('app.agents.llm_gateway.VisionLLM')
    def test_complete_json_with_schema_error(self, mock_vision_llm):
        """Test JSON completion with schema error."""
        mock_llm_instance = Mock()
        mock_llm_instance.infer.side_effect = Exception("LLM error")
        mock_vision_llm.return_value = mock_llm_instance
        
        system_prompt = "You are a test assistant."
        user_prompt = "Generate a test response."
        response_schema = {"type": "object"}
        
        with pytest.raises(RuntimeError, match="LLM completion failed"):
            complete_json_with_schema(system_prompt, user_prompt, response_schema)


class TestJSONSchemaValidation:
    """Test JSON schema validation functionality."""
    
    def test_validate_json_schema_valid(self):
        """Test validating valid JSON schema."""
        data = {
            "name": "test",
            "value": 123,
            "active": True
        }
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"},
                "active": {"type": "boolean"}
            },
            "required": ["name", "value"]
        }
        
        result = validate_json_schema(data, schema)
        assert result == True
    
    def test_validate_json_schema_invalid_type(self):
        """Test validating invalid JSON schema type."""
        data = "not a dict"
        schema = {
            "type": "object",
            "properties": {}
        }
        
        result = validate_json_schema(data, schema)
        assert result == False
    
    def test_validate_json_schema_missing_required(self):
        """Test validating JSON schema with missing required fields."""
        data = {
            "name": "test"
            # Missing required "value" field
        }
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"}
            },
            "required": ["name", "value"]
        }
        
        result = validate_json_schema(data, schema)
        assert result == False
    
    def test_validate_json_schema_invalid_field_type(self):
        """Test validating JSON schema with invalid field types."""
        data = {
            "name": "test",
            "value": "not a number"  # Should be number
        }
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"}
            }
        }
        
        result = validate_json_schema(data, schema)
        assert result == False
    
    def test_validate_json_schema_error(self):
        """Test validating JSON schema with error."""
        data = {"test": "data"}
        schema = {"invalid": "schema"}
        
        result = validate_json_schema(data, schema)
        assert result == True  # Should handle error gracefully


class TestFieldValidation:
    """Test field validation functionality."""
    
    def test_validate_field_string(self):
        """Test validating string field."""
        result = _validate_field("test", {"type": "string"})
        assert result == True
        
        result = _validate_field(123, {"type": "string"})
        assert result == False
    
    def test_validate_field_number(self):
        """Test validating number field."""
        result = _validate_field(123, {"type": "number"})
        assert result == True
        
        result = _validate_field(123.45, {"type": "number"})
        assert result == True
        
        result = _validate_field("123", {"type": "number"})
        assert result == False
    
    def test_validate_field_boolean(self):
        """Test validating boolean field."""
        result = _validate_field(True, {"type": "boolean"})
        assert result == True
        
        result = _validate_field(False, {"type": "boolean"})
        assert result == True
        
        result = _validate_field("true", {"type": "boolean"})
        assert result == False
    
    def test_validate_field_array(self):
        """Test validating array field."""
        result = _validate_field([1, 2, 3], {"type": "array"})
        assert result == True
        
        result = _validate_field("not array", {"type": "array"})
        assert result == False
    
    def test_validate_field_object(self):
        """Test validating object field."""
        result = _validate_field({"key": "value"}, {"type": "object"})
        assert result == True
        
        result = _validate_field("not object", {"type": "object"})
        assert result == False
    
    def test_validate_field_no_type(self):
        """Test validating field without type constraint."""
        result = _validate_field("any value", {})
        assert result == True
    
    def test_validate_field_error(self):
        """Test validating field with error."""
        result = _validate_field("test", {"invalid": "schema"})
        assert result == True  # Should handle error gracefully


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
