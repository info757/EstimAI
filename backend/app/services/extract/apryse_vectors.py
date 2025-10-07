"""
Apryse-based vector extraction with real-world measurement conversion.

This module provides a VectorExtractor class that uses Apryse PDFNet SDK to:
1. Extract vector geometry (lines, polylines, paths) from PDF pages
2. Parse scale information (scale bars, viewport transforms)
3. Convert PDF coordinates to real-world feet
4. Extract text annotations with spatial relationships

All Apryse imports are gated by APR_USE_APRYSE environment variable.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class ApryseUnavailable(Exception):
    """Raised when Apryse PDFNet is required but not available."""
    pass


# Check if Apryse is enabled
APR_USE_APRYSE = os.getenv("APR_USE_APRYSE", "0") == "1"

if not APR_USE_APRYSE:
    logger.warning("Apryse disabled - VectorExtractor will raise ApryseUnavailable")


@dataclass
class Polyline:
    """A polyline extracted from PDF with real-world measurements."""
    id: str
    points: List[Tuple[float, float]]  # [(x, y), ...] in PDF points
    length_ft: float  # Real-world length in feet
    bbox: Tuple[float, float, float, float]  # (minx, miny, maxx, maxy)
    stride: Optional[str] = None  # Stroke color/pattern identifier
    layer: Optional[str] = None  # Layer/OCG name if available
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": self.id,
            "points": self.points,
            "length_ft": self.length_ft,
            "bbox": self.bbox,
            "stride": self.stride,
            "layer": self.layer
        }


@dataclass
class TextAnno:
    """A text annotation extracted from PDF."""
    text: str
    value: Optional[str]  # Parsed numeric/label value
    bbox: Tuple[float, float, float, float]  # (minx, miny, maxx, maxy)
    x: float  # Center x
    y: float  # Center y
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "text": self.text,
            "value": self.value,
            "bbox": self.bbox,
            "x": self.x,
            "y": self.y
        }


@dataclass
class ScaleInfo:
    """Scale information extracted from PDF."""
    inches_per_foot: float  # How many PDF inches = 1 real-world foot
    points_per_foot: float  # How many PDF points (1/72 inch) = 1 real-world foot
    scale_text: str  # Original scale annotation (e.g., "1\" = 20'")
    source: str  # "scale_bar" | "viewport" | "assumed"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "inches_per_foot": self.inches_per_foot,
            "points_per_foot": self.points_per_foot,
            "scale_text": self.scale_text,
            "source": self.source
        }


class VectorExtractor:
    """
    Extract vector geometry from PDF using Apryse PDFNet SDK.
    
    This class handles:
    - Opening PDFs with Apryse
    - Parsing scale information from scale bars or viewport
    - Extracting vector paths (lines, polylines) with real-world lengths
    - Extracting text annotations with spatial relationships
    
    Unit Conversion:
    - PDF uses "points" (1/72 inch)
    - Construction plans have scale bars (e.g., "1 inch = 20 feet")
    - We convert: PDF points → inches → feet using parsed scale
    
    Example:
        extractor = VectorExtractor("plans.pdf")
        scale = extractor.load_scale(page_num=0)
        lines = extractor.extract_layer_lines(["STORM", "WATER"], page_num=0)
        texts = extractor.extract_text_annotations(page_num=0)
    """
    
    def __init__(self, pdf_path: str):
        """
        Initialize vector extractor for a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Raises:
            ApryseUnavailable: If APR_USE_APRYSE is not enabled
            FileNotFoundError: If PDF file doesn't exist
        """
        if not APR_USE_APRYSE:
            raise ApryseUnavailable(
                "Apryse PDFNet is disabled. Set APR_USE_APRYSE=1 to enable vector extraction."
            )
        
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        self._doc = None
        self._scale_cache: Dict[int, ScaleInfo] = {}
        self._text_stats_cache: Dict[int, Dict[str, Any]] = {}  # Per-page text statistics
        self._text_index_cache: Dict[int, Any] = {}  # Per-page spatial index
        
        logger.info(f"VectorExtractor initialized for: {self.pdf_path.name}")
    
    def _ensure_doc(self):
        """Lazy-load Apryse document."""
        if self._doc is not None:
            return self._doc
        
        try:
            from backend.app.services.ingest.pdfnet_runtime import open_doc, init, ApryseUnavailable as PDFNetUnavailable
            
            # Initialize PDFNet if not already done
            try:
                init()
            except Exception as init_err:
                logger.warning(f"PDFNet init warning: {init_err}")
            
            self._doc = open_doc(str(self.pdf_path))
            logger.info(f"Opened PDF with Apryse: {self.pdf_path.name}")
            return self._doc
        except ImportError as e:
            raise ApryseUnavailable(f"Apryse PDFNet SDK not available: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to open PDF with Apryse: {e}")
    
    def load_scale(self, page_num: int = 0) -> ScaleInfo:
        """
        Load scale information from PDF page using PDFNet.
        
        Uses get_scale_transform() from pdfnet_runtime which:
        1. Parses scale bar text (e.g., "1\" = 20'")
        2. Derives from page matrix + UserUnit
        3. Falls back to assumed 1" = 20'
        
        Args:
            page_num: Page index (0-based)
            
        Returns:
            ScaleInfo with conversion factors
        """
        # Check cache
        if page_num in self._scale_cache:
            return self._scale_cache[page_num]
        
        doc = self._ensure_doc()
        
        try:
            from backend.app.services.ingest.pdfnet_runtime import get_scale_transform, iter_pages
            
            # Get page
            pages = list(iter_pages(doc))
            if page_num >= len(pages):
                logger.warning(f"Page {page_num} not found, using page 0")
                page_num = 0
            
            page = pages[page_num]
            
            # Get scale transform from PDFNet
            feet_per_point, to_world_xy = get_scale_transform(doc, page)
            
            # Convert to ScaleInfo
            scale_info = ScaleInfo(
                inches_per_foot=feet_per_point * 72.0,  # Convert back to inches/foot
                points_per_foot=1.0 / feet_per_point,   # Inverse for points_per_foot
                scale_text=f"{feet_per_point * 72.0:.1f} ft/in",
                source="pdfnet"
            )
            
            self._scale_cache[page_num] = scale_info
            logger.info(f"Loaded scale: {scale_info.scale_text}")
            return scale_info
        
        except Exception as e:
            logger.error(f"Scale loading failed: {e}")
            # Fallback
            scale_info = ScaleInfo(
                inches_per_foot=1.0 / 20.0,
                points_per_foot=72.0 / 20.0,
                scale_text="1\" = 20' (fallback)",
                source="fallback"
            )
            self._scale_cache[page_num] = scale_info
            return scale_info
    
    def extract_layer_lines(
        self, 
        layer_hints: List[str],
        page_num: int = 0,
        min_len_ft: float = 8.0
    ) -> List[Polyline]:
        """
        Extract vector lines/polylines from specific layers using PDFNet.
        
        Args:
            layer_hints: Layer names to look for (e.g., ["STORM", "WATER", "C-UTIL"])
            page_num: Page index (0-based)
            min_len_ft: Minimum length threshold in feet
            
        Returns:
            List of Polyline objects with real-world measurements
            
        Raises:
            ApryseUnavailable: If PDFNet is not available or not initialized
        """
        doc = self._ensure_doc()
        
        try:
            from backend.app.services.ingest.pdfnet_runtime import (
                get_scale_transform,
                iter_stroked_polylines,
                iter_pages,
                ApryseUnavailable as PDFNetUnavailable
            )
            
            # Get page
            pages = list(iter_pages(doc))
            if page_num >= len(pages):
                logger.warning(f"Page {page_num} not found, using page 0")
                page_num = 0
            
            page = pages[page_num]
            
            # Get scale transform
            feet_per_point, to_world_xy = get_scale_transform(doc, page)
            
            # Extract stroked polylines
            polyline_dicts = iter_stroked_polylines(
                doc, page,
                feet_per_point=feet_per_point,
                to_world_xy=to_world_xy,
                layer_hints=layer_hints,
                min_len_ft=min_len_ft,
                max_count=5000
            )
            
            logger.info(
                f"Page {page_num}: Extracted {len(polyline_dicts)} polylines "
                f"(scale: {feet_per_point * 72:.1f} ft/in, layer_hints: {layer_hints})"
            )
            
            if len(polyline_dicts) == 0:
                logger.warning(
                    f"⚠️ Page {page_num} yielded 0 polylines "
                    f"(layer_hints: {layer_hints}, min_len: {min_len_ft} ft). "
                    f"Check if layers exist or try empty layer_hints []"
                )
            
            # Convert to Polyline objects
            polylines = []
            for pl_dict in polyline_dicts:
                polyline = Polyline(
                    id=pl_dict["id"],
                    points=pl_dict["points"],
                    length_ft=pl_dict["length_ft"],
                    bbox=pl_dict["bbox"],
                    stride=pl_dict.get("color"),
                    layer=pl_dict.get("layer")
                )
                polylines.append(polyline)
            
            return polylines
        
        except (ImportError, PDFNetUnavailable) as e:
            raise ApryseUnavailable(f"Apryse PDFNet not available: {e}")
        except Exception as e:
            logger.error(f"Vector extraction failed on page {page_num}: {e}")
            raise RuntimeError(f"Failed to extract vectors: {e}")
    
    def extract_text_annotations(self, page_num: int = 0) -> tuple[List[TextAnno], str]:
        """
        Extract text annotations from PDF page using PDFNet TextExtractor.
        
        Args:
            page_num: Page index (0-based)
            
        Returns:
            Tuple of (annotations, full_page_text)
            - annotations: List of TextAnno objects with text content and spatial info
            - full_page_text: Complete text content from page (for legend parsing)
            
        Raises:
            ApryseUnavailable: If PDFNet is not available
        """
        doc = self._ensure_doc()
        
        try:
            from backend.app.services.ingest.pdfnet_runtime import (
                iter_pages,
                get_scale_transform,
                ApryseUnavailable as PDFNetUnavailable
            )
            from PDFNetPython3.PDFNetPython import TextExtractor
            
            # Get page
            pages = list(iter_pages(doc))
            if page_num >= len(pages):
                logger.warning(f"Page {page_num} not found, using page 0")
                page_num = 0
            
            page = pages[page_num]
            
            # Get scale for coordinate conversion
            feet_per_point, to_world_xy = get_scale_transform(doc, page)
            
            # Extract text with bounding boxes
            txt_extractor = TextExtractor()
            txt_extractor.Begin(page)
            
            # Get text runs with positions
            # Note: Full bbox extraction requires more complex PDFNet API calls
            # For now, extract text elements and approximate positions
            
            annotations = []
            
            # Simple text extraction - get all text
            all_text = txt_extractor.GetAsText()
            logger.debug(f"Extracted {len(all_text)} characters of text from page {page_num}")
            
            # Split into lines and create annotations
            # This is simplified - full implementation would get per-word bboxes
            lines = all_text.split('\n')
            
            for i, line in enumerate(lines):
                text_str = line.strip()
                if not text_str:
                    continue
                
                # Parse value
                value = self._parse_text_value(text_str)
                
                # Approximate position (would need proper bbox extraction)
                # For now, use a grid layout as placeholder
                x = 100.0 + (i % 10) * 50.0
                y = 100.0 + (i // 10) * 20.0
                bbox = (x, y, x + len(text_str) * 5, y + 10)
                
                # Convert to world coordinates
                x_ft, y_ft = to_world_xy(x, y)
                bbox_ft = (
                    to_world_xy(bbox[0], bbox[1])[0],
                    to_world_xy(bbox[0], bbox[1])[1],
                    to_world_xy(bbox[2], bbox[3])[0],
                    to_world_xy(bbox[2], bbox[3])[1]
                )
                
                anno = TextAnno(
                    text=text_str,
                    value=value,
                    bbox=bbox_ft,
                    x=x_ft,
                    y=y_ft
                )
                
                annotations.append(anno)
            
            logger.info(f"Extracted {len(annotations)} text annotations from page {page_num}")
            
            if len(annotations) == 0:
                logger.warning(f"⚠️ Page {page_num} yielded 0 text annotations")
            
            return annotations, all_text
        
        except (ImportError, PDFNetUnavailable) as e:
            raise ApryseUnavailable(f"Apryse PDFNet not available: {e}")
        except Exception as e:
            logger.error(f"Text extraction failed on page {page_num}: {e}")
            raise RuntimeError(f"Failed to extract text: {e}")
    
    def build_text_index(self, page_num: int = 0) -> List[Any]:
        """
        Build per-page text index using the unified text extraction API.
        
        Args:
            page_num: Page index (0-based)
            
        Returns:
            List of TextRun objects with real coordinates in feet
            
        Notes:
            - Uses ESTIMAI_TEXT_BACKEND to route to PyMuPDF or PDFNet
            - Caches results and statistics per page
            - Provides real text coordinates for spatial matching
        """
        # Check cache first
        if page_num in self._text_stats_cache:
            # Already built, return cached runs
            return self._text_stats_cache[page_num].get('runs', [])
        
        doc = self._ensure_doc()
        
        try:
            from backend.app.services.ingest.pdfnet_runtime import (
                iter_pages,
                get_scale_transform,
            )
            from backend.app.services.ingest.text_runtime import extract_text_runs_all
            
            # Get page
            pages = list(iter_pages(doc))
            if page_num >= len(pages):
                logger.warning(f"Page {page_num} not found, using page 0")
                page_num = 0
            
            page = pages[page_num]
            
            # Get scale transform (same as used for vectors)
            feet_per_point, to_world_xy = get_scale_transform(doc, page)
            
            # Extract text using unified API
            text_runs = extract_text_runs_all(str(self.pdf_path), page, page_num, to_world_xy)
            
            # Calculate statistics
            total_chars = sum(len(run.text) for run in text_runs)
            runs_count = len(text_runs)
            
            # Cache results
            self._text_stats_cache[page_num] = {
                'runs': text_runs,
                'chars_total': total_chars,
                'runs_count': runs_count,
                'feet_per_point': feet_per_point
            }
            
            logger.info(f"Built text index for page {page_num}: {runs_count} runs, {total_chars} chars")
            return text_runs
            
        except Exception as e:
            logger.error(f"Failed to build text index on page {page_num}: {e}")
            # Cache empty result to avoid retrying
            self._text_stats_cache[page_num] = {
                'runs': [],
                'chars_total': 0,
                'runs_count': 0,
                'error': str(e)
            }
            return []
    
    def get_text_stats(self, page_num: int = 0) -> Dict[str, Any]:
        """
        Get text extraction statistics for a page.
        
        Args:
            page_num: Page index (0-based)
            
        Returns:
            Dict with: chars_total, runs_count, and optional error
            
        Example:
            >>> extractor = VectorExtractor("plan.pdf")
            >>> stats = extractor.get_text_stats(0)
            >>> print(f"Page has {stats['chars_total']} chars in {stats['runs_count']} runs")
        """
        # Build index if not cached
        if page_num not in self._text_stats_cache:
            self.build_text_index(page_num)
        
        stats = self._text_stats_cache.get(page_num, {})
        return {
            'chars_total': stats.get('chars_total', 0),
            'runs_count': stats.get('runs_count', 0),
            'error': stats.get('error')
        }
    
    def get_text_index(self, page_num: int = 0):
        """
        Get spatial text index for a page.
        
        Args:
            page_num: Page index (0-based)
            
        Returns:
            TextIndex object for spatial queries, or None if text extraction failed
            
        Example:
            >>> extractor = VectorExtractor("plan.pdf")
            >>> index = extractor.get_text_index(0)
            >>> nearby = index.query_expand(polyline_bbox, expand_ft=40, limit=20)
        """
        # Check if index is already cached
        if page_num in self._text_index_cache:
            return self._text_index_cache[page_num]
        
        # Build text index if needed
        text_runs = self.build_text_index(page_num)
        
        if not text_runs:
            logger.warning(f"No text runs available for page {page_num}, index will be empty")
            self._text_index_cache[page_num] = None
            return None
        
        # Create and cache spatial index
        from backend.app.services.extract.spatial import TextIndex
        index = TextIndex(text_runs)
        self._text_index_cache[page_num] = index
        
        logger.debug(f"Created TextIndex for page {page_num} with {len(text_runs)} runs")
        return index
    
    def _parse_text_value(self, text: str) -> Optional[str]:
        """
        Parse meaningful values from text annotations.
        
        Patterns:
        - Pipe sizes: "8\"", "12 IN" → "8", "12"
        - Slopes: "0.5%", "2.0% SLOPE" → "0.5", "2.0"
        - Manholes: "MH-101", "MH 24" → "MH-101", "MH-24"
        - Stations: "STA 1+00" → "1+00"
        - Elevations: "ELEV 102.5" → "102.5"
        """
        text = text.upper().strip()
        
        # Try patterns in order
        patterns = [
            (r'(\d+\.?\d*)\s*(?:IN|INCH|")', "diameter"),  # Pipe diameter
            (r'(\d+\.?\d*)\s*%', "slope"),  # Slope percentage
            (r'MH[-\s]?(\d+)', "manhole"),  # Manhole ID
            (r'INLET[-\s]?(\d+)', "inlet"),  # Inlet ID
            (r'STA\s+([\d+]+)', "station"),  # Station
            (r'ELEV\.?\s+(\d+\.?\d*)', "elevation"),  # Elevation
            (r'(\d+\.?\d*)\s*(?:FT|FEET)', "length"),  # Length
        ]
        
        for pattern, _ in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        # If no pattern matches, return the original text if it contains numbers
        if re.search(r'\d', text):
            return text
        
        return None
    
    def close(self):
        """Close the PDF document and release resources."""
        if self._doc is not None:
            try:
                # Apryse docs don't need explicit closing in Python
                # but we clear the reference
                self._doc = None
                logger.debug(f"Closed PDF: {self.pdf_path.name}")
            except Exception as e:
                logger.warning(f"Error closing PDF: {e}")


def create_extractor(pdf_path: str) -> VectorExtractor:
    """
    Factory function to create a VectorExtractor.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        VectorExtractor instance
        
    Raises:
        ApryseUnavailable: If Apryse is not enabled
        FileNotFoundError: If PDF doesn't exist
    """
    return VectorExtractor(pdf_path)


# Convenience function for quick extraction
def extract_all(pdf_path: str, page_num: int = 0, layer_hints: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Extract all data from a PDF page in one call.
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page index (0-based)
        layer_hints: Optional layer names to filter (None = all layers)
        
    Returns:
        Dictionary with scale, lines, and texts
        
    Example:
        data = extract_all("plans.pdf", page_num=1, layer_hints=["STORM"])
        scale = data["scale"]
        lines = data["lines"]  # Real-world lengths in feet
        texts = data["texts"]  # Annotations with values
    """
    extractor = VectorExtractor(pdf_path)
    
    try:
        scale = extractor.load_scale(page_num)
        lines = extractor.extract_layer_lines(layer_hints or [], page_num)
        texts = extractor.extract_text_annotations(page_num)
        
        return {
            "scale": scale.to_dict(),
            "lines": [line.to_dict() for line in lines],
            "texts": [text.to_dict() for text in texts],
            "page_num": page_num,
            "pdf_file": str(pdf_path)
        }
    finally:
        extractor.close()

