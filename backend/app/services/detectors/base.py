"""Base detector interface and types."""
from dataclasses import dataclass
from typing import Protocol, List
import numpy as np


@dataclass
class Detection:
    """Represents a single detection result."""
    type: str
    x_px: float
    y_px: float
    confidence: float


class Detector(Protocol):
    """Plugin contract for detection implementations."""
    
    def detect(self, img: np.ndarray) -> List[Detection]:
        """
        Detect objects in an image.
        
        Args:
            img: Input image as numpy array (RGB format)
            
        Returns:
            List of Detection objects
        """
        ...
