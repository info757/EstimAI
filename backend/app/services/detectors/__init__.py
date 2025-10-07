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
    1. Detects utility networks using Apryse+LLM pipeline
    2. Optionally builds surface sampler for depth calculations
    3. Returns JSON-serializable data structure
    
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
    from pydantic import BaseModel
    
    logger = logging.getLogger(__name__)
    logger.info(f"Running extract pipeline on: {file_ref}")
    
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
    except Exception as e:
        logger.error(f"Network detection failed: {e}", exc_info=True)
        # Return empty networks but don't fail completely
        storm_result = {"nodes": [], "pipes": [], "qa_flags": []}
        sanitary_result = {"nodes": [], "pipes": [], "qa_flags": []}
        water_result = {"nodes": [], "pipes": [], "qa_flags": []}
    
    # Step 3: Build response with JSON-serializable data
    networks = {}
    
    if storm_result and storm_result.get("pipes"):
        networks['storm'] = _to_primitive(storm_result)
    
    if sanitary_result and sanitary_result.get("pipes"):
        networks['sanitary'] = _to_primitive(sanitary_result)
    
    if water_result and water_result.get("pipes"):
        networks['water'] = _to_primitive(water_result)
    
    # Log final counts
    total_pipes = sum(len(net.get('pipes', [])) for net in networks.values())
    logger.info(f"Extract complete: {total_pipes} total pipes across {len(networks)} networks")
    
    return {
        'networks': networks,
        'surface': _to_primitive(surface) if surface else None
    }