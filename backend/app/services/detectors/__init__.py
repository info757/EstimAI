"""Detector registry and factory functions."""
from typing import Protocol
from pathlib import Path
from .base import Detection
from .opencv_template import OpenCVTemplateDetector
from ...core.config import settings


class Detector(Protocol):
    """Plugin contract for detection implementations."""
    
    def detect(self, img) -> list[Detection]:
        """Detect objects in an image."""
        ...


def get_detector(name: str = None) -> Detector:
    """
    Get a detector instance by name.
    
    Args:
        name: Detector name ("opencv_template" supported)
               If None, uses settings.DETECTOR_IMPL
        
    Returns:
        Detector instance
        
    Raises:
        ValueError: If detector name is not supported
    """
    if name is None:
        name = settings.DETECTOR_IMPL
    
    if name == "opencv_template":
        templates_dir = settings.get_templates_dir()
        return OpenCVTemplateDetector(templates_dir)
    else:
        raise ValueError(f"Unsupported detector: {name}")


def list_available_detectors() -> list[str]:
    """
    List all available detector implementations.
    
    Returns:
        List of detector names
    """
    return ["opencv_template"]


def create_detector(name: str = None, **kwargs) -> Detector:
    """
    Create a detector instance with optional parameters.
    
    Args:
        name: Detector name
        **kwargs: Additional parameters for detector initialization
        
    Returns:
        Detector instance
    """
    if name is None:
        name = settings.DETECTOR_IMPL
    
    if name == "opencv_template":
        templates_dir = kwargs.get('templates_dir', settings.get_templates_dir())
        return OpenCVTemplateDetector(Path(templates_dir))
    else:
        raise ValueError(f"Unsupported detector: {name}")