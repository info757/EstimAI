"""
PDF content extraction utilities.

This module provides functions to extract vectors, text, and other elements
from PDF pages.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import math


@dataclass
class VectorEl:
    """Vector element from PDF."""
    type: str
    x1: float
    y1: float
    x2: float
    y2: float
    attrs: Dict[str, Any] = None


@dataclass
class TextEl:
    """Text element from PDF."""
    text: str
    x: float
    y: float
    attrs: Dict[str, Any] = None


def extract_vectors(page: Any) -> List[Dict[str, Any]]:
    """
    Extract vector elements from a PDF page.
    For mock implementation, returns sample vectors.
    """
    # Mock implementation - in real version this would use Apryse
    mock_vectors = [
        {
            "type": "line",
            "x1": 100, "y1": 100,
            "x2": 200, "y2": 200,
            "attrs": {"stroke_width": 1.0}
        },
        {
            "type": "line", 
            "x1": 150, "y1": 150,
            "x2": 250, "y2": 250,
            "attrs": {"stroke_width": 2.0}
        },
        {
            "type": "circle",
            "x1": 300, "y1": 300,
            "x2": 350, "y2": 350,
            "attrs": {"radius": 25.0}
        }
    ]
    
    return mock_vectors


def extract_text(page: Any) -> List[Dict[str, Any]]:
    """
    Extract text elements from a PDF page.
    For mock implementation, returns sample text.
    """
    # Mock implementation - in real version this would use Apryse
    mock_texts = [
        {
            "text": "STORM SEWER",
            "x": 100, "y": 100,
            "attrs": {"font_size": 12.0}
        },
        {
            "text": "1\" = 50'",
            "x": 200, "y": 200,
            "attrs": {"font_size": 10.0}
        },
        {
            "text": "MANHOLE",
            "x": 300, "y": 300,
            "attrs": {"font_size": 11.0}
        }
    ]
    
    return mock_texts
