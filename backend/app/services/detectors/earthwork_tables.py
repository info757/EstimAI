"""Earthwork table parsing and analysis utilities."""
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from ..ingest.extract import TextEl

logger = logging.getLogger(__name__)


@dataclass
class CutFillSummary:
    """Earthwork cut/fill summary data."""
    station_start: str
    station_end: str
    cut_yd3: float
    fill_yd3: float
    net_yd3: float
    area_sf: float
    notes: str = ""


@dataclass
class EarthworkTable:
    """Complete earthwork table data."""
    title: str
    summary: List[CutFillSummary]
    total_cut_yd3: float
    total_fill_yd3: float
    net_yd3: float
    table_bounds: Tuple[float, float, float, float]  # x1, y1, x2, y2


def parse_earthwork_tables(texts: List[TextEl]) -> List[EarthworkTable]:
    """
    Parse earthwork summary tables from text elements.
    
    Args:
        texts: List of text elements from the document
        
    Returns:
        List of parsed earthwork tables
    """
    tables = []
    
    # Find earthwork table headers
    table_headers = _find_earthwork_headers(texts)
    
    for header in table_headers:
        table = _parse_earthwork_table(header, texts)
        if table:
            tables.append(table)
    
    logger.info(f"Parsed {len(tables)} earthwork tables")
    return tables


def _find_earthwork_headers(texts: List[TextEl]) -> List[TextEl]:
    """Find earthwork table headers."""
    headers = []
    
    # Common earthwork table header patterns
    header_patterns = [
        r'EARTHWORK\s+SUMMARY',
        r'CUT\s+AND\s+FILL\s+SUMMARY',
        r'VOLUME\s+SUMMARY',
        r'EXCAVATION\s+SUMMARY',
        r'GRADING\s+SUMMARY'
    ]
    
    for text in texts:
        text_content = text.text.upper().strip()
        for pattern in header_patterns:
            if re.search(pattern, text_content, re.IGNORECASE):
                headers.append(text)
                break
    
    return headers


def _parse_earthwork_table(header: TextEl, texts: List[TextEl]) -> Optional[EarthworkTable]:
    """Parse a single earthwork table."""
    try:
        # Find table bounds
        table_bounds = _find_table_bounds(header, texts)
        if not table_bounds:
            return None
        
        # Find table rows within bounds
        table_texts = _filter_texts_in_bounds(texts, table_bounds)
        
        # Parse table data
        summary_rows = _parse_table_rows(table_texts)
        
        if not summary_rows:
            return None
        
        # Calculate totals
        total_cut = sum(row.cut_yd3 for row in summary_rows)
        total_fill = sum(row.fill_yd3 for row in summary_rows)
        net_yd3 = total_cut - total_fill
        
        return EarthworkTable(
            title=header.text,
            summary=summary_rows,
            total_cut_yd3=total_cut,
            total_fill_yd3=total_fill,
            net_yd3=net_yd3,
            table_bounds=table_bounds
        )
        
    except Exception as e:
        logger.error(f"Error parsing earthwork table: {e}")
        return None


def _find_table_bounds(header: TextEl, texts: List[TextEl]) -> Optional[Tuple[float, float, float, float]]:
    """Find the bounding box of the earthwork table."""
    # Start with header bounds
    min_x = header.bbox[0]
    min_y = header.bbox[1]
    max_x = header.bbox[2]
    max_y = header.bbox[3]
    
    # Look for table content below the header
    header_y = header.bbox[3]
    search_distance = 200.0  # points
    
    for text in texts:
        # Check if text is below the header
        if text.bbox[1] > header_y and text.bbox[1] < header_y + search_distance:
            # Check if text looks like table content
            if _is_table_content(text.text):
                min_x = min(min_x, text.bbox[0])
                min_y = min(min_y, text.bbox[1])
                max_x = max(max_x, text.bbox[2])
                max_y = max(max_y, text.bbox[3])
    
    return (min_x, min_y, max_x, max_y)


def _is_table_content(text: str) -> bool:
    """Check if text looks like table content."""
    # Look for patterns that indicate table rows
    patterns = [
        r'\d+\.\d+',  # Numbers
        r'STATION',   # Station references
        r'CUT|FILL',  # Cut/fill indicators
        r'YD3|CU\.YD',  # Volume units
        r'\+|\-',     # Plus/minus signs
    ]
    
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False


def _filter_texts_in_bounds(texts: List[TextEl], bounds: Tuple[float, float, float, float]) -> List[TextEl]:
    """Filter texts that are within the table bounds."""
    min_x, min_y, max_x, max_y = bounds
    filtered = []
    
    for text in texts:
        # Check if text is within bounds
        if (min_x <= text.bbox[0] <= max_x and 
            min_y <= text.bbox[1] <= max_y):
            filtered.append(text)
    
    return filtered


