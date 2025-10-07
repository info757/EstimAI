"""
LLM-based elevation parser for pipe invert elevations.

Uses a focused system prompt to extract IE/INV values from text near pipe endpoints.
"""
import logging
from typing import Optional
import json
import os
import httpx

logger = logging.getLogger(__name__)


class ElevationParser:
    """LLM-based parser for extracting invert elevations from text."""
    
    def __init__(self, model: str = "gpt-4o-mini", timeout: int = 30):
        self.model = model
        self.timeout = timeout
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set - elevation parsing will be limited to regex")
    
    async def parse_elevation_async(
        self,
        text_snippet: str,
        endpoint_label: str = "pipe endpoint"
    ) -> Optional[float]:
        """
        Parse elevation from text snippet using LLM.
        
        Args:
            text_snippet: Text near the endpoint (e.g., "IE=95.5 12\" PVC")
            endpoint_label: Description of endpoint (e.g., "inlet" or "outlet")
        
        Returns:
            Elevation in feet, or None if not found
        """
        if not self.api_key:
            logger.debug("No API key - skipping LLM elevation parse")
            return None
        
        if not text_snippet or len(text_snippet.strip()) < 3:
            return None
        
        system_prompt = """You are reading a utility plan. Identify invert elevations (INV. or IE) for each pipe endpoint, and report them as numbers in feet above sea level. Do not guess. If not visible, return null.

Rules:
1. Look for patterns like: "IE=95.5", "INV. 94.8", "INV 92.3", "IE 88.0"
2. The number is always in feet (decimal format)
3. Return ONLY the numeric value (e.g., 95.5)
4. If no elevation is visible in the text, return null
5. Do not infer or guess - only extract explicit values"""
        
        user_prompt = f"""Text near {endpoint_label}:
{text_snippet}

Extract the invert elevation (IE/INV) as a number in feet. Return JSON with format:
{{"elevation": <number or null>}}"""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0,
                        "max_tokens": 50,
                        "response_format": {"type": "json_object"}
                    }
                )
                response.raise_for_status()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                
                elevation = parsed.get("elevation")
                if elevation is not None:
                    logger.debug(f"LLM parsed elevation: {elevation} from '{text_snippet[:50]}...'")
                    return float(elevation)
                else:
                    logger.debug(f"LLM found no elevation in '{text_snippet[:50]}...'")
                    return None
        
        except Exception as e:
            logger.warning(f"LLM elevation parse failed: {e}")
            return None
    
    def parse_elevation(
        self,
        text_snippet: str,
        endpoint_label: str = "pipe endpoint"
    ) -> Optional[float]:
        """Synchronous wrapper for parse_elevation_async."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async context - use ThreadPoolExecutor
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.parse_elevation_async(text_snippet, endpoint_label)
                    )
                    return future.result(timeout=self.timeout + 5)
            else:
                return loop.run_until_complete(
                    self.parse_elevation_async(text_snippet, endpoint_label)
                )
        except Exception as e:
            logger.error(f"Failed to run async elevation parse: {e}")
            return None


# Singleton instance
_parser_instance: Optional[ElevationParser] = None


def get_elevation_parser() -> ElevationParser:
    """Get or create singleton elevation parser."""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = ElevationParser()
    return _parser_instance
