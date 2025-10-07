"""
Input canonicalization for deterministic LLM calls.

Ensures that identical geometry produces identical JSON bundles,
which in turn produce identical content hashes and LLM responses.
"""
import hashlib
import json
import math
from typing import Any, Dict, List


def stable_poly_id(vertices: List[List[float]]) -> str:
    """
    Generate stable polyline ID from quantized vertices.
    
    Quantization ensures tiny OCR jitter doesn't change the ID.
    """
    # Quantize vertices to 3 decimals
    q = [[round(x, 3), round(y, 3)] for x, y in vertices]
    h = hashlib.sha1(json.dumps(q, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()[:12]
    return f"P{h}"


def sanitize_number(x: Any) -> Any:
    """
    Sanitize numeric values: quantize floats, convert NaN/Infinity to None.
    
    Returns:
        - None for null/NaN/Infinity
        - Quantized float (3 decimals) for valid floats
        - Original int for integers
    """
    if x is None:
        return None
    if isinstance(x, float) and math.isfinite(x):
        return round(x, 3)
    if isinstance(x, int):
        return x
    return None  # Drop weirds like 'nan' strings


def canonicalize_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Canonicalize a detection bundle for deterministic hashing.
    
    Transformations:
    - Stable poly IDs from vertex hash (not random UUIDs)
    - Quantized floats (3 decimals, no NaN/Infinity)
    - Clamped ranges (e.g., alongness ∈ [-1, 1])
    - Stable sorting (by ID)
    - Explicit nulls (never undefined)
    
    Args:
        bundle: Detection bundle with polylines, labels, nodes
        
    Returns:
        Canonicalized bundle ready for hashing
    """
    # Ensure poly IDs are stable
    for p in bundle.get("polylines", []):
        if not p.get("id"):
            p["id"] = stable_poly_id(p.get("vertices", []))
        
        # Sanitize numeric fields
        p["length_ft"] = sanitize_number(p.get("length_ft"))
        
        # Sanitize style
        style = p.get("style", {})
        style["width"] = sanitize_number(style.get("width"))
        if "stroke_rgb" in style and isinstance(style["stroke_rgb"], list):
            style["stroke_rgb"] = [sanitize_number(c) for c in style["stroke_rgb"]]
        p["style"] = style
        
        # Sanitize nearest labels
        for nl in p.get("nearest_labels", []):
            nl["dist_ft"] = sanitize_number(nl.get("dist_ft"))
            a = nl.get("alongness")
            # Clamp alongness to [-1, 1] or None
            nl["alongness"] = None if a is None else max(-1, min(1, round(a, 3)))
        
        # Sanitize nearest nodes
        for nn in p.get("nearest_nodes", []):
            nn["dist_ft"] = sanitize_number(nn.get("dist_ft"))
    
    # Stable sort top-level arrays
    bundle["polylines"] = sorted(bundle.get("polylines", []), key=lambda x: x.get("id", ""))
    bundle["labels"] = sorted(bundle.get("labels", []), key=lambda x: x.get("id", ""))
    bundle["nodes"] = sorted(bundle.get("nodes", []), key=lambda x: x.get("id", ""))
    
    # Ensure legend key exists (explicit null is better than omission)
    if "legend_ontology" not in bundle:
        bundle["legend_ontology"] = None
    
    return bundle


def content_hash(payload: Dict[str, Any]) -> str:
    """
    Create stable content hash from canonicalized payload.
    
    Uses:
    - Sorted keys
    - Compact separators
    - ensure_ascii=False for unicode stability
    
    Returns:
        SHA256 hash (hex, 64 chars)
    """
    s = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(s.encode()).hexdigest()