def _parse_table_rows(texts: List[TextEl]) -> List[CutFillSummary]:
    """Parse table rows into CutFillSummary objects."""
    rows = []
    
    # Sort texts by Y coordinate (top to bottom)
    sorted_texts = sorted(texts, key=lambda t: t.bbox[1])
    
    # Group texts by row (similar Y coordinates)
    current_row = []
    current_y = None
    tolerance = 5.0  # points
    
    for text in sorted_texts:
        if current_y is None or abs(text.bbox[1] - current_y) <= tolerance:
            current_row.append(text)
            current_y = text.bbox[1]
        else:
            # Process current row
            if current_row:
                summary = _parse_table_row(current_row)
                if summary:
                    rows.append(summary)
            
            # Start new row
            current_row = [text]
            current_y = text.bbox[1]
    
    # Process last row
    if current_row:
        summary = _parse_table_row(current_row)
        if summary:
            rows.append(summary)
    
    return rows


def _parse_table_row(texts: List[TextEl]) -> Optional[CutFillSummary]:
    """Parse a single table row."""
    try:
        # Sort texts by X coordinate (left to right)
        sorted_texts = sorted(texts, key=lambda t: t.bbox[0])
        
        # Extract text content
        row_text = " ".join(text.text for text in sorted_texts)
        
        # Parse station range
        station_start, station_end = _parse_station_range(row_text)
        
        # Parse volumes
        cut_yd3 = _parse_volume(row_text, "cut")
        fill_yd3 = _parse_volume(row_text, "fill")
        
        # Parse area
        area_sf = _parse_area(row_text)
        
        # Calculate net
        net_yd3 = cut_yd3 - fill_yd3
        
        # Only return if we found meaningful data
        if station_start or cut_yd3 > 0 or fill_yd3 > 0:
            return CutFillSummary(
                station_start=station_start,
                station_end=station_end,
                cut_yd3=cut_yd3,
                fill_yd3=fill_yd3,
                net_yd3=net_yd3,
                area_sf=area_sf,
                notes=row_text
            )
        
        return None
        
    except Exception as e:
        logger.error(f"Error parsing table row: {e}")
        return None


def _parse_station_range(text: str) -> Tuple[str, str]:
    """Parse station range from text."""
    # Look for station patterns like "STA 0+00", "0+00", "STA 0+00 to 1+00"
    station_patterns = [
        r'STA\s*(\d+\+\d+)',
        r'(\d+\+\d+)',
        r'(\d+\+\d+)\s*TO\s*(\d+\+\d+)',
        r'(\d+\+\d+)\s*-\s*(\d+\+\d+)'
    ]
    
    for pattern in station_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if len(match.groups()) == 1:
                return match.group(1), match.group(1)
            elif len(match.groups()) == 2:
                return match.group(1), match.group(2)
    
    return "", ""


def _parse_volume(text: str, volume_type: str) -> float:
    """Parse volume from text."""
    # Look for volume patterns
    volume_patterns = [
        r'(\d+(?:\.\d+)?)\s*YD3',
        r'(\d+(?:\.\d+)?)\s*CU\.YD',
        r'(\d+(?:\.\d+)?)\s*CUBIC\s*YARDS',
        r'(\d+(?:\.\d+)?)\s*CY'
    ]
    
    for pattern in volume_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Try to find the volume type (cut/fill)
            if volume_type.lower() in text.lower():
                return float(matches[0])
            elif len(matches) == 1:
                return float(matches[0])
            elif len(matches) == 2:
                # Assume first is cut, second is fill
                if volume_type.lower() == "cut":
                    return float(matches[0])
                else:
                    return float(matches[1])
    
    return 0.0


def _parse_area(text: str) -> float:
    """Parse area from text."""
    # Look for area patterns
    area_patterns = [
        r'(\d+(?:\.\d+)?)\s*SF',
        r'(\d+(?:\.\d+)?)\s*SQ\.FT',
        r'(\d+(?:\.\d+)?)\s*SQUARE\s*FEET'
    ]
    
    for pattern in area_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    
    return 0.0


def export_earthwork_summary(tables: List[EarthworkTable], file_path: str) -> bool:
    """Export earthwork summary to JSON file."""
    try:
        data = []
        for table in tables:
            table_data = {
                "title": table.title,
                "summary": [
                    {
                        "station_start": row.station_start,
                        "station_end": row.station_end,
                        "cut_yd3": row.cut_yd3,
                        "fill_yd3": row.fill_yd3,
                        "net_yd3": row.net_yd3,
                        "area_sf": row.area_sf,
                        "notes": row.notes
                    }
                    for row in table.summary
                ],
                "total_cut_yd3": table.total_cut_yd3,
                "total_fill_yd3": table.total_fill_yd3,
                "net_yd3": table.net_yd3
            }
            data.append(table_data)
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Earthwork summary exported to {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error exporting earthwork summary: {e}")
        return False


def validate_earthwork_data(tables: List[EarthworkTable]) -> List[str]:
    """Validate earthwork data and return warnings."""
    warnings = []
    
    for table in tables:
        # Check for negative volumes
        for row in table.summary:
            if row.cut_yd3 < 0:
                warnings.append(f"Negative cut volume: {row.cut_yd3} at {row.station_start}")
            if row.fill_yd3 < 0:
                warnings.append(f"Negative fill volume: {row.fill_yd3} at {row.station_start}")
        
        # Check for large net volumes
        if abs(table.net_yd3) > 1000:
            warnings.append(f"Large net volume: {table.net_yd3} YD3 in {table.title}")
        
        # Check for missing station data
        for row in table.summary:
            if not row.station_start and not row.station_end:
                warnings.append(f"Missing station data in {table.title}")
    
    return warnings
