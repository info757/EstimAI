"""Simple LLM client for vision tasks."""
import json
import httpx
from typing import Dict, Any
from backend.app.core.config import settings


class VisionLLM:
    """Simple vision LLM client with JSON-only responses."""
    
    def __init__(self, model: str = None):
        """Initialize the client with model name."""
        self.model = model or settings.VISION_MODEL
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not set (check backend/.env)")
        self.api_key = settings.OPENAI_API_KEY
    
    async def infer(self, image_b64: str, prompt: str, json_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns a dict validated by the schema (model asked to output JSON only).
        
        Args:
            image_b64: Base64 encoded image
            prompt: Text prompt for the model
            json_schema: JSON schema for response format
            
        Returns:
            Parsed JSON response as dict
            
        Raises:
            Exception: If API call fails or response is invalid JSON
        """
        payload = {
            "model": self.model,
            # Instruct the model to return JSON matching the schema
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "detections_schema",
                    "schema": json_schema,
                    "strict": True
                }
            },
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                    ]
                }
            ]
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # simple one-shot call
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            if r.status_code == 401:
                raise RuntimeError("OpenAI 401 Unauthorized — check OPENAI_API_KEY in backend/.env")
            r.raise_for_status()
            data = r.json()
        # extract the JSON content
        text = data["choices"][0]["message"]["content"]
        try:
            return json.loads(text)
        except Exception:
            # last-resort cleanup
            text = text.strip().split("```json")[-1].split("```")[0].strip()
            return json.loads(text)


# Convenience function for quick usage
def get_vision_llm() -> VisionLLM:
    """Get a configured VisionLLM instance."""
    return VisionLLM()
