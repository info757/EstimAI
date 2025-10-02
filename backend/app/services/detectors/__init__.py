from app.core.config import settings

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