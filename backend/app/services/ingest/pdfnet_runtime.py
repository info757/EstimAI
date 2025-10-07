"""
Apryse PDFNet runtime utilities.

This module provides functions to initialize and work with Apryse PDFNet
for PDF document processing.
"""
import logging
import os
import re
from typing import Optional, Iterator, Any, Union, Tuple, Callable, List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

# Global state
_initialized = False
_pdfnet_available = False
_pdftron_module = None


class ApryseUnavailable(Exception):
    """Raised when Apryse PDFNet is required but not available."""
    pass


def _get_pdftron():
    """Get pdftron module, trying both import names."""
    global _pdftron_module
    if _pdftron_module is not None:
        return _pdftron_module
    
    try:
        import pdftron
        _pdftron_module = pdftron
        return pdftron
    except ImportError:
        try:
            import PDFNetPython3 as pdftron
            _pdftron_module = pdftron
            return pdftron
        except ImportError:
            raise ImportError("Neither 'pdftron' nor 'PDFNetPython3' module found")

def init(license_key: Optional[str] = None) -> None:
    """
    Initialize Apryse PDFNet. Idempotent.
    """
    global _initialized, _pdfnet_available
    
    if _initialized:
        logger.debug("PDFNet already initialized.")
        return
    
    try:
        # Get pdftron module (handles both import styles)
        pdftron = _get_pdftron()
        from PDFNetPython3.PDFNetPython import PDFNet, SDFDoc, PDFDoc, Page
        
        # Initialize with license key
        if license_key:
            PDFNet.Initialize(license_key)
            logger.info("✅ PDFNet initialized with provided license key")
        else:
            # Try to get license key from settings (reads from .env)
            try:
                from backend.app.core.config import settings
                env_key = settings.APR_LICENSE_KEY
            except:
                # Fallback to os.getenv
                import os
                env_key = os.getenv("APR_LICENSE_KEY") or os.getenv("PDFTRON_LICENSE_KEY")
            
            if env_key:
                PDFNet.Initialize(env_key)
                logger.info("✅ PDFNet initialized with license key from .env/settings")
            else:
                # Try to initialize without key (will fail)
                try:
                    PDFNet.Initialize()
                    logger.warning("⚠️ PDFNet initialized in DEMO MODE (no license key)")
                except Exception as key_err:
                    logger.error(
                        f"❌ PDFNet requires a license key: {key_err}\n"
                        "Get a free demo key: https://www.pdftron.com/pws/get-key\n"
                        "Set in .env: APR_LICENSE_KEY='your-key-here'"
                    )
                    raise
        
        _pdfnet_available = True
        _initialized = True
        logger.info(f"PDFNet version: {PDFNet.GetVersion()}")
        
    except ImportError as e:
        logger.warning(f"PDFNet not available - pdftron/PDFNetPython3 module not found: {e}")
        _pdfnet_available = False
        _initialized = True
    except Exception as e:
        logger.error(f"Failed to initialize PDFNet: {e}")
        _pdfnet_available = False
        _initialized = True
        raise


def open_doc(path_or_bytes: Union[str, bytes]) -> Any:
    """
    Open a PDF document from a file path or bytes.
    Returns a mock document for testing when PDFNet is not available.
    """
    if not _pdfnet_available:
        # Return a mock document for testing
        return MockPDFDoc(path_or_bytes)
    
    try:
        pdftron = _get_pdftron()
        from PDFNetPython3.PDFNetPython import PDFDoc
        
        if isinstance(path_or_bytes, str):
            # PDFNetPython3 API: just pass filename to constructor
            doc = PDFDoc(path_or_bytes)
            logger.debug(f"Opened PDF from path: {path_or_bytes}")
        elif isinstance(path_or_bytes, bytes):
            # For bytes, need to use MemoryFilter
            from PDFNetPython3.PDFNetPython import Filter
            reader = Filter.CreateMemoryFilter(path_or_bytes)
            doc = PDFDoc(reader)
            logger.debug("Opened PDF from bytes.")
        else:
            raise ValueError("path_or_bytes must be a string (path) or bytes.")
        return doc
    except Exception as e:
        logger.error(f"Failed to open PDF: {e}")
        raise


def iter_pages(doc: Any) -> Iterator[Any]:
    """
    Iterate through pages of a PDFDoc.
    Returns mock pages for testing when PDFNet is not available.
    """
    if not _pdfnet_available:
        # Return mock pages
        for i in range(3):  # Mock 3 pages
            yield MockPage(i)
        return
    
    try:
        for i in range(1, doc.GetPageCount() + 1):
            yield doc.GetPage(i)
    except Exception as e:
        logger.error(f"Failed to iterate pages: {e}")
        raise


