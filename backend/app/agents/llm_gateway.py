"""
LLM Gateway for agent communication.

Provides a unified interface for LLM communication across agents.
"""
import json
import logging
from typing import Any, Dict, Optional
from backend.app.core.llm import llm_call_json

logger = logging.getLogger(__name__)


async def complete_json(
    system_prompt: str,
    user_prompt: str,
    context: Optional[Dict[str, Any]] = None,
    schema: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Complete JSON response using LLM with schema validation.
    
    Args:
        system_prompt: System prompt for the LLM
        user_prompt: User prompt for the LLM
        context: Optional context data
        schema: Optional JSON schema for validation
        
    Returns:
        Dictionary with LLM response
    """
    try:
        # Prepare context
        full_context = context or {}
        full_context['user_prompt'] = user_prompt
        
        # Call LLM with JSON mode
        result = await llm_call_json(
            prompt=system_prompt,
            context=full_context,
            schema=schema
        )
        
        return result
        
    except Exception as e:
        logger.error(f"LLM completion failed: {str(e)}")
        raise Exception(f"LLM completion failed: {str(e)}")


async def complete_text(
    system_prompt: str,
    user_prompt: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Complete text response using LLM.
    
    Args:
        system_prompt: System prompt for the LLM
        user_prompt: User prompt for the LLM
        context: Optional context data
        
    Returns:
        String with LLM response
    """
    try:
        # For now, use the JSON completion and extract text
        # In a full implementation, this would use a different LLM endpoint
        result = await complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context=context
        )
        
        # Extract text from result
        if isinstance(result, dict):
            return result.get('text', str(result))
        else:
            return str(result)
            
    except Exception as e:
        logger.error(f"LLM text completion failed: {str(e)}")
        raise Exception(f"LLM text completion failed: {str(e)}")


def validate_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """
    Validate data against JSON schema.
    
    Args:
        data: Data to validate
        schema: JSON schema
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Simple validation - in production this would use jsonschema library
        if not isinstance(data, dict):
            return False
        
        # Check required fields
        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in data:
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Schema validation failed: {str(e)}")
        return False
