"""Raster rendering utilities using PyMuPDF."""
try:
    import fitz  # PyMuPDF
except Exception as e:
    raise RuntimeError(
        "PyMuPDF is required for PDF rendering. "
        "Install it with: pip install pymupdf"
    ) from e

import numpy as np
from typing import Tuple, Dict
from pathlib import Path


def render_pdf_page(pdf_path: str, page: int, dpi: int = 300) -> Tuple[np.ndarray, Dict]:
    """
    Render a PDF page to a numpy array using PyMuPDF.
    Handles Pixmap stride / row padding correctly.
    
    Args:
        pdf_path: Path to the PDF file
        page: Page number (0-based)
        dpi: Resolution in dots per inch
        
    Returns:
        Tuple of (RGB numpy array, metadata dict)
    """
    # Open PDF document
    doc = fitz.open(pdf_path)
    
    try:
        # Get the specified page
        if page >= len(doc):
            raise ValueError(f"Page {page} out of bounds for PDF {pdf_path}")
        
        pdf_page = doc[page]
        
        # Calculate zoom factor from DPI
        # PyMuPDF uses 72 DPI as base, so zoom = dpi / 72
        zoom = dpi / 72.0
        
        # Get page dimensions in PDF points
        page_rect = pdf_page.rect
        page_width_pts = page_rect.width
        page_height_pts = page_rect.height
        
        # Create transformation matrix for the specified DPI
        matrix = fitz.Matrix(zoom, zoom)
        
        # Render page to pixmap with RGB colorspace, no alpha
        pixmap = pdf_page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB, alpha=False)
        
        # Get raw samples data
        arr = np.frombuffer(pixmap.samples, dtype=np.uint8)
        
        n = pixmap.n  # number of channels (should be 3 when alpha=False and csRGB)
        if n != 3:
            # normalize to RGB if needed (rare; defensive)
            pixmap = pdf_page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB, alpha=False)
            arr = np.frombuffer(pixmap.samples, dtype=np.uint8)
            n = pixmap.n
        
        if pixmap.stride == pixmap.w * n:
            # No padding, direct reshape
            img_array = arr.reshape(pixmap.h, pixmap.w, n)
        else:
            # Handle stride/padding: reshape using stride, then crop padding columns
            img_array = (
                arr.reshape(pixmap.h, pixmap.stride)[:, :pixmap.w * n]
                   .reshape(pixmap.h, pixmap.w, n)
            )
        
        # Ensure contiguous RGB uint8
        img_array = np.ascontiguousarray(img_array, dtype=np.uint8)
        
        # Calculate scale factors (PDF points per pixel)
        scale_x_pts_per_px = page_width_pts / pixmap.w
        scale_y_pts_per_px = page_height_pts / pixmap.h
        
        # Create metadata dictionary
        meta = {
            "page_width_pts": page_width_pts,
            "page_height_pts": page_height_pts,
            "img_width_px": pixmap.w,
            "img_height_px": pixmap.h,
            "scale_x_pts_per_px": scale_x_pts_per_px,
            "scale_y_pts_per_px": scale_y_pts_per_px,
            "dpi": dpi,
            "zoom": zoom
        }
        
        return img_array, meta
        
    finally:
        # Always close the document
        doc.close()


def px_to_pdf(x_px: float, y_px: float, meta: Dict) -> Tuple[float, float]:
    """
    Convert pixel coordinates to PDF coordinates.
    
    Args:
        x_px: X coordinate in pixels
        y_px: Y coordinate in pixels
        meta: Metadata dictionary from render_pdf_page
        
    Returns:
        Tuple of (x_pdf, y_pdf) coordinates in PDF points
    """
    # Get scale factors from metadata
    scale_x = meta["scale_x_pts_per_px"]
    scale_y = meta["scale_y_pts_per_px"]
    
    # Convert pixel coordinates to PDF coordinates
    x_pdf = x_px * scale_x
    y_pdf = y_px * scale_y
    
    return x_pdf, y_pdf


