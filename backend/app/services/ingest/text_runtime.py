"""
Unified text extraction runtime.

Automatically routes to the configured text backend (PyMuPDF or PDFNet)
based on ESTIMAI_TEXT_BACKEND environment variable.
"""

import os
import logging
from typing import List, Any, Callable, Tuple
from .text_models import TextRun
from .pymupdf_text import extract_text_runs_pymupdf
from .pdfnet_runtime import extract_text_runs_pdfnet

logger = logging.getLogger(__name__)


def extract_text_runs(
    pdf_path: str,
    page: Any,
    page_index: int,
    to_world_xy: Callable[[float, float], Tuple[float, float]]
) -> List[TextRun]:
    """
    Extract text runs from a PDF page using the configured backend.
    
    Automatically selects PyMuPDF or PDFNet based on ESTIMAI_TEXT_BACKEND.
    
    Args:
        pdf_path: Path to PDF file
        page: PDFNet page object (used if backend is 'pdfnet', ignored otherwise)
        page_index: Page index (0-based, used if backend is 'pymupdf')
        to_world_xy: Function to convert PDF points to world feet
        
    Returns:
        List of TextRun objects with coordinates in feet
        
    Environment:
        ESTIMAI_TEXT_BACKEND: "pymupdf" (fast, real coords) or "pdfnet" (robust, estimated coords)
        
    Example:
        >>> from backend.app.services.ingest.pdfnet_runtime import get_scale_transform
        >>> feet_per_pt, to_world = get_scale_transform(doc, page)
        >>> runs = extract_text_runs(pdf_path, page, 0, to_world)
        >>> print(f"Extracted {len(runs)} text runs")
    """
    backend = os.getenv('ESTIMAI_TEXT_BACKEND', 'pdfnet').lower()
    
    if backend == 'pymupdf':
        logger.debug(f"Using PyMuPDF for text extraction (page {page_index})")
        return extract_text_runs_pymupdf(pdf_path, page_index, to_world_xy)
    else:
        logger.debug(f"Using PDFNet for text extraction (page {page_index})")
        return extract_text_runs_pdfnet(page, to_world_xy)


# Alias for backward compatibility
extract_text_runs_all = extract_text_runs


__all__ = ["extract_text_runs", "extract_text_runs_all"]