class MockPDFDoc:
    """Mock PDF document for testing when PDFNet is not available."""
    def __init__(self, path_or_bytes):
        self.path = path_or_bytes if isinstance(path_or_bytes, str) else "bytes"
        self.page_count = 3  # Mock 3 pages
    
    def GetPageCount(self):
        return self.page_count


class MockPage:
    """Mock PDF page for testing when PDFNet is not available."""
    def __init__(self, page_num):
        self.page_num = page_num
        self.mock_vectors = [
            {"type": "line", "x1": 100, "y1": 100, "x2": 200, "y2": 200},
            {"type": "line", "x1": 150, "y1": 150, "x2": 250, "y2": 250},
        ]
        self.mock_texts = [
            {"text": "STORM SEWER", "x": 100, "y": 100},
            {"text": "1\" = 50'", "x": 200, "y": 200},
        ]
    
    def GetPageCount(self):
        return 3


def get_scale_transform(doc: Any, page: Any) -> Tuple[float, Callable[[float, float], Tuple[float, float]]]:
    """
    Get scale transformation for converting PDF coordinates to real-world feet.
    
    Args:
        doc: PDFNet document
        page: PDFNet page
        
    Returns:
        Tuple of (feet_per_point, to_world_xy) where:
        - feet_per_point: float - Conversion factor from PDF points to feet
        - to_world_xy: callable - Function that converts (x, y) points to (X_ft, Y_ft) feet
        
    Strategy:
    1. Try to parse explicit scale bar text (e.g., "1\" = 20'", "SCALE: 1\"=40 ft")
    2. If not found, derive from PDFNet page default matrix and UserUnit
    3. Return conversion factor and coordinate transform function
    
    Scale Bar Patterns:
    - "1\" = 20'" → 20 feet per inch → 20/72 = 0.278 feet per point
    - "1 IN = 50 FT" → 50 feet per inch → 50/72 = 0.694 feet per point
    - "SCALE: 1\"=40'" → 40 feet per inch → 40/72 = 0.556 feet per point
    
    Raises:
        ApryseUnavailable: If PDFNet not initialized or APR_USE_APRYSE != 1
    """
    # Check environment
    if os.getenv("APR_USE_APRYSE", "0") != "1":
        raise ApryseUnavailable("Set APR_USE_APRYSE=1 to use Apryse scale extraction")
    
    if not _pdfnet_available:
        raise ApryseUnavailable("PDFNet not initialized - call init() first")
    
    if doc is None or page is None:
        raise ApryseUnavailable("Document or page is None")
    
    # Strategy 1: Try to parse explicit scale bar text
    scale_text, feet_per_inch = _try_parse_scale_bar(page)
    
    if feet_per_inch is not None:
        # Found explicit scale bar
        feet_per_point = feet_per_inch / 72.0
        logger.info(f"✅ Explicit scale found: {scale_text} → {feet_per_point:.6f} ft/pt")
        
        # Create transform function
        def to_world_xy(x: float, y: float) -> Tuple[float, float]:
            """Convert page coordinates to world coordinates in feet."""
            return (x * feet_per_point, y * feet_per_point)
        
        return (feet_per_point, to_world_xy)
    
    # Strategy 2: Derive from page default matrix and UserUnit
    logger.warning("No explicit scale bar found, using page default matrix + UserUnit")
    
    try:
        pdftron = _get_pdftron()
        from PDFNetPython3.PDFNetPython import Page
        
        # Get page properties
        user_unit = 1.0  # Default UserUnit
        if hasattr(page, 'GetUserUnit'):
            try:
                user_unit = page.GetUserUnit()
            except:
                pass
        
        # Get default matrix (converts page space to default user space)
        if hasattr(page, 'GetDefaultMatrix'):
            try:
                # is_right_side_up parameter depends on coordinate system
                matrix = page.GetDefaultMatrix(True)
                
                # Matrix typically has scaling factors
                # For simplicity, use the average of x and y scaling
                # matrix.m_a is x-scale, matrix.m_d is y-scale
                if hasattr(matrix, 'm_a') and hasattr(matrix, 'm_d'):
                    scale_factor = (abs(matrix.m_a) + abs(matrix.m_d)) / 2.0
                else:
                    scale_factor = 1.0
            except:
                scale_factor = 1.0
        else:
            scale_factor = 1.0
        
        # Convert: PDF points → inches → feet
        # points * user_unit / 72 = inches
        # inches / 12 = feet
        # So: feet_per_point = (user_unit / 72.0) / 12.0 * scale_factor
        feet_per_point = (user_unit * scale_factor) / 72.0 / 12.0
        
        logger.warning(
            f"Using derived scale: UserUnit={user_unit:.2f}, "
            f"ScaleFactor={scale_factor:.2f} → {feet_per_point:.6f} ft/pt "
            f"(⚠️ May be inaccurate - verify with known dimension)"
        )
        
        def to_world_xy(x: float, y: float) -> Tuple[float, float]:
            """Convert page coordinates to world coordinates in feet."""
            return (x * feet_per_point, y * feet_per_point)
        
        return (feet_per_point, to_world_xy)
    
    except Exception as e:
        logger.error(f"Failed to derive scale from page matrix: {e}")
        # Ultimate fallback: assume 1" = 20' (common engineering scale)
        feet_per_point = 20.0 / 72.0  # 0.278 ft/pt
        logger.warning(f"⚠️ Fallback to assumed scale: 1\" = 20' → {feet_per_point:.6f} ft/pt")
        
        def to_world_xy(x: float, y: float) -> Tuple[float, float]:
            return (x * feet_per_point, y * feet_per_point)
        
        return (feet_per_point, to_world_xy)


