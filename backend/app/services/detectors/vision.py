"""
Vision-based detector using GPT-4o to read PDF pages directly.

This is a pure LLM approach that bypasses Apryse vector extraction entirely.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def detect_all_networks_vision(pdf_path: str, page_num: int = 0) -> Dict[str, Any]:
    """
    Detect all utility networks using GPT-4o vision.
    
    Processes ALL pages in the PDF to capture both plan and profile views.
    
    Args:
        pdf_path: Path to PDF file
        page_num: Starting page index (0-based)
    
    Returns:
        Dict with networks: {storm: {...}, sanitary: {...}, water: {...}}
    """
    from backend.app.services.ai.vision_takeoff import extract_pipes_from_pdf_vision_multipage
    
    logger.info(f"🔍 Detecting utilities using GPT-4o vision (PDF: {pdf_path})")
    
    # Call vision LLM with all pages
    result = extract_pipes_from_pdf_vision_multipage(pdf_path, model="gpt-4o", timeout=180)
    
    if "error" in result:
        logger.error(f"Vision detection failed: {result['error']}")
        return {
            "storm": {"nodes": [], "pipes": [], "qa_flags": []},
            "sanitary": {"nodes": [], "pipes": [], "qa_flags": []},
            "water": {"nodes": [], "pipes": [], "qa_flags": []},
        }
    
    # Convert vision LLM output to our network format
    networks = {}
    
    # Storm network
    storm_pipes = _convert_vision_pipes_to_network(
        result.get("storm_pipes", []),
        discipline="storm"
    )
    networks["storm"] = {
        "nodes": [],  # TODO: extract nodes from vision
        "pipes": storm_pipes,
        "qa_flags": []
    }
    
    # Sanitary network
    sanitary_pipes = _convert_vision_pipes_to_network(
        result.get("sanitary_pipes", []),
        discipline="sanitary"
    )
    networks["sanitary"] = {
        "nodes": [],
        "pipes": sanitary_pipes,
        "qa_flags": []
    }
    
    # Water network
    water_pipes = _convert_vision_pipes_to_network(
        result.get("water_pipes", []),
        discipline="water"
    )
    networks["water"] = {
        "nodes": [],
        "pipes": water_pipes,
        "qa_flags": []
    }
    
    total_pipes = len(storm_pipes) + len(sanitary_pipes) + len(water_pipes)
    logger.info(
        f"✅ Vision detection complete: {total_pipes} total pipes "
        f"(storm={len(storm_pipes)}, sanitary={len(sanitary_pipes)}, water={len(water_pipes)})"
    )
    
    return networks


def _convert_vision_pipes_to_network(
    vision_pipes: List[Dict[str, Any]],
    discipline: str
) -> List[Dict[str, Any]]:
    """
    Convert vision LLM pipe format to our network pipe format.
    
    Args:
        vision_pipes: List of pipes from vision LLM
        discipline: Network discipline
    
    Returns:
        List of pipe dicts in our standard format
    """
    pipes = []
    
    for i, vp in enumerate(vision_pipes):
        pipe_id = vp.get("id", f"{discipline}_pipe_{i}")
        
        # Extract attributes
        length_ft = vp.get("length_ft", 0.0)
        material = vp.get("material")
        dia_in = vp.get("dia_in")
        invert_in = vp.get("invert_in")
        invert_out = vp.get("invert_out")
        ground_elev = vp.get("ground_elev")  # Read from vision LLM
        
        # Build pipe dict
        pipe = {
            "id": pipe_id,
            "discipline": discipline,
            "mat": material,
            "dia_in": dia_in,
            "length_ft": length_ft,
            "avg_depth_ft": None,
            "confidence": 0.9,  # Vision LLM is high confidence
            "reason": vp.get("notes", "Identified by GPT-4o vision"),
            "extra": {
                "start_point": vp.get("start_point"),
                "end_point": vp.get("end_point"),
                "invert_in_ft": invert_in,
                "invert_out_ft": invert_out,
                "ground_elev_ft": ground_elev,
                "source": "vision_llm"
            },
            "qa_flags": []
        }
        
        # Calculate depth if we have inverts and ground elevation
        if invert_in is not None and invert_out is not None and ground_elev is not None:
            # Average depth along the pipe run
            avg_invert = (invert_in + invert_out) / 2
            pipe["avg_depth_ft"] = ground_elev - avg_invert
            logger.info(
                f"  {pipe_id}: GL={ground_elev:.1f}, IE_avg={avg_invert:.1f}, "
                f"Depth={pipe['avg_depth_ft']:.1f}ft"
            )
        elif invert_in is not None or invert_out is not None:
            # Have inverts but no ground elevation
            pipe["qa_flags"].append({
                "code": "DEPTH_UNAVAILABLE",
                "message": "Ground elevation not found in profile view",
                "severity": "warning"
            })
        
        pipes.append(pipe)
    
    return pipes
