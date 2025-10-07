"""
LLM-based elevation extraction that reads the entire page context.

Instead of complex coordinate matching, we send the LLM:
- All text on the page
- All polylines (with IDs)
- Ask it to match IE/INV values to pipe IDs

The LLM can "see" spatial relationships through text layout.
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
import json
import os
import httpx
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


async def extract_elevations_llm_async(
    polylines: List[Dict[str, Any]],
    text_runs: List[Dict[str, Any]],
    model: str = "gpt-4o-mini",
    timeout: int = 90
) -> Dict[str, Tuple[Optional[float], Optional[float]]]:
    """
    Extract invert elevations for all pipes using LLM.
    
    Args:
        polylines: List of polyline dicts with id, vertices, material, etc.
        text_runs: List of text run dicts with text and bbox
        model: OpenAI model to use
        timeout: Request timeout in seconds
    
    Returns:
        Dict mapping polyline_id -> (invert_in, invert_out)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set - cannot extract elevations with LLM")
        return {}
    
    if not polylines or not text_runs:
        return {}
    
    # Build context for LLM with coordinates - let LLM figure out coordinate matching
    pipe_summaries = []
    for poly in polylines[:50]:  # Limit to first 50 to avoid token overflow
        pipe_id = poly.get("id", "unknown")
        material = poly.get("material") or poly.get("attrs", {}).get("material") or "unknown"
        dia = poly.get("dia_in") or poly.get("attrs", {}).get("dia_in")
        vertices = poly.get("vertices", [])
        
        # Include coordinates for LLM to use if helpful
        if vertices and len(vertices) >= 2:
            start = vertices[0]
            end = vertices[-1]
            summary = f"Pipe {pipe_id}: {material} {dia}\" at ({start[0]:.1f}, {start[1]:.1f}) to ({end[0]:.1f}, {end[1]:.1f})"
        else:
            summary = f"Pipe {pipe_id}: {material} {dia}\""
        
        pipe_summaries.append(summary)
    
    # Combine text with coordinates
    text_content = "\n".join([
        f"{r.get('text', '')} [at {r.get('bbox', [0,0,0,0])[0]:.1f}, {r.get('bbox', [0,0,0,0])[1]:.1f}]"
        for r in text_runs[:200]
    ])
    
    system_prompt = """You are an expert at reading civil engineering utility plans. Your task is to extract invert elevations (IE/INV) for each pipe.

COORDINATE CONTEXT:
- Coordinate systems may differ between pipes and text (points vs feet vs drawing units)
- Use material/diameter labels as PRIMARY matching criteria (e.g., "12\" PVC" near "IE=95.5")
- Spatial coordinates are hints, but NOT required to match exactly
- Look for clusters: IE labels are usually drawn near the pipe they describe

ELEVATION PATTERNS TO RECOGNIZE:
- Standard: "IE=95.5", "INV. 94.8", "IE 95.5", "INV 94.8"
- With direction: "INV IN=95.5", "INV OUT=94.2", "IE(IN)=95.5"
- Abbreviated: "I.E. 95.5", "EL=95.5", "ELEV 95.5"
- In tables: Row with pipe size + two elevation numbers

MATCHING LOGIC:
1. Find all IE/INV numbers in the text
2. For each pipe, look for material/diameter labels that match:
   - "pvc 12.0\"" matches "12\" PVC", "12 PVC", "12\" P.V.C.", "12 INCH PVC"
   - "concrete 15.0\"" matches "15\" CONCRETE", "15 CONC", "15\" C", "15 INCH CONCRETE"
   - Match is case-insensitive and flexible on formatting
3. IE labels near that material label (or near the pipe's coordinate area) belong to that pipe
4. Each pipe typically has TWO values: upstream (IN, higher) and downstream (OUT, lower)
5. If you find IE values but can't determine which is IN vs OUT, assign the higher value to invert_in
6. If you find only ONE IE value for a pipe, put it in invert_in (we'll assume slope downstream)
7. If multiple pipes have the same material/size, use coordinates as a tie-breaker

EXAMPLES:
- Text: "12\" PVC", "IE=95.5", "IE=94.8" → Pipe with "pvc 12.0\"" gets {in: 95.5, out: 94.8}
- Text: "15\" CONCRETE", "INV IN=96.2", "INV OUT=95.0" → Pipe with "concrete 15.0\"" gets {in: 96.2, out: 95.0}
- Text: "8\" PVC", "IE=92.5" → Pipe with "pvc 8.0\"" gets {in: 92.5, out: null}

IMPORTANT:
- Return ONLY the JSON object with no markdown, no explanation
- Every pipe in the input must appear in the output (use null if no IE found)
- Don't guess or extrapolate elevation values, but DO use flexible matching for materials
- If you see "12\" PVC" in text and a pipe has "pvc 12.0\"", that's a match - assign any nearby IE values
- Better to assign IE values to a pipe based on material match than to leave them null

Output format:
{
  "storm_pipe_0": {"invert_in": 95.5, "invert_out": 94.8},
  "storm_pipe_1": {"invert_in": 96.2, "invert_out": null},
  "storm_pipe_2": {"invert_in": null, "invert_out": null}
}"""
    
    user_prompt = f"""PIPES TO EXTRACT ELEVATIONS FOR:
{chr(10).join(pipe_summaries)}

ALL TEXT ON THE PAGE (with [x, y] coordinates):
{text_content}

TASK:
For EACH pipe listed above, find its invert elevations by:
1. Identifying the material/diameter (e.g., "pvc 12.0\"" means look for "12\" PVC" or "12 INCH PVC" in text)
2. Finding IE/INV labels near that material description
3. Extracting the numerical elevation values (e.g., from "IE=95.5" extract 95.5)
4. Assigning the higher value to invert_in, lower to invert_out

Return a JSON object with an entry for EVERY pipe (use null for pipes with no IE labels found).

Example output structure:
{{
  "storm_pipe_0": {{"invert_in": 95.5, "invert_out": 94.8}},
  "storm_pipe_1": {{"invert_in": null, "invert_out": null}}
}}"""
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.info(f"🤖 Calling LLM to extract elevations for {len(pipe_summaries)} pipes...")
            logger.info(f"📋 Sample pipes sent to LLM:\n{chr(10).join(pipe_summaries[:3])}")
            logger.info(f"📝 Sample text sent to LLM:\n{text_content[:500]}...")
            
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0,
                    "max_tokens": 2000,
                    "response_format": {"type": "json_object"}
                }
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            
            # Convert to expected format
            elevation_map = {}
            success_count = 0
            for pipe_id, elevs in parsed.items():
                invert_in = elevs.get("invert_in")
                invert_out = elevs.get("invert_out")
                elevation_map[pipe_id] = (invert_in, invert_out)
                if invert_in is not None or invert_out is not None:
                    success_count += 1
            
            logger.info(
                f"✅ LLM extracted elevations: {success_count}/{len(pipe_summaries)} pipes have IE data"
            )
            
            return elevation_map
    
    except Exception as e:
        logger.error(f"❌ LLM elevation extraction failed: {e}", exc_info=True)
        return {}


def extract_elevations_llm(
    polylines: List[Dict[str, Any]],
    text_runs: List[Dict[str, Any]],
    model: str = "gpt-4o-mini",
    timeout: int = 90
) -> Dict[str, Tuple[Optional[float], Optional[float]]]:
    """Synchronous wrapper for extract_elevations_llm_async."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context - use ThreadPoolExecutor
            with ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    extract_elevations_llm_async(polylines, text_runs, model, timeout)
                )
                return future.result(timeout=timeout + 10)
        else:
            return loop.run_until_complete(
                extract_elevations_llm_async(polylines, text_runs, model, timeout)
            )
    except Exception as e:
        logger.error(f"Failed to run async LLM elevation extraction: {e}")
        return {}

