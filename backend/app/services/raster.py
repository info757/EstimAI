"""Raster rendering utilities using PyMuPDF."""
import fitz  # PyMuPDF
import numpy as np
from typing import Tuple, Dict
from pathlib import Path


def render_pdf_page(pdf_path: str, page: int, dpi: int = 300) -> Tuple[np.ndarray, Dict]:
    """
    Render a PDF page to a numpy array using PyMuPDF.
    
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
        
        # Render page to pixmap
        pixmap = pdf_page.get_pixmap(matrix=matrix)
        
        # Convert to numpy array
        # Get raw image data as bytes
        img_data = pixmap.tobytes("ppm")
        
        # Convert to numpy array
        # PPM format: P6 (binary), width height, maxval, then RGB data
        img_width_px = pixmap.width
        img_height_px = pixmap.height
        
        # Reshape the data to (height, width, 3) for RGB
        img_array = np.frombuffer(img_data, dtype=np.uint8)
        img_array = img_array.reshape((img_height_px, img_width_px, 3))
        
        # Calculate scale factors (PDF points per pixel)
        scale_x_pts_per_px = page_width_pts / img_width_px
        scale_y_pts_per_px = page_height_pts / img_height_px
        
        # Create metadata dictionary
        meta = {
            "page_width_pts": page_width_pts,
            "page_height_pts": page_height_pts,
            "img_width_px": img_width_px,
            "img_height_px": img_height_px,
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
        
        # Render the region
        pixmap = pdf_page.get_pixmap(matrix=matrix, clip=clip_rect)
        
        # Convert to numpy array
        img_data = pixmap.tobytes("ppm")
        img_width_px = pixmap.width
        img_height_px = pixmap.height
        
        img_array = np.frombuffer(img_data, dtype=np.uint8)
        img_array = img_array.reshape((img_height_px, img_width_px, 3))
        
        # Calculate scale factors for the region
        region_width_pts = x1 - x0
        region_height_pts = y1 - y0
        scale_x_pts_per_px = region_width_pts / img_width_px
        scale_y_pts_per_px = region_height_pts / img_height_px
        
        # Create metadata
        meta = {
            "page_width_pts": region_width_pts,
            "page_height_pts": region_height_pts,
            "img_width_px": img_width_px,
            "img_height_px": img_height_px,
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
