"""
Debug endpoints for development and troubleshooting.

These endpoints are only available when ESTIMAI_DEBUG=1 is set.
"""

import os
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/debug", tags=["debug"])


def _is_debug_enabled() -> bool:
    """Check if debug mode is enabled."""
    return os.getenv("ESTIMAI_DEBUG", "0") == "1"


@router.get("/extract")
async def debug_extract(
    file_ref: str = Query(..., description="Path to PDF file"),
    max_pages: int = Query(2, ge=1, le=5, description="Max pages to extract (1-5)"),
    max_polylines: int = Query(50, ge=1, le=200, description="Max polylines per page (1-200)")
):
    """
    Debug endpoint to inspect raw extraction candidates.
    
    Returns polylines, text annotations, and legend tokens for troubleshooting.
    Only available when ESTIMAI_DEBUG=1.
    
    Args:
        file_ref: Path to PDF file (absolute or relative to artifacts)
        max_pages: Number of pages to extract (default 2)
        max_polylines: Max polylines to return per page (default 50)
        
    Returns:
        JSON with:
        - polylines: List of {id, length_ft, bbox, layer, nearby_text[:5]}
        - text_annotations: Sample of extracted text with positions
        - legend_tokens: Parsed legend from page
        - scale: Scale information
        
    Example:
        GET /v1/debug/extract?file_ref=/path/to/file.pdf&max_pages=1
    """
    # Security: Only available in debug mode
    if not _is_debug_enabled():
        raise HTTPException(
            status_code=403,
            detail="Debug endpoints disabled. Set ESTIMAI_DEBUG=1 to enable."
        )
    
    # Resolve file path
    file_path = Path(file_ref)
    if not file_path.is_absolute():
        # Try relative to artifacts
        from backend.app.core.config import settings
        file_path = Path(settings.ARTIFACT_DIR) / file_ref
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {file_ref}"
        )
    
    logger.info(f"Debug extract: {file_path} (max_pages={max_pages})")
    
    try:
        from backend.app.services.extract.apryse_vectors import VectorExtractor, ApryseUnavailable
        from backend.app.services.extract.legend_parser import parse_legend_from_text
        
        result = {
            "file": str(file_path),
            "pages": []
        }
        
        # Extract from each page
        extractor = VectorExtractor(str(file_path))
        
        for page_num in range(max_pages):
            try:
                page_data = {
                    "page_num": page_num,
                    "scale": None,
                    "legend_tokens": [],
                    "polylines": [],
                    "text_annotations": []
                }
                
                # Get scale
                try:
                    scale = extractor.load_scale(page_num=page_num)
                    page_data["scale"] = {
                        "scale_text": scale.scale_text,
                        "feet_per_inch": scale.feet_per_inch,
                        "points_per_foot": scale.points_per_foot
                    }
                except Exception as e:
                    logger.warning(f"Scale extraction failed on page {page_num}: {e}")
                    page_data["scale"] = {"error": str(e)}
                
                # Extract text and legend
                try:
                    text_annos, full_page_text = extractor.extract_text_annotations(page_num=page_num)
                    
                    # Parse legend
                    legend_tokens = parse_legend_from_text(full_page_text)
                    page_data["legend_tokens"] = legend_tokens
                    
                    # Sample text annotations (first 10)
                    for text in text_annos[:10]:
                        text_x = text.get("x", 0) if isinstance(text, dict) else getattr(text, 'x', 0)
                        text_y = text.get("y", 0) if isinstance(text, dict) else getattr(text, 'y', 0)
                        text_str = text.get("text", "") if isinstance(text, dict) else getattr(text, 'text', "")
                        
                        page_data["text_annotations"].append({
                            "text": text_str[:60],  # Truncate long text
                            "x": round(text_x, 2),
                            "y": round(text_y, 2)
                        })
                    
                    page_data["text_annotations_total"] = len(text_annos)
                    page_data["full_text_length"] = len(full_page_text)
                    
                except Exception as e:
                    logger.warning(f"Text extraction failed on page {page_num}: {e}")
                    page_data["text_error"] = str(e)
                
                # Extract polylines (try all common layer hints)
                all_layer_hints = [
                    # Storm
                    "STORM", "SD", "STORM SEWER", "STORM DRAIN", "C-STRM",
                    # Sanitary
                    "SANITARY", "SAN", "SEWER", "SANITARY SEWER", "C-SAN",
                    # Water
                    "WATER", "WM", "WATER MAIN", "DOMESTIC WATER", "C-WAT"
                ]
                
                try:
                    polylines = extractor.extract_layer_lines(all_layer_hints, page_num=page_num)
                    logger.info(f"Page {page_num}: extracted {len(polylines)} polylines")
                    
                    # Helper to find nearby text
                    def _find_nearby_text(polyline, all_texts, search_radius_ft=10.0):
                        bbox = polyline.bbox
                        expanded_bbox = (
                            bbox[0] - search_radius_ft,
                            bbox[1] - search_radius_ft,
                            bbox[2] + search_radius_ft,
                            bbox[3] + search_radius_ft
                        )
                        
                        nearby = []
                        for text in all_texts:
                            text_x = text.get("x", 0) if isinstance(text, dict) else getattr(text, 'x', 0)
                            text_y = text.get("y", 0) if isinstance(text, dict) else getattr(text, 'y', 0)
                            
                            if (expanded_bbox[0] <= text_x <= expanded_bbox[2] and
                                expanded_bbox[1] <= text_y <= expanded_bbox[3]):
                                text_str = text.get("text", "") if isinstance(text, dict) else getattr(text, 'text', "")
                                if text_str:
                                    nearby.append(text_str)
                        
                        return nearby[:5]  # Return first 5
                    
                    # Process polylines
                    for i, polyline in enumerate(polylines[:max_polylines]):
                        nearby_text = _find_nearby_text(polyline, text_annos) if text_annos else []
                        
                        polyline_data = {
                            "id": polyline.id,
                            "length_ft": round(polyline.length_ft, 2),
                            "bbox": [round(x, 2) for x in polyline.bbox],
                            "layer": polyline.layer or "None",
                            "nearby_text": nearby_text,
                            "legend_context": legend_tokens[:3]  # Show legend for context
                        }
                        
                        page_data["polylines"].append(polyline_data)
                    
                    page_data["polylines_total"] = len(polylines)
                    
                except Exception as e:
                    logger.warning(f"Polyline extraction failed on page {page_num}: {e}")
                    page_data["polyline_error"] = str(e)
                
                result["pages"].append(page_data)
                
            except Exception as e:
                logger.error(f"Page {page_num} extraction failed: {e}")
                result["pages"].append({
                    "page_num": page_num,
                    "error": str(e)
                })
        
        return result
        
    except ApryseUnavailable as e:
        raise HTTPException(
            status_code=503,
            detail=f"Apryse PDFNet not available: {e}"
        )
    except Exception as e:
        logger.error(f"Debug extract failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}"
        )


@router.get("/health")
async def debug_health():
    """
    Debug health check.
    
    Returns system info and debug status.
    """
    if not _is_debug_enabled():
        raise HTTPException(
            status_code=403,
            detail="Debug endpoints disabled. Set ESTIMAI_DEBUG=1 to enable."
        )
    
    return {
        "debug_enabled": True,
        "apryse_enabled": os.getenv("APR_USE_APRYSE", "0") == "1",
        "demo_mode": os.getenv("ESTIMAI_USE_DEMO", "0") == "1",
        "min_confidence": float(os.getenv("ESTIMAI_PIPE_MIN_CONF", "0.35")),
        "env_vars": {
            k: v for k, v in os.environ.items()
            if k.startswith("ESTIMAI_") or k.startswith("APR_")
        }
    }


__all__ = ["router"]

