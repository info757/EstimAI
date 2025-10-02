"""OpenCV template matching detector implementation."""
try:
    import cv2  # type: ignore
except Exception as e:
    raise RuntimeError(
        "OpenCV is required for the template detector. "
        "Install it with: pip install opencv-python-headless"
    ) from e

import numpy as np
from pathlib import Path
from typing import List, Tuple
from .base import Detection, Detector
from ...core.config import settings


class OpenCVTemplateDetector:
    """OpenCV-based template matching detector."""
    
    def __init__(self, templates_dir: Path):
        """
        Initialize detector with templates from directory.
        
        Args:
            templates_dir: Directory containing PNG template files
        """
        self.templates_dir = Path(templates_dir)
        self.templates = {}
        self.threshold = 0.8
        
        # Load all PNG templates
        self._load_templates()
    
    def _load_templates(self):
        """Load all PNG template files from the templates directory."""
        if not self.templates_dir.exists():
            print(f"Warning: Templates directory {self.templates_dir} does not exist")
            return
        
        png_files = list(self.templates_dir.glob("*.png"))
        if not png_files:
            print(f"Warning: No PNG files found in {self.templates_dir}")
            return
        
        for template_path in png_files:
            template_name = template_path.stem  # e.g., "water", "sewer"
            template_img = cv2.imread(str(template_path), cv2.IMREAD_UNCHANGED)
            
            if template_img is None:
                print(f"Warning: Could not load template {template_path}")
                continue
            
            # Handle alpha channel if present
            if template_img.shape[2] == 4:
                # Separate RGB and alpha
                template_rgb = template_img[:, :, 0:3]
                template_alpha = template_img[:, :, 3]
            else:
                template_rgb = template_img
                template_alpha = None
            
            self.templates[template_name] = {
                'template': template_rgb,
                'alpha': template_alpha,
                'width': template_rgb.shape[1],
                'height': template_rgb.shape[0]
            }
            
            print(f"Loaded template: {template_name} ({template_rgb.shape[1]}x{template_rgb.shape[0]})")
    
    def _apply_nms(self, detections: List[Tuple[str, int, int, float]], 
                   template_width: int, template_height: int) -> List[Tuple[str, int, int, float]]:
        """
        Apply Non-Maximum Suppression to remove overlapping detections.
        
        Args:
            detections: List of (type, x, y, confidence) tuples
            template_width: Template width for overlap calculation
            template_height: Template height for overlap calculation
            
        Returns:
            Filtered list of detections
        """
        if not detections:
            return []
        
        # Sort by confidence (descending)
        detections.sort(key=lambda x: x[3], reverse=True)
        
        # Calculate overlap threshold
        min_dim = min(template_width, template_height)
        overlap_threshold = 0.6 * min_dim
        
        filtered = []
        for detection in detections:
            type_name, x, y, conf = detection
            
            # Check for overlap with existing detections
            is_overlap = False
            for existing in filtered:
                _, ex_x, ex_y, _ = existing
                
                # Calculate distance between centers
                distance = np.sqrt((x - ex_x)**2 + (y - ex_y)**2)
                
                if distance < overlap_threshold:
                    is_overlap = True
                    break
            
            if not is_overlap:
                filtered.append(detection)
        
        return filtered
    
    def detect(self, img: np.ndarray) -> List[Detection]:
        """
        Detect objects in image using template matching.
        
        Args:
            img: Input image as numpy array (RGB format)
            
        Returns:
            List of Detection objects
        """
        if not self.templates:
            return []
        
        all_detections = []
        
        for template_name, template_data in self.templates.items():
            template = template_data['template']
            alpha = template_data['alpha']
            template_width = template_data['width']
            template_height = template_data['height']
            
            # Perform template matching
            if alpha is not None:
                # Use alpha channel as mask
                result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED, mask=alpha)
            else:
                result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
            
            # Find locations above threshold
            locations = np.where(result >= self.threshold)
            
            # Convert to list of (x, y, confidence) tuples
            template_detections = []
            for pt in zip(*locations[::-1]):  # Switch x and y
                x, y = pt
                confidence = result[y, x]
                
                # Convert to center coordinates
                center_x = x + template_width // 2
                center_y = y + template_height // 2
                
                template_detections.append((template_name, center_x, center_y, confidence))
            
            # Apply NMS to this template's detections
            filtered_detections = self._apply_nms(template_detections, template_width, template_height)
            all_detections.extend(filtered_detections)
        
        # Convert to Detection objects
        detections = []
        for type_name, x, y, confidence in all_detections:
            detection = Detection(
                type=type_name,
                x_px=float(x),
                y_px=float(y),
                confidence=float(confidence)
            )
            detections.append(detection)
        
        return detections


# Type alias for the detector
Detector = OpenCVTemplateDetector