def iter_stroked_polylines(
    doc: Any,
    page: Any,
    *,
    feet_per_point: float,
    to_world_xy: Callable[[float, float], Tuple[float, float]],
    layer_hints: List[str] | None = None,
    min_len_ft: float = 8.0,
    max_count: int = 5000
) -> List[Dict[str, Any]]:
    """
    Extract stroked polylines from PDF page with real-world measurements.
    
    Args:
        doc: PDFNet document
        page: PDFNet page
        feet_per_point: Conversion factor from PDF points to feet
        to_world_xy: Function to convert (x, y) points to (X_ft, Y_ft) feet
        layer_hints: Optional layer names to filter (e.g., ["STORM", "WATER"])
        min_len_ft: Minimum length threshold in feet (default 8.0)
        max_count: Maximum number of polylines to return (default 5000)
        
    Returns:
        List of dictionaries with polyline data:
        - id: str (hash of coordinates)
        - points: [(X_ft, Y_ft), ...] in world feet
        - length_ft: float (sum of chord lengths)
        - bbox: (minx, miny, maxx, maxy) in feet
        - layer: str | None
        - stroke_width_pt: float | None
        - color: (r, g, b) | None
        
    Process:
    1. Traverse page content with ElementReader
    2. Filter for stroked PATH elements (exclude fills)
    3. Flatten Bezier curves to polylines
    4. Transform to world coordinates
    5. Calculate length and bbox
    6. Filter by layer, length, and count
    7. Deduplicate near-duplicates
    
    Example:
        scale_transform = get_scale_transform(doc, page)
        polylines = iter_stroked_polylines(doc, page, *scale_transform, layer_hints=["STORM"])
        for pl in polylines:
            print(f"{pl['id']}: {pl['length_ft']:.1f} ft")
    """
    if not _pdfnet_available:
        logger.warning("PDFNet not available, returning empty polylines")
        return []
    
    try:
        pdftron = _get_pdftron()
        from PDFNetPython3.PDFNetPython import ElementReader, Element
        import hashlib
        
        # Initialize element reader
        reader = ElementReader()
        reader.Begin(page)
        
        polylines = []
        visited_paths = 0
        kept_candidates = 0
        
        # Traverse page elements
        element = reader.Next()
        while element is not None and kept_candidates < max_count:
            try:
                # Only process PATH elements that are stroked
                if element.GetType() == Element.e_path and element.IsStroked():
                    visited_paths += 1
                    
                    # Extract path data
                    path_data = element.GetPathData()
                    if not path_data:
                        element = reader.Next()
                        continue
                    
                    # Convert path to polyline points
                    points_pdf = _flatten_path_to_polyline(path_data)
                    
                    if not points_pdf or len(points_pdf) < 2:
                        element = reader.Next()
                        continue
                    
                    # Transform to world coordinates
                    points_world = [to_world_xy(x, y) for x, y in points_pdf]
                    
                    # Calculate length in feet (sum of chord distances)
                    length_ft = 0.0
                    for i in range(len(points_world) - 1):
                        x1, y1 = points_world[i]
                        x2, y2 = points_world[i + 1]
                        segment_len = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
                        length_ft += segment_len
                    
                    # Filter by minimum length
                    if length_ft < min_len_ft:
                        element = reader.Next()
                        continue
                    
                    # Calculate bounding box
                    xs = [p[0] for p in points_world]
                    ys = [p[1] for p in points_world]
                    bbox = (min(xs), min(ys), max(xs), max(ys))
                    
                    # Get stroke properties
                    stroke_width = None
                    color = None
                    layer_name = None
                    
                    try:
                        gs = element.GetGState()
                        if gs:
                            stroke_width = gs.GetLineWidth()
                            
                            # Try to get stroke color
                            try:
                                color_space = gs.GetStrokeColorSpace()
                                if color_space:
                                    # Get RGB approximation
                                    color = (0, 0, 0)  # Placeholder - full color extraction is complex
                            except:
                                pass
                    except:
                        pass
                    
                    # Try to get layer/OCG name
                    # This is complex in PDFNet - simplified for now
                    try:
                        # Placeholder for layer extraction
                        # Full implementation would traverse OCG context
                        layer_name = None
                    except:
                        pass
                    
                    # Filter by layer hints if provided
                    if layer_hints and layer_name:
                        layer_upper = layer_name.upper()
                        if not any(hint.upper() in layer_upper for hint in layer_hints):
                            element = reader.Next()
                            continue
                    
                    # Generate stable ID from coordinates
                    coord_str = ",".join(f"{x:.2f},{y:.2f}" for x, y in points_world[:10])  # First 10 points
                    polyline_id = hashlib.md5(coord_str.encode()).hexdigest()[:12]
                    
                    # Create polyline dict
                    polyline = {
                        "id": f"pl_{polyline_id}",
                        "points": points_world,
                        "length_ft": length_ft,
                        "bbox": bbox,
                        "layer": layer_name,
                        "stroke_width_pt": stroke_width,
                        "color": color
                    }
                    
                    polylines.append(polyline)
                    kept_candidates += 1
            
            except Exception as e:
                logger.debug(f"Error processing element: {e}")
                # Continue to next element on error
            
            element = reader.Next()
        
        reader.End()
        
        # Deduplicate near-duplicates
        polylines = _deduplicate_polylines(polylines)
        
        # Calculate statistics
        if polylines:
            lengths = [pl["length_ft"] for pl in polylines]
            min_len = min(lengths)
            avg_len = sum(lengths) / len(lengths)
            max_len = max(lengths)
            
            logger.info(
                f"Extracted {len(polylines)} polylines from {visited_paths} paths "
                f"(min: {min_len:.1f} ft, avg: {avg_len:.1f} ft, max: {max_len:.1f} ft)"
            )
        else:
            logger.warning(f"No polylines extracted from {visited_paths} paths")
        
        return polylines
    
    except Exception as e:
        logger.error(f"Polyline extraction failed: {e}", exc_info=True)
        return []


