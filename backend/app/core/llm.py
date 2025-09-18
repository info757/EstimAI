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
            # Make API call
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[system_message, user_message],
                response_format={"type": "json_object"},
                temperature=0
            )
            
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
