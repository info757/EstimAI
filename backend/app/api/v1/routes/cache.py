"""
Cache management API endpoints.

Provides endpoints for inspecting and managing the LLM response cache.
"""
from fastapi import APIRouter
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/cache", tags=["cache"])


@router.get("/stats")
def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Returns:
        Dict with cache size, entry count, etc.
    """
    from backend.app.services.ai.llm_cache import get_cache_stats
    
    stats = get_cache_stats()
    return {
        "ok": True,
        "stats": stats
    }


@router.delete("/clear")
def clear_cache(model_name: str | None = None) -> Dict[str, Any]:
    """
    Clear cache entries.
    
    Args:
        model_name: If provided, only clear entries for this model
    
    Returns:
        Number of entries cleared
    """
    from backend.app.services.ai.llm_cache import clear_cache as do_clear
    
    cleared = do_clear(model_name)
    return {
        "ok": True,
        "cleared": cleared,
        "message": f"Cleared {cleared} cache entries"
    }


@router.get("/versions")
def get_cache_versions() -> Dict[str, Any]:
    """
    Get current prompt and schema versions.
    
    Returns:
        Current versions used for caching
    """
    from backend.app.services.ai.llm_cache import PROMPT_VERSION, SCHEMA_VERSION
    
    return {
        "ok": True,
        "versions": {
            "prompt": PROMPT_VERSION,
            "schema": SCHEMA_VERSION
        }
    }