def _flatten_path_to_polyline(path_data: Any, curve_samples: int = 8) -> List[Tuple[float, float]]:
    """
    Flatten a PDFNet PathData to a polyline, sampling curves.
    
    Args:
        path_data: PDFNet PathData object
        curve_samples: Number of samples for curve segments
        
    Returns:
        List of (x, y) points in PDF coordinates
        
    Operators:
    - M (moveto): Start new path at point
    - L (lineto): Line to point
    - C (curveto): Cubic Bezier (4 points)
    - Q (quad curveto): Quadratic Bezier (3 points)
    - H (horizontal lineto): Horizontal line
    - V (vertical lineto): Vertical line
    """
    points = []
    current_x, current_y = 0.0, 0.0
    
    try:
        # Get path points and operators
        operators = path_data.GetOperators()
        path_points = path_data.GetPoints()
        
        if not operators or not path_points:
            return []
        
        point_idx = 0
        
        for op in operators:
            try:
                op_type = op  # Operator type
                
                # M - MoveTo (start new subpath)
                if op_type == 1:  # PathData.e_moveto
                    if point_idx < len(path_points):
                        current_x = path_points[point_idx]
                        current_y = path_points[point_idx + 1]
                        points.append((current_x, current_y))
                        point_idx += 2
                
                # L - LineTo
                elif op_type == 2:  # PathData.e_lineto
                    if point_idx < len(path_points):
                        current_x = path_points[point_idx]
                        current_y = path_points[point_idx + 1]
                        points.append((current_x, current_y))
                        point_idx += 2
                
                # C - Cubic Bezier Curve (4 control points)
                elif op_type == 3:  # PathData.e_cubicto
                    if point_idx + 5 < len(path_points):
                        # Control points
                        cp1_x, cp1_y = path_points[point_idx], path_points[point_idx + 1]
                        cp2_x, cp2_y = path_points[point_idx + 2], path_points[point_idx + 3]
                        end_x, end_y = path_points[point_idx + 4], path_points[point_idx + 5]
                        
                        # Sample curve
                        for i in range(1, curve_samples + 1):
                            t = i / curve_samples
                            # Cubic Bezier formula
                            t2 = t * t
                            t3 = t2 * t
                            mt = 1 - t
                            mt2 = mt * mt
                            mt3 = mt2 * mt
                            
                            x = (mt3 * current_x + 
                                 3 * mt2 * t * cp1_x + 
                                 3 * mt * t2 * cp2_x + 
                                 t3 * end_x)
                            y = (mt3 * current_y + 
                                 3 * mt2 * t * cp1_y + 
                                 3 * mt * t2 * cp2_y + 
                                 t3 * end_y)
                            points.append((x, y))
                        
                        current_x, current_y = end_x, end_y
                        point_idx += 6
                
                # Rect (rectangle) - add 4 corners
                elif op_type == 5:  # PathData.e_rect
                    if point_idx + 3 < len(path_points):
                        x, y = path_points[point_idx], path_points[point_idx + 1]
                        w, h = path_points[point_idx + 2], path_points[point_idx + 3]
                        points.extend([
                            (x, y),
                            (x + w, y),
                            (x + w, y + h),
                            (x, y + h),
                            (x, y)  # Close
                        ])
                        point_idx += 4
                
                # Z - ClosePath
                elif op_type == 4:  # PathData.e_closepath
                    # No new points, just closes the path
                    pass
            
            except Exception as e:
                logger.debug(f"Error processing operator {op_type}: {e}")
                continue
        
        return points
    
    except Exception as e:
        logger.debug(f"Path flattening failed: {e}")
        return []


