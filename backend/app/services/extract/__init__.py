"""
Vector extraction services for PDF processing.

This module provides high-level interfaces for extracting vector geometry,
text annotations, and scale information from construction plan PDFs.
"""
from .apryse_vectors import (
    VectorExtractor,
    Polyline,
    TextAnno,
    ScaleInfo,
    ApryseUnavailable,
    create_extractor,
    extract_all
)

__all__ = [
    "VectorExtractor",
    "Polyline",
    "TextAnno",
    "ScaleInfo",
    "ApryseUnavailable",
    "create_extractor",
    "extract_all",
]

