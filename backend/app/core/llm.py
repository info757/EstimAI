import asyncio
import json
import os
from typing import Any, Dict
import time

from openai import OpenAI
from jsonschema import validate, ValidationError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def llm_call_json(*, prompt: str, context: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call OpenAI model with JSON mode and validate response against schema.
    
    Implements local caching by content hash for deterministic replay.
    
    Args:
        prompt: System prompt for the model
        context: Context data to be serialized as JSON in user message
        schema: JSON schema to validate the response against
        
    Returns:
        Dict that matches the provided schema
        
    Raises:
        RuntimeError: If OPENAI_API_KEY is not set
        ValueError: If response parsing or validation fails
    """
    from backend.app.services.ai.canonicalize import content_hash
    from backend.app.services.ai.llm_cache import read_cache, write_cache
    
    # Compute content hash for caching
    ctx_hash = content_hash(context)
    model_name = "gpt-4o-mini"
    
    # Try local cache first
    cached_response = read_cache(model_name, ctx_hash)
    if cached_response is not None:
        return cached_response
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is required")
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Build messages
    system_message = {"role": "system", "content": prompt}
    user_message = {"role": "user", "content": json.dumps(context, indent=2)}
    
    # Retry configuration
    max_retries = 2
    base_delay = 0.5
    
    for attempt in range(max_retries + 1):
        try:
            # Get seed from settings for deterministic results
            from backend.app.core.config import settings
            
            # Build API call parameters with full determinism
            call_params = {
                "model": "gpt-4o-mini",
                "messages": [system_message, user_message],
                "response_format": {"type": "json_object"},
                # Deterministic parameters
                "temperature": 0,
                "top_p": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0,
                "max_tokens": 4000,  # Generous limit to prevent truncation
            }
            
            # Add seed for deterministic results if configured
            import logging
            logger = logging.getLogger(__name__)
            
            if settings.ESTIMAI_SEED is not None:
                call_params["seed"] = settings.ESTIMAI_SEED
                logger.info(f"🎲 Deterministic mode: model={call_params['model']}, seed={settings.ESTIMAI_SEED}, temp=0, top_p=1, max_tokens={call_params['max_tokens']}")
            else:
                logger.info(f"⚠️ Non-deterministic mode: model={call_params['model']}, temp=0, top_p=1 (no seed)")
            
            # Make API call
            response = client.chat.completions.create(**call_params)
            
            # Extract content from response
            content = response.choices[0].message.content
            
            # Parse JSON response
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                raw_text = content[:200] + "..." if len(content) > 200 else content
                raise ValueError(f"Failed to parse JSON response: {e}. Raw text: {raw_text}")
            
            # Validate against schema if provided
            if schema is not None:
                try:
                    validate(instance=result, schema=schema)
                except ValidationError as e:
                    raw_text = content[:200] + "..." if len(content) > 200 else content
                    raise ValueError(f"Response validation failed: {e}. Raw text: {raw_text}")
            
            # Cache successful response
            metadata = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                "completion_tokens": response.usage.completion_tokens if response.usage else None,
                "model_fingerprint": getattr(response, 'system_fingerprint', None),
            }
            write_cache(
                model_name=model_name,
                content_hash=ctx_hash,
                request_context=context,
                response=result,
                metadata=metadata
            )
            
            return result
            
        except Exception as e:
            # Check if we should retry
            if attempt < max_retries and (
                hasattr(e, 'status_code') and e.status_code in [429, 500, 502, 503, 504]
            ):
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
                continue
            else:
                # Re-raise the original exception
                raise
