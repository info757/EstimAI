# backend/app/services/parsers.py
"""
Multi-format document parsing service with OCR support.
Provides normalized document model for ingested files.
"""

import csv
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Import parsing libraries (with fallbacks for optional dependencies)
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logger.warning("python-docx not available - DOCX parsing will be stubbed")

try:
    from openpyxl import load_workbook
    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False
    logger.warning("openpyxl not available - XLSX parsing will be stubbed")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow not available - Image processing will be stubbed")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract not available - OCR will be stubbed")


def detect_type(filename: str, mime: Optional[str] = None) -> str:
    """
    Detect document type based on filename extension.
    
    Args:
        filename: Name of the file
        mime: Optional MIME type (currently unused, for future enhancement)
        
    Returns:
        Document type string
    """
    if not filename:
        return "unknown"
    
    ext = Path(filename).suffix.lower()
    
    if ext == '.docx':
        return "docx"
    elif ext == '.xlsx':
        return "xlsx"
    elif ext == '.csv':
        return "csv"
    elif ext in ['.png', '.jpg', '.jpeg', '.tif', '.tiff']:
        return "image"
    elif ext == '.pdf':
        return "pdf"
    else:
        return "unknown"


def parse_docx(path: Path) -> Dict[str, Any]:
    """
    Parse DOCX file and extract text and tables.
    
    Args:
        path: Path to the DOCX file
        
    Returns:
        Dictionary with 'text' and 'tables' content
    """
    if not DOCX_AVAILABLE:
        return {
            "text": "(python-docx not available)",
            "tables": []
        }
    
    try:
        doc = Document(path)
        
        # Extract text from paragraphs
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text.strip())
        
        # Extract tables
        tables = []
        for i, table in enumerate(doc.tables):
            table_data = []
            for row in table.rows:
                row_data = []
                for cell in row.cells:
                    row_data.append(cell.text.strip())
                table_data.append(row_data)
            
            tables.append({
                "name": f"Table_{i+1}",
                "rows": table_data
            })
        
        return {
            "text": "\n".join(text_parts),
            "tables": tables
        }
        
    except Exception as e:
        logger.error(f"Failed to parse DOCX file {path}: {e}")
        return {
            "text": f"(Error parsing DOCX: {e})",
            "tables": []
        }


def parse_xlsx(path: Path) -> Dict[str, Any]:
    """
    Parse XLSX file and extract text and tables from each sheet.
    
    Args:
        path: Path to the XLSX file
        
    Returns:
        Dictionary with 'text' and 'tables' content
    """
    if not XLSX_AVAILABLE:
        return {
            "text": "(openpyxl not available)",
            "tables": []
        }
    
    try:
        workbook = load_workbook(path, data_only=True)
        
        # Extract text from all cells (flattened)
        text_parts = []
        tables = []
        
        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            
            # Extract table data from sheet
            table_data = []
            for row in sheet.iter_rows(values_only=True):
                if any(cell is not None and str(cell).strip() for cell in row):
                    row_data = [str(cell) if cell is not None else "" for cell in row]
                    table_data.append(row_data)
            
            if table_data:
                tables.append({
                    "name": sheet_name,
                    "rows": table_data
                })
                
                # Add sheet content to text (flattened)
                for row in table_data:
                    text_parts.extend([str(cell) for cell in row if str(cell).strip()])
        
        return {
            "text": " ".join(text_parts),
            "tables": tables
        }
        
    except Exception as e:
        logger.error(f"Failed to parse XLSX file {path}: {e}")
        return {
            "text": f"(Error parsing XLSX: {e})",
            "tables": []
        }


def parse_csv(path: Path) -> Dict[str, Any]:
    """
    Parse CSV file and extract text and table data.
    
    Args:
        path: Path to the CSV file
        
    Returns:
        Dictionary with 'text' and 'tables' content
    """
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as file:
            reader = csv.reader(file)
            rows = list(reader)
        
        # Extract text (flattened)
        text_parts = []
        for row in rows:
            text_parts.extend([str(cell) for cell in row if str(cell).strip()])
        
        # Create table structure
        tables = []
        if rows:
            tables.append({
                "name": None,  # CSV doesn't have sheet names
                "rows": rows
            })
        
        return {
            "text": " ".join(text_parts),
            "tables": tables
        }
        
    except Exception as e:
        logger.error(f"Failed to parse CSV file {path}: {e}")
        return {
            "text": f"(Error parsing CSV: {e})",
            "tables": []
        }


def parse_image_ocr(path: Path, lang: str = "eng", enabled: bool = False) -> Dict[str, Any]:
    """
    Parse image file with OCR if enabled, otherwise return stub.
    
    Args:
        path: Path to the image file
        lang: OCR language code
        enabled: Whether OCR is enabled
        
    Returns:
        Dictionary with 'text' and 'tables' content
    """
    if not enabled:
        return {
            "text": "(OCR disabled)",
            "tables": []
        }
    
    if not PIL_AVAILABLE:
        return {
            "text": "(Pillow not available for image processing)",
            "tables": []
        }
    
    if not TESSERACT_AVAILABLE:
        return {
            "text": "(pytesseract not available for OCR)",
            "tables": []
        }
    
    try:
        # Open image with PIL
        image = Image.open(path)
        
        # Perform OCR
        text = pytesseract.image_to_string(image, lang=lang)
        
        # Clean up text
        text = text.strip()
        
        return {
            "text": text if text else "(No text detected)",
            "tables": []  # OCR typically doesn't detect table structure
        }
        
    except Exception as e:
        logger.error(f"Failed to parse image with OCR {path}: {e}")
        return {
            "text": f"(Error processing image: {e})",
            "tables": []
        }


def parse_pdf_stub(path: Path) -> Dict[str, Any]:
    """
    Stub PDF parser (placeholder for future PDF text extraction).
    
    Args:
        path: Path to the PDF file
        
    Returns:
        Dictionary with stub content
    """
    return {
        "text": "(PDF text extraction not yet implemented)",
        "tables": []
    }


def build_normalized(doc_type: str, meta: Dict[str, Any], text: str, tables: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build normalized document model.
    
    Args:
        doc_type: Document type identifier
        meta: File metadata (filename, content_hash, size)
        text: Extracted text content
        tables: Extracted table data
        
    Returns:
        Normalized document model
    """
    return {
        "type": doc_type,
        "meta": meta,
        "content": {
            "text": text,
            "tables": tables
        }
    }


def parse_document(path: Path, doc_type: str, ocr_enabled: bool = False, ocr_lang: str = "eng") -> Dict[str, Any]:
    """
    Parse document based on type and return normalized model.
    
    Args:
        path: Path to the document
        doc_type: Document type
        ocr_enabled: Whether OCR is enabled for images
        ocr_lang: OCR language code
        
    Returns:
        Normalized document model
    """
    # Extract content based on document type
    if doc_type == "docx":
        content = parse_docx(path)
    elif doc_type == "xlsx":
        content = parse_xlsx(path)
    elif doc_type == "csv":
        content = parse_csv(path)
    elif doc_type == "image":
        content = parse_image_ocr(path, ocr_lang, ocr_enabled)
    elif doc_type == "pdf":
        content = parse_pdf_stub(path)
    else:
        content = {"text": "", "tables": []}
    
    # Build metadata
    meta = {
        "filename": path.name,
        "content_hash": "",  # Will be set by caller
        "size": path.stat().st_size if path.exists() else 0
    }
    
    # Return normalized model
    return build_normalized(doc_type, meta, content["text"], content["tables"])
