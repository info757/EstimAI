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