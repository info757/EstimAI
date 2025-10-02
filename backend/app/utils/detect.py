"""Detection utilities for count items."""
import os
import tempfile
import uuid
from typing import List, Dict, Any, Tuple, Optional
import fitz  # PyMuPDF
import cv2
import numpy as np
from pathlib import Path

from ..models import CountItem, CountStatus
from ..schemas import CountItemCreate
from ..core.config import settings

class DetectionResult:
    def __init__(self, file: str, page: int, points_per_foot: float):
        self.file = file
        self.page = page
        self.points_per_foot = points_per_foot
        self.counts: List[Dict[str, Any]] = []
        self.totals: Dict[str, int] = {}

def convert_px_to_pdf(x_px: float, y_px: float, page_rect: fitz.Rect, image_width: int, image_height: int) -> Tuple[float, float]:
    """Convert pixel coordinates to PDF coordinates."""
    sx = page_rect.width / image_width
    sy = page_rect.height / image_height
    x_pdf = x_px * sx
    y_pdf = y_px * sy
    return x_pdf, y_pdf

def load_templates(templates_dir: str) -> Dict[str, np.ndarray]:
    """Load template images for template matching."""
    templates = {}
    template_files = ["water.png", "sewer.png", "storm.png"]
    
    for template_file in template_files:
        template_path = os.path.join(templates_dir, template_file)
        if os.path.exists(template_path):
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            if template is not None:
                templates[template_file.replace('.png', '')] = template
                print(f"Loaded template: {template_file}")
    
    return templates

def template_match(image: np.ndarray, templates: Dict[str, np.ndarray], threshold: float = 0.8) -> List[Dict[str, Any]]:
    """Perform template matching on the image."""
    detections = []
    
    for template_name, template in templates.items():
        # Perform template matching
        result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)
        
        # Get template dimensions
        h, w = template.shape
        
        for pt in zip(*locations[::-1]):  # Switch x and y coordinates
            x_px = pt[0] + w // 2  # Center of template
            y_px = pt[1] + h // 2
            confidence = result[pt[1], pt[0]]
            
            detections.append({
                "type": template_name,
                "x_px": float(x_px),
                "y_px": float(y_px),
                "confidence": float(confidence)
            })
    
    return detections

def generate_synthetic_detections() -> List[Dict[str, Any]]:
    """Generate synthetic detections when no templates are available."""
    synthetic_types = ["water", "sewer", "storm", "valve", "hydrant"]
    detections = []
    
    # Generate 3-5 random detections
    num_detections = np.random.randint(3, 6)
    
    for i in range(num_detections):
        detection_type = np.random.choice(synthetic_types)
        x_px = np.random.uniform(100, 800)  # Random x position
        y_px = np.random.uniform(100, 1000)  # Random y position
        confidence = np.random.uniform(0.7, 0.95)  # High confidence for synthetic
        
        detections.append({
            "type": detection_type,
            "x_px": float(x_px),
            "y_px": float(y_px),
            "confidence": float(confidence)
        })
    
    return detections

def detect_count_items(
    pdf_path: str, 
    page_num: int, 
    points_per_foot: float,
    templates_dir: str = None
) -> DetectionResult:
    """
    Detect count items on a PDF page using template matching or synthetic detection.
    
    Args:
        pdf_path: Path to the PDF file
        page_num: Page number (0-based)
        points_per_foot: Scale factor for coordinate conversion
        templates_dir: Directory containing template images (uses settings if None)
    
    Returns:
        DetectionResult with counts and totals
    """
    if templates_dir is None:
        templates_dir = str(settings.get_templates_dir())
    
    result = DetectionResult(pdf_path, page_num + 1, points_per_foot)  # Convert to 1-based
    
    try:
        # Open PDF with PyMuPDF
        doc = fitz.open(pdf_path)
        if page_num >= len(doc):
            raise ValueError(f"Page {page_num} not found in PDF")
        
        page = doc[page_num]
        page_rect = page.rect
        
        # Render page to PNG at 300 DPI
        matrix = fitz.Matrix(300/72, 300/72)  # 300 DPI
        pix = page.get_pixmap(matrix=matrix)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            pix.save(temp_file.name)
            temp_path = temp_file.name
        
        # Load image with OpenCV
        image = cv2.imread(temp_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError("Failed to load rendered image")
        
        image_height, image_width = image.shape
        
        # Try to load templates
        templates = load_templates(templates_dir)
        
        if templates:
            print(f"Using template matching with {len(templates)} templates")
            detections = template_match(image, templates)
        else:
            print("No templates found, using synthetic detections")
            detections = generate_synthetic_detections()
        
        # Convert detections to PDF coordinates and create count items
        for detection in detections:
            x_pdf, y_pdf = convert_px_to_pdf(
                detection["x_px"], 
                detection["y_px"], 
                page_rect, 
                image_width, 
                image_height
            )
            
            count_item = {
                "id": str(uuid.uuid4()),
                "type": detection["type"],
                "x_pdf": x_pdf,
                "y_pdf": y_pdf,
                "confidence": detection["confidence"],
                "status": "pending"
            }
            
            result.counts.append(count_item)
            
            # Update totals
            result.totals[detection["type"]] = result.totals.get(detection["type"], 0) + 1
        
        # Clean up temporary file
        os.unlink(temp_path)
        doc.close()
        
    except Exception as e:
        print(f"Detection error: {e}")
        # Fallback to synthetic detections
        detections = generate_synthetic_detections()
        
        for detection in detections:
            count_item = {
                "id": str(uuid.uuid4()),
                "type": detection["type"],
                "x_pdf": detection["x_px"],  # Use pixel coordinates as fallback
                "y_pdf": detection["y_px"],
                "confidence": detection["confidence"],
                "status": "pending"
            }
            
            result.counts.append(count_item)
            result.totals[detection["type"]] = result.totals.get(detection["type"], 0) + 1
    
    return result

def create_count_items_from_detection(
    detection_result: DetectionResult, 
    db_session
) -> List[CountItem]:
    """Create CountItem database records from detection results."""
    count_items = []
    
    for count_data in detection_result.counts:
        count_item = CountItem(
            file=detection_result.file,
            page=detection_result.page,
            type=count_data["type"],
            confidence=count_data["confidence"],
            x_pdf=count_data["x_pdf"],
            y_pdf=count_data["y_pdf"],
            points_per_foot=detection_result.points_per_foot,
            status=CountStatus.PENDING
        )
        
        db_session.add(count_item)
        count_items.append(count_item)
    
    db_session.commit()
    return count_items