def pdf_to_px(x_pdf: float, y_pdf: float, meta: Dict) -> Tuple[float, float]:
    """
    Convert PDF coordinates to pixel coordinates.
    
    Args:
        x_pdf: X coordinate in PDF points
        y_pdf: Y coordinate in PDF points
        meta: Metadata dictionary from render_pdf_page
        
    Returns:
        Tuple of (x_px, y_px) coordinates in pixels
    """
    # Get scale factors from metadata
    scale_x = meta["scale_x_pts_per_px"]
    scale_y = meta["scale_y_pts_per_px"]
    
    # Convert PDF coordinates to pixel coordinates
    x_px = x_pdf / scale_x
    y_px = y_pdf / scale_y
    
    return x_px, y_px


def get_page_info(pdf_path: str, page: int) -> Dict:
    """
    Get page information without rendering.
    
    Args:
        pdf_path: Path to the PDF file
        page: Page number (0-based)
        
    Returns:
        Dictionary with page dimensions and metadata
    """
    doc = fitz.open(pdf_path)
    
    try:
        if page >= len(doc):
            raise ValueError(f"Page {page} out of bounds for PDF {pdf_path}")
        
        pdf_page = doc[page]
        page_rect = pdf_page.rect
        
        return {
            "page_width_pts": page_rect.width,
            "page_height_pts": page_rect.height,
            "page_number": page,
            "total_pages": len(doc)
        }
        
    finally:
        doc.close()


def render_pdf_page_region(
    pdf_path: str, 
    page: int, 
    region: Tuple[float, float, float, float], 
    dpi: int = 300
) -> Tuple[np.ndarray, Dict]:
    """
    Render a specific region of a PDF page.
    
    Args:
        pdf_path: Path to the PDF file
        page: Page number (0-based)
        region: (x0, y0, x1, y1) in PDF points defining the region
        dpi: Resolution in dots per inch
        
    Returns:
        Tuple of (RGB numpy array, metadata dict)
    """
    doc = fitz.open(pdf_path)
    
    try:
        if page >= len(doc):
            raise ValueError(f"Page {page} out of bounds for PDF {pdf_path}")
        
        pdf_page = doc[page]
        
        # Calculate zoom factor
        zoom = dpi / 72.0
        
        # Create transformation matrix
        matrix = fitz.Matrix(zoom, zoom)
        
        # Define the region to render
        x0, y0, x1, y1 = region
        clip_rect = fitz.Rect(x0, y0, x1, y1)
        
        # Render the region with RGB colorspace, no alpha
        pixmap = pdf_page.get_pixmap(matrix=matrix, clip=clip_rect, colorspace=fitz.csRGB, alpha=False)
        
        # Get raw samples data
        arr = np.frombuffer(pixmap.samples, dtype=np.uint8)
        
        n = pixmap.n  # number of channels (should be 3 when alpha=False and csRGB)
        if n != 3:
            # normalize to RGB if needed (rare; defensive)
            pixmap = pdf_page.get_pixmap(matrix=matrix, clip=clip_rect, colorspace=fitz.csRGB, alpha=False)
            arr = np.frombuffer(pixmap.samples, dtype=np.uint8)
            n = pixmap.n
        
        if pixmap.stride == pixmap.w * n:
            # No padding, direct reshape
            img_array = arr.reshape(pixmap.h, pixmap.w, n)
        else:
            # Handle stride/padding: reshape using stride, then crop padding columns
            img_array = (
                arr.reshape(pixmap.h, pixmap.stride)[:, :pixmap.w * n]
                   .reshape(pixmap.h, pixmap.w, n)
            )
        
        # Ensure contiguous RGB uint8
        img_array = np.ascontiguousarray(img_array, dtype=np.uint8)
        
        # Calculate scale factors for the region
        region_width_pts = x1 - x0
        region_height_pts = y1 - y0
        scale_x_pts_per_px = region_width_pts / pixmap.w
        scale_y_pts_per_px = region_height_pts / pixmap.h
        
        # Create metadata
        meta = {
            "page_width_pts": region_width_pts,
            "page_height_pts": region_height_pts,
            "img_width_px": pixmap.w,
            "img_height_px": pixmap.h,
            "scale_x_pts_per_px": scale_x_pts_per_px,
            "scale_y_pts_per_px": scale_y_pts_per_px,
            "dpi": dpi,
            "zoom": zoom,
            "region": region,
            "clip_rect": (x0, y0, x1, y1)
        }
        
        return img_array, meta
        
    finally:
        doc.close()