def _deduplicate_polylines(polylines: List[Dict[str, Any]], bbox_overlap_threshold: float = 0.8) -> List[Dict[str, Any]]:
    """
    Remove near-duplicate polylines based on bbox overlap and length similarity.
    
    Args:
        polylines: List of polyline dictionaries
        bbox_overlap_threshold: Fraction of bbox overlap to consider duplicate
        
    Returns:
        Deduplicated list of polylines
    """
    if len(polylines) <= 1:
        return polylines
    
    # Simple deduplication: keep first occurrence of similar polylines
    unique = []
    seen = set()
    
    for pl in polylines:
        # Create a simple key from rounded bbox and length
        bbox = pl["bbox"]
        key = (
            round(bbox[0], 1),
            round(bbox[1], 1),
            round(bbox[2], 1),
            round(bbox[3], 1),
            round(pl["length_ft"], 1)
        )
        
        if key not in seen:
            unique.append(pl)
            seen.add(key)
    
    if len(unique) < len(polylines):
        logger.info(f"Deduplicated {len(polylines)} → {len(unique)} polylines")
    
    return unique


def _try_parse_scale_bar(page: Any) -> Tuple[Optional[str], Optional[float]]:
    """
    Try to find and parse scale bar text from page.
    
    Returns:
        Tuple of (scale_text, feet_per_inch) or (None, None) if not found
        
    Patterns:
    - "1\" = 20'" → 20.0 feet per inch
    - "1 IN = 50 FT" → 50.0 feet per inch
    - "SCALE: 1\"=40'" → 40.0 feet per inch
    - "1\"=30 FT" → 30.0 feet per inch
    """
    if not _pdfnet_available:
        return (None, None)
    
    try:
        pdftron = _get_pdftron()
        from PDFNetPython3.PDFNetPython import TextExtractor
        
        # Extract all text from page
        txt_extractor = TextExtractor()
        txt_extractor.Begin(page)
        all_text = txt_extractor.GetAsText()
        
        # Common scale bar patterns
        patterns = [
            # "1\" = 20'" or "1 IN = 20 FT" with flexible spacing
            r'1\s*(?:"|IN|INCH)\s*=\s*(\d+(?:\.\d+)?)\s*(?:\'|FT|FEET)',
            # "SCALE: 1\" = 20'"
            r'SCALE\s*:?\s*1\s*(?:"|IN|INCH)\s*=\s*(\d+(?:\.\d+)?)\s*(?:\'|FT|FEET)',
            # "1:240" ratio format (1 inch = 240/12 = 20 feet)
            r'1\s*:\s*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                
                # For ratio format (1:240), convert to feet
                if ':' in match.group(0):
                    # 1:240 means 1 inch = 240 inches = 20 feet
                    feet_per_inch = value / 12.0
                else:
                    feet_per_inch = value
                
                scale_text = match.group(0).strip()
                logger.info(f"Parsed scale bar: '{scale_text}' → {feet_per_inch} ft/in")
                return (scale_text, feet_per_inch)
        
        # No scale found
        return (None, None)
    
    except Exception as e:
        logger.warning(f"Scale bar parsing failed: {e}")
        return (None, None)
