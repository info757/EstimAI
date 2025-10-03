"""Detection service that orchestrates raster rendering, detection, and coordinate mapping."""
import numpy as np
from typing import List, Dict, Tuple, Any
from pathlib import Path

from .raster import render_pdf_page, px_to_pdf
from .detectors import get_detector
from backend.app.core.config import settings


async def run_detection(pdf_path: str, page: int) -> Tuple[List[Dict], Dict]:
    """
    Run detection on a PDF page.
    
    Args:
        pdf_path: Path to the PDF file
        page: Page number (0-based)
        
    Returns:
        Tuple of (detections, metadata)
        - detections: List of dicts with {type, x_pdf, y_pdf, confidence}
        - metadata: Rendering metadata from raster service
    """
    # Validate inputs
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    if page < 0:
        raise ValueError(f"Page number must be non-negative, got: {page}")
    
    # Step 1: Rasterize the PDF page to RGB numpy array
    print(f"Rendering PDF page {page} from {pdf_path}")
    img_array, meta = render_pdf_page(str(pdf_path), page, dpi=300)
    
    # Step 2: Get detector and run detection
    print(f"Running detection with {settings.DETECTOR_IMPL} detector")
    detector = get_detector(settings.DETECTOR_IMPL)
    hits = await detector.detect(img_array)
    
    # Step 3: Convert pixel coordinates to PDF coordinates
    print(f"Converting {len(hits)} detections to PDF coordinates")
    detections = []
    
    for hit in hits:
        # Convert pixel coordinates to PDF coordinates
        x_pdf, y_pdf = px_to_pdf(hit["x_px"], hit["y_px"], meta)
        
        detection_dict = {
            "type": hit["type"],
            "x_pdf": x_pdf,
            "y_pdf": y_pdf,
            "confidence": hit["confidence"]
        }
        detections.append(detection_dict)
    
    # Step 4: Prepare metadata
    detection_meta = {
        "pdf_path": str(pdf_path),
        "page": page,
        "detector": settings.DETECTOR_IMPL,
        "total_detections": len(detections),
        "image_shape": img_array.shape,
        "rendering_meta": meta
    }
    
    # Add detection summary by type
    type_counts = {}
    for detection in detections:
        type_name = detection["type"]
        type_counts[type_name] = type_counts.get(type_name, 0) + 1
    
    detection_meta["type_counts"] = type_counts
    
    print(f"Detection complete: {len(detections)} objects found")
    for type_name, count in type_counts.items():
        print(f"  - {type_name}: {count}")
    
    return detections, detection_meta


async def run_detection_with_region(
    pdf_path: str, 
    page: int, 
    region: Tuple[float, float, float, float]
) -> Tuple[List[Dict], Dict]:
    """
    Run detection on a specific region of a PDF page.
    
    Args:
        pdf_path: Path to the PDF file
        page: Page number (0-based)
        region: (x0, y0, x1, y1) in PDF points defining the region
        
    Returns:
        Tuple of (detections, metadata)
    """
    from .raster import render_pdf_page_region
    
    # Validate inputs
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    if page < 0:
        raise ValueError(f"Page number must be non-negative, got: {page}")
    
    # Step 1: Render the specific region
    print(f"Rendering PDF page {page} region {region} from {pdf_path}")
    img_array, meta = render_pdf_page_region(str(pdf_path), page, region, dpi=300)
    
    # Step 2: Get detector and run detection
    print(f"Running detection with {settings.DETECTOR_IMPL} detector")
    detector = get_detector(settings.DETECTOR_IMPL)
    hits = await detector.detect(img_array)
    
    # Step 3: Convert pixel coordinates to PDF coordinates
    print(f"Converting {len(hits)} detections to PDF coordinates")
    detections = []
    
    for hit in hits:
        # Convert pixel coordinates to PDF coordinates
        x_pdf, y_pdf = px_to_pdf(hit["x_px"], hit["y_px"], meta)
        
        detection_dict = {
            "type": hit["type"],
            "x_pdf": x_pdf,
            "y_pdf": y_pdf,
            "confidence": hit["confidence"]
        }
        detections.append(detection_dict)
    
    # Step 4: Prepare metadata
    detection_meta = {
        "pdf_path": str(pdf_path),
        "page": page,
        "region": region,
        "detector": settings.DETECTOR_IMPL,
        "total_detections": len(detections),
        "image_shape": img_array.shape,
        "rendering_meta": meta
    }
    
    # Add detection summary by type
    type_counts = {}
    for detection in detections:
        type_name = detection["type"]
        type_counts[type_name] = type_counts.get(type_name, 0) + 1
    
    detection_meta["type_counts"] = type_counts
    
    print(f"Region detection complete: {len(detections)} objects found")
    for type_name, count in type_counts.items():
        print(f"  - {type_name}: {count}")
    
    return detections, detection_meta


async def run_detection_batch(pdf_path: str, pages: List[int]) -> Dict[int, Tuple[List[Dict], Dict]]:
    """
    Run detection on multiple pages of a PDF.
    
    Args:
        pdf_path: Path to the PDF file
        pages: List of page numbers (0-based)
        
    Returns:
        Dictionary mapping page numbers to (detections, metadata) tuples
    """
    results = {}
    
    for page in pages:
        try:
            detections, meta = await run_detection(pdf_path, page)
            results[page] = (detections, meta)
        except Exception as e:
            print(f"Error processing page {page}: {e}")
            results[page] = ([], {"error": str(e)})
    
    return results


def get_detection_summary(results: Dict[int, Tuple[List[Dict], Dict]]) -> Dict[str, Any]:
    """
    Get summary statistics for batch detection results.
    
    Args:
        results: Results from run_detection_batch
        
    Returns:
        Summary dictionary with totals and statistics
    """
    total_detections = 0
    type_totals = {}
    successful_pages = 0
    failed_pages = 0
    
    for page, (detections, meta) in results.items():
        if "error" in meta:
            failed_pages += 1
            continue
        
        successful_pages += 1
        total_detections += len(detections)
        
        for detection in detections:
            type_name = detection["type"]
            type_totals[type_name] = type_totals.get(type_name, 0) + 1
    
    return {
        "total_pages": len(results),
        "successful_pages": successful_pages,
        "failed_pages": failed_pages,
        "total_detections": total_detections,
        "type_totals": type_totals,
        "average_detections_per_page": total_detections / successful_pages if successful_pages > 0 else 0
    }
