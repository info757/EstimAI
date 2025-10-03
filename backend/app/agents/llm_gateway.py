"""LLM Gateway for structured JSON responses using existing LLM infrastructure."""
import json
import logging
from typing import Dict, Any, Optional

from ..services.llm_client import VisionLLM
from ..core.config import settings

logger = logging.getLogger(__name__)


def complete_json(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    """
    Complete a JSON response using the existing LLM infrastructure.
    
    This function uses the existing VisionLLM client to generate structured JSON responses
    for text-based tasks (not requiring image input).
    
    Args:
        system_prompt: System prompt for the LLM
        user_prompt: User prompt with the task description
        
    Returns:
        Parsed JSON response as a dictionary
        
    Raises:
        RuntimeError: If LLM response is invalid or cannot be parsed
    """
    try:
        # Initialize the LLM client
        llm = VisionLLM()
        
        # Create a JSON schema for the response
        json_schema = {
            "type": "object",
            "properties": {
                "response": {
                    "type": "object",
                    "description": "The structured response data"
                }
            },
            "required": ["response"],
            "additionalProperties": False
        }
        
        # Combine prompts
        full_prompt = f"{system_prompt}\n\n{user_prompt}\n\nReturn your response as valid JSON."
        
        # Use a dummy base64 image (empty 1x1 pixel) since we're doing text-only processing
        # The VisionLLM client expects an image, so we provide a minimal one
        dummy_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        
        # Call the LLM
        response = llm.infer(dummy_image_b64, full_prompt, json_schema)
        
        if not response or "response" not in response:
            raise RuntimeError("LLM response missing 'response' field")
        
        return response["response"]
        
    except Exception as e:
        logger.error(f"Error in complete_json: {e}")
        raise RuntimeError(f"LLM completion failed: {e}") from e


def complete_json_with_schema(system_prompt: str, user_prompt: str, response_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Complete a JSON response with a custom schema.
    
    Args:
        system_prompt: System prompt for the LLM
        user_prompt: User prompt with the task description
        response_schema: Custom JSON schema for the response
        
    Returns:
        Parsed JSON response as a dictionary
    """
    try:
        # Initialize the LLM client
        llm = VisionLLM()
        
        # Create the full schema with the custom response schema
        json_schema = {
            "type": "object",
            "properties": {
                "response": response_schema
            },
            "required": ["response"],
            "additionalProperties": False
        }
        
        # Combine prompts
        full_prompt = f"{system_prompt}\n\n{user_prompt}\n\nReturn your response as valid JSON matching the provided schema."
        
        # Use a dummy base64 image (empty 1x1 pixel) since we're doing text-only processing
        dummy_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        
        # Call the LLM
        response = llm.infer(dummy_image_b64, full_prompt, json_schema)
        
        if not response or "response" not in response:
            raise RuntimeError("LLM response missing 'response' field")
        
        return response["response"]
        
    except Exception as e:
        logger.error(f"Error in complete_json_with_schema: {e}")
        raise RuntimeError(f"LLM completion failed: {e}") from e


def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """
    Validate data against a JSON schema.
    
    Args:
        data: Data to validate
        schema: JSON schema to validate against
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Simple validation - in production you might want to use jsonschema library
        if not isinstance(data, dict):
            return False
        
        # Check required fields
        if "required" in schema:
            for field in schema["required"]:
                if field not in data:
                    return False
        
        # Check properties
        if "properties" in schema:
            for field, field_schema in schema["properties"].items():
                if field in data:
                    if not _validate_field(data[field], field_schema):
                        return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating JSON schema: {e}")
        return False


def _validate_field(value: Any, field_schema: Dict[str, Any]) -> bool:
    """Validate a single field against its schema."""
    try:
        if "type" in field_schema:
            expected_type = field_schema["type"]
            if expected_type == "string" and not isinstance(value, str):
                return False
            elif expected_type == "number" and not isinstance(value, (int, float)):
                return False
            elif expected_type == "boolean" and not isinstance(value, bool):
                return False
            elif expected_type == "array" and not isinstance(value, list):
                return False
            elif expected_type == "object" and not isinstance(value, dict):
                return False
        
        return True
        
    except Exception:
        return False
