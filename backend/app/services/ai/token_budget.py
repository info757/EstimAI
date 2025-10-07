"""
Token budgeting and context length management.

Prevents context overflow by:
1. Estimating token count before sending
2. Tiling large inputs into manageable chunks
3. Spatial clustering for geographic data
"""
import json
import logging
import math
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

# Model limits (gpt-4o-mini)
MAX_CONTEXT_TOKENS = 128_000
MAX_OUTPUT_TOKENS = 4_000
SAFE_PROMPT_TOKENS = MAX_CONTEXT_TOKENS - MAX_OUTPUT_TOKENS - 1_000  # 123k safety margin

# Token estimation (rough approximation: 1 token ≈ 4 chars for English)
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.
    
    Uses simple heuristic: 1 token ≈ 4 characters.
    This is conservative for English, may overestimate for code/JSON.
    
    For production, use tiktoken library for accurate counts.
    """
    return len(text) // CHARS_PER_TOKEN


def estimate_context_tokens(
    prompt: str,
    context: Dict[str, Any]
) -> int:
    """
    Estimate total token count for LLM call.
    
    Returns:
        Estimated token count (prompt + context)
    """
    prompt_tokens = estimate_tokens(prompt)
    context_tokens = estimate_tokens(json.dumps(context))
    
    total = prompt_tokens + context_tokens
    
    logger.debug(f"Token estimate: prompt={prompt_tokens}, context={context_tokens}, total={total}")
    
    return total


def check_context_length(
    prompt: str,
    context: Dict[str, Any],
    max_tokens: int = SAFE_PROMPT_TOKENS
) -> Tuple[bool, int]:
    """
    Check if context fits within token budget.
    
    Returns:
        (fits: bool, token_count: int)
    """
    token_count = estimate_context_tokens(prompt, context)
    fits = token_count <= max_tokens
    
    if not fits:
        logger.warning(
            f"⚠️ Context overflow: {token_count} tokens > {max_tokens} limit "
            f"({token_count - max_tokens} tokens over)"
        )
    
    return (fits, token_count)


def spatial_tile_candidates(
    candidates: List[Dict[str, Any]],
    tile_size_ft: float = 500.0,
    overlap_ft: float = 100.0
) -> List[List[Dict[str, Any]]]:
    """
    Tile candidates into spatial neighborhoods for batch processing.
    
    Strategy:
    1. Compute bounding box of all candidates
    2. Divide into tiles (500 ft × 500 ft with 100 ft overlap)
    3. Assign candidates to tiles based on bbox center
    4. Include nearby candidates in overlap zones
    
    Args:
        candidates: List of candidate dicts with bbox field
        tile_size_ft: Size of each tile in feet (default 500)
        overlap_ft: Overlap between tiles in feet (default 100)
        
    Returns:
        List of candidate lists (one per tile)
    """
    if not candidates:
        return []
    
    # Extract bboxes
    bboxes = []
    for c in candidates:
        bbox = c.get("bbox", [0, 0, 0, 0])
        if len(bbox) >= 4:
            bboxes.append(bbox)
    
    if not bboxes:
        return [candidates]  # No spatial info, return as single tile
    
    # Compute global bounds
    min_x = min(bbox[0] for bbox in bboxes)
    min_y = min(bbox[1] for bbox in bboxes)
    max_x = max(bbox[2] for bbox in bboxes)
    max_y = max(bbox[3] for bbox in bboxes)
    
    width = max_x - min_x
    height = max_y - min_y
    
    # Calculate number of tiles
    stride = tile_size_ft - overlap_ft
    num_tiles_x = max(1, math.ceil(width / stride))
    num_tiles_y = max(1, math.ceil(height / stride))
    
    logger.info(
        f"Spatial tiling: {len(candidates)} candidates → "
        f"{num_tiles_x}×{num_tiles_y} tiles "
        f"({tile_size_ft}ft with {overlap_ft}ft overlap)"
    )
    
    # Create tiles
    tiles: List[List[Dict[str, Any]]] = []
    
    for ty in range(num_tiles_y):
        for tx in range(num_tiles_x):
            # Tile bounds
            tile_min_x = min_x + tx * stride
            tile_min_y = min_y + ty * stride
            tile_max_x = tile_min_x + tile_size_ft
            tile_max_y = tile_min_y + tile_size_ft
            
            # Collect candidates in this tile (by bbox center)
            tile_candidates = []
            for c in candidates:
                bbox = c.get("bbox", [0, 0, 0, 0])
                if len(bbox) < 4:
                    continue
                
                # Compute center
                cx = (bbox[0] + bbox[2]) / 2
                cy = (bbox[1] + bbox[3]) / 2
                
                # Check if in tile (with overlap)
                if (tile_min_x <= cx <= tile_max_x and 
                    tile_min_y <= cy <= tile_max_y):
                    tile_candidates.append(c)
            
            if tile_candidates:
                tiles.append(tile_candidates)
                logger.debug(
                    f"Tile ({tx},{ty}): {len(tile_candidates)} candidates "
                    f"at ({tile_min_x:.0f},{tile_min_y:.0f})"
                )
    
    if not tiles:
        # Fallback: all in one tile
        tiles = [candidates]
    
    logger.info(f"Created {len(tiles)} non-empty tiles")
    
    return tiles


def filter_nearby_labels(
    candidate: Dict[str, Any],
    all_labels: List[str],
    max_labels: int = 20
) -> List[str]:
    """
    Filter labels to only include those near the candidate.
    
    For now, uses simple truncation. In production, use spatial index.
    
    Args:
        candidate: Candidate dict with bbox
        all_labels: All available labels
        max_labels: Max labels to include per candidate
        
    Returns:
        Filtered list of nearby labels
    """
    # Simple truncation for now
    # TODO: Implement spatial filtering using bbox proximity
    nearby_text = candidate.get("nearby_text", [])
    
    if len(nearby_text) <= max_labels:
        return nearby_text
    
    # Truncate to max
    logger.debug(
        f"Truncating labels for {candidate.get('id')}: "
        f"{len(nearby_text)} → {max_labels}"
    )
    return nearby_text[:max_labels]


def tile_large_context(
    prompt: str,
    context: Dict[str, Any],
    max_tokens: int = SAFE_PROMPT_TOKENS
) -> List[Dict[str, Any]]:
    """
    Tile a large context into smaller chunks that fit within token budget.
    
    Strategy:
    1. Check if context fits
    2. If not, split candidates into spatial tiles
    3. Create separate context for each tile
    4. Each tile includes only nearby labels
    
    Args:
        prompt: System prompt (constant across tiles)
        context: Full context dict
        max_tokens: Max tokens per tile
        
    Returns:
        List of context dicts (one per tile)
    """
    # Check if fits
    fits, token_count = check_context_length(prompt, context, max_tokens)
    
    if fits:
        logger.info(f"Context fits in budget: {token_count} tokens < {max_tokens}")
        return [context]
    
    # Need to tile
    logger.warning(
        f"Context overflow: {token_count} tokens > {max_tokens}. "
        f"Splitting into spatial tiles..."
    )
    
    candidates = context.get("candidates", [])
    
    if not candidates:
        # Nothing to tile
        logger.error("Context overflow but no candidates to tile!")
        return [context]
    
    # Tile spatially
    tiles = spatial_tile_candidates(candidates)
    
    # Create context for each tile
    tiled_contexts = []
    for i, tile_candidates in enumerate(tiles):
        tile_context = {
            "task": context.get("task", "classify_utility_pipes"),
            "candidates": tile_candidates,
            "legend_ontology": context.get("legend_ontology"),
            "scale_info": context.get("scale_info"),
            "instructions": context.get("instructions"),
            "tile_info": {
                "tile_number": i + 1,
                "total_tiles": len(tiles),
                "candidates_in_tile": len(tile_candidates)
            }
        }
        
        # Verify this tile fits
        tile_fits, tile_tokens = check_context_length(prompt, tile_context, max_tokens)
        
        if not tile_fits:
            logger.error(
                f"Tile {i+1} still too large: {tile_tokens} tokens! "
                f"Consider smaller tile size or fewer labels."
            )
        else:
            logger.info(
                f"Tile {i+1}/{len(tiles)}: {len(tile_candidates)} candidates, "
                f"{tile_tokens} tokens"
            )
        
        tiled_contexts.append(tile_context)
    
    return tiled_contexts


def log_token_stats(
    prompt: str,
    context: Dict[str, Any],
    response: Any = None
) -> Dict[str, int]:
    """
    Log token usage statistics for debugging.
    
    Args:
        prompt: System prompt
        context: Context dict
        response: Optional LLM response (for completion tokens)
        
    Returns:
        Dict with token stats
    """
    prompt_tokens = estimate_tokens(prompt)
    context_tokens = estimate_tokens(json.dumps(context))
    total_input = prompt_tokens + context_tokens
    
    stats = {
        "prompt_tokens": prompt_tokens,
        "context_tokens": context_tokens,
        "total_input_tokens": total_input,
        "completion_tokens": 0,
        "total_tokens": total_input
    }
    
    if response:
        response_tokens = estimate_tokens(json.dumps(response))
        stats["completion_tokens"] = response_tokens
        stats["total_tokens"] = total_input + response_tokens
    
    logger.info(
        f"📊 Token usage: "
        f"input={stats['total_input_tokens']} "
        f"(prompt={stats['prompt_tokens']}, context={stats['context_tokens']}), "
        f"output={stats['completion_tokens']}, "
        f"total={stats['total_tokens']}"
    )
    
    # Warn if approaching limit
    if stats['total_tokens'] > MAX_CONTEXT_TOKENS * 0.9:
        logger.warning(
            f"⚠️ Approaching context limit: {stats['total_tokens']} / {MAX_CONTEXT_TOKENS} "
            f"({stats['total_tokens'] / MAX_CONTEXT_TOKENS * 100:.1f}%)"
        )
    
    return stats

