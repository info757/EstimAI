from __future__ import annotations
from typing import Optional, Any
from backend.app.core.config import settings

def init_depth_config(base_dir: str = "config") -> None:
    """Initialize depth calculation configuration."""
    from .depth import init_depth_config as _init_depth_config
    _init_depth_config(base_dir)

def get_detector(name: str):
    if name == "vision_llm":
        from .vision_llm import VisionLLMDetector  # lazy import
        return VisionLLMDetector(
            model=settings.VISION_MODEL,
            tile_px=settings.TILE_PX,
            overlap_px=settings.TILE_OVERLAP_PX,
        )
    if name == "opencv_template":
        from .opencv_template import OpenCVTemplateDetector  # lazy import
        return OpenCVTemplateDetector(getattr(settings, "TEMPLATES_DIR", None))
    # default to vision to avoid importing cv2 unintentionally
    from .vision_llm import VisionLLMDetector
    return VisionLLMDetector(
        model=settings.VISION_MODEL,
        tile_px=settings.TILE_PX,
        overlap_px=settings.TILE_OVERLAP_PX,
    )

def run_extract(file_ref: str, max_pages: Optional[int] = None) -> Any:
    """
    Canonical extract entrypoint used by the agent.
    
    This function provides a stable interface that:
    1. Detects utility networks using VISION LLM (GPT-4o) or Apryse+LLM pipeline
    2. Optionally builds surface sampler for depth calculations
    3. Returns JSON-serializable data structure
    
    Feature flags:
    - ESTIMAI_USE_VISION=1: Use pure GPT-4o vision (no Apryse)
    - ESTIMAI_USE_VISION=0: Use Apryse vector extraction + LLM classification (default)
    
    Args:
        file_ref: Path to the PDF file to extract from
        max_pages: Optional maximum number of pages to process
        
    Returns:
        Dictionary with:
        - networks: {'storm': {...}, 'sanitary': {...}, 'water': {...}}
        - surface: Optional surface sampler (for depth calculations)
        
    Example:
        result = run_extract("plans.pdf")
        storm_pipes = result['networks']['storm']['pipes']
        for pipe in storm_pipes:
            print(f"{pipe['id']}: {pipe['length_ft']} ft")
    """
    import logging
    import enum
    import os
    from pydantic import BaseModel
    
    logger = logging.getLogger(__name__)
    logger.info(f"Running extract pipeline on: {file_ref}")
    
    # Check if using vision-only mode
    use_vision = os.getenv("ESTIMAI_USE_VISION", "0") == "1"
    
    if use_vision:
        logger.info("🔍 Using GPT-4o VISION mode (bypassing Apryse)")
        from .vision import detect_all_networks_vision
        networks = detect_all_networks_vision(file_ref, page_num=0)
        return {
            "networks": networks,
            "surface": None
        }
    
    # Default: Use Apryse vector extraction + LLM classification
    logger.info("🔍 Using Apryse + LLM classification mode")
    
    # Import network detection functions
    from .storm import detect_storm_network
    from .sanitary import detect_sanitary_network
    from .water import detect_water_network
    
    # Helper to make objects JSON-serializable
    def _to_primitive(x):
        """Convert Pydantic models, enums, sets to JSON-serializable types."""
        if isinstance(x, BaseModel):
            return x.model_dump(mode='json')
        if isinstance(x, enum.Enum):
            return x.value
        if isinstance(x, set):
            return list(x)
        if isinstance(x, dict):
            return {k: _to_primitive(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [_to_primitive(item) for item in x]
        return x
    
    # Step 1: Try to build optional surface sampler (best-effort)
    surface = None
    try:
        from .earthwork_surface import build_surface_sampler
        surface = build_surface_sampler(file_ref=file_ref, max_pages=max_pages)
        logger.info("Surface sampler built successfully")
    except ImportError:
        logger.debug("earthwork_surface module not available")
    except Exception as e:
        logger.warning(f"Surface sampler build failed: {e}")
    
    # Step 2: Detect networks using Apryse+LLM pipeline
    # Note: detect_*_network functions now expect pdf_path parameter
    try:
        storm_result = detect_storm_network([], [], pdf_path=file_ref)
        sanitary_result = detect_sanitary_network([], [], pdf_path=file_ref)
        water_result = detect_water_network([], [], pdf_path=file_ref)
        
        logger.info(
            f"Network detection complete: "
            f"storm={len(storm_result.get('pipes', []))} pipes, "
            f"sanitary={len(sanitary_result.get('pipes', []))} pipes, "
            f"water={len(water_result.get('pipes', []))} pipes"
        )
        
        # Step 2.5: Collect unknowns (pipes that weren't classified into any network)
        from .unknown import collect_unknowns, merge_unknowns_into_response
        
        # Combine all detections and classified IDs
        all_detections_combined = []
        classified_ids_combined = set()
        
        for network_name, result in [("storm", storm_result), ("sanitary", sanitary_result), ("water", water_result)]:
            all_detections = result.get("all_detections", [])
            classified_ids = result.get("classified_ids", set())
            
            logger.info(
                f"📊 {network_name}: {len(all_detections)} total detections, "
                f"{len(classified_ids)} classified into this network"
            )
            
            # Only add detections once (from first network that saw them)
            for det in all_detections:
                if det.polyline_id not in {d.polyline_id for d in all_detections_combined}:
                    all_detections_combined.append(det)
            
            classified_ids_combined.update(classified_ids)
        
        # Collect unknowns (not classified into any network)
        unknown_result = collect_unknowns(all_detections_combined, classified_ids_combined)
        
        logger.info(
            f"Classification summary: "
            f"{len(classified_ids_combined)} classified, "
            f"{len(unknown_result.get('pipes', []))} unknown (routed to HITL)"
        )
        
    except Exception as e:
        logger.error(f"Network detection failed: {e}", exc_info=True)
        # Return empty networks but don't fail completely
        storm_result = {"nodes": [], "pipes": [], "qa_flags": []}
        sanitary_result = {"nodes": [], "pipes": [], "qa_flags": []}
        water_result = {"nodes": [], "pipes": [], "qa_flags": []}
        unknown_result = {"nodes": [], "pipes": [], "qa_flags": []}
    
    # Step 3: Build response with JSON-serializable data
    networks = {}
    
    if storm_result and storm_result.get("pipes"):
        # Remove internal fields before sending to client
        storm_clean = {k: v for k, v in storm_result.items() if k not in ["all_detections", "classified_ids"]}
        networks['storm'] = _to_primitive(storm_clean)
    
    if sanitary_result and sanitary_result.get("pipes"):
        sanitary_clean = {k: v for k, v in sanitary_result.items() if k not in ["all_detections", "classified_ids"]}
        networks['sanitary'] = _to_primitive(sanitary_clean)
    
    if water_result and water_result.get("pipes"):
        water_clean = {k: v for k, v in water_result.items() if k not in ["all_detections", "classified_ids"]}
        networks['water'] = _to_primitive(water_clean)
    
    # Add unknown network if we have unclassified pipes
    if unknown_result and unknown_result.get("pipes"):
        networks['unknown'] = _to_primitive(unknown_result)
        logger.warning(
            f"⚠️ 'unknown' network added with {len(unknown_result['pipes'])} pipes - "
            f"requires HITL review before approval"
        )
    
    # Log final counts
    total_pipes = sum(len(net.get('pipes', [])) for net in networks.values())
    classified_pipes = sum(len(net.get('pipes', [])) for k, net in networks.items() if k != 'unknown')
    unknown_pipes = len(networks.get('unknown', {}).get('pipes', []))
    
    logger.info(
        f"Extract complete: {total_pipes} total pipes across {len(networks)} networks "
        f"({classified_pipes} classified, {unknown_pipes} unknown)"
    )
    
    return {
        'networks': networks,
        'surface': _to_primitive(surface) if surface else None
    }