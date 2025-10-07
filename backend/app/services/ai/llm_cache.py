"""
Local LLM response cache for deterministic replay.

Caches LLM responses by (model, prompt_version, schema_version, content_hash)
to ensure identical inputs always produce identical outputs, even if OpenAI
updates their models or has issues.

Cache is stored in backend/artifacts/llm_cache/{cache_key}.json
"""
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Cache directory
CACHE_DIR = Path("backend/artifacts/llm_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Current versions (bump these when prompt/schema changes)
PROMPT_VERSION = "v1.1"  # Added anti-collapse guardrails
SCHEMA_VERSION = "v1.1"  # Added evidence_refs, reason length constraint


def get_cache_key(
    model_name: str,
    prompt_version: str,
    schema_version: str,
    content_hash: str
) -> str:
    """
    Generate cache key from model config and content.
    
    Format: {model}_{prompt_v}_{schema_v}_{content_hash[:12]}
    """
    return f"{model_name}_{prompt_version}_{schema_version}_{content_hash[:12]}"


def get_cache_path(cache_key: str) -> Path:
    """Get filesystem path for cache entry."""
    return CACHE_DIR / f"{cache_key}.json"


def read_cache(
    model_name: str,
    content_hash: str,
    prompt_version: str = PROMPT_VERSION,
    schema_version: str = SCHEMA_VERSION
) -> Optional[Dict[str, Any]]:
    """
    Read cached LLM response if available.
    
    Returns:
        Cached response dict, or None if not cached
    """
    cache_key = get_cache_key(model_name, prompt_version, schema_version, content_hash)
    cache_path = get_cache_path(cache_key)
    
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        
        logger.info(f"💾 Cache HIT: {cache_key}")
        return cached.get("response")
    
    except Exception as e:
        logger.warning(f"Cache read failed for {cache_key}: {e}")
        return None


def write_cache(
    model_name: str,
    content_hash: str,
    request_context: Dict[str, Any],
    response: Dict[str, Any],
    prompt_version: str = PROMPT_VERSION,
    schema_version: str = SCHEMA_VERSION,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Write LLM response to cache.
    
    Args:
        model_name: LLM model identifier
        content_hash: SHA256 hash of canonicalized input
        request_context: Original request context (for debugging)
        response: LLM response to cache
        prompt_version: Version of system prompt
        schema_version: Version of JSON schema
        metadata: Optional metadata (e.g., tokens used, latency)
    
    Returns:
        Cache key
    """
    cache_key = get_cache_key(model_name, prompt_version, schema_version, content_hash)
    cache_path = get_cache_path(cache_key)
    
    cache_entry = {
        "cache_key": cache_key,
        "model": model_name,
        "prompt_version": prompt_version,
        "schema_version": schema_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_context": request_context,
        "response": response,
        "metadata": metadata or {}
    }
    
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_entry, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Cache WRITE: {cache_key}")
        return cache_key
    
    except Exception as e:
        logger.error(f"Cache write failed for {cache_key}: {e}")
        return cache_key


def clear_cache(model_name: Optional[str] = None) -> int:
    """
    Clear cache entries.
    
    Args:
        model_name: If provided, only clear entries for this model.
                   If None, clear all entries.
    
    Returns:
        Number of entries cleared
    """
    cleared = 0
    
    for cache_file in CACHE_DIR.glob("*.json"):
        if model_name:
            # Only clear if filename starts with model name
            if not cache_file.stem.startswith(model_name):
                continue
        
        try:
            cache_file.unlink()
            cleared += 1
        except Exception as e:
            logger.warning(f"Failed to delete {cache_file}: {e}")
    
    logger.info(f"Cleared {cleared} cache entries")
    return cleared


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Returns:
        Dict with cache size, entry count, etc.
    """
    cache_files = list(CACHE_DIR.glob("*.json"))
    
    total_size = sum(f.stat().st_size for f in cache_files)
    
    return {
        "entry_count": len(cache_files),
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "cache_dir": str(CACHE_DIR)
    }

