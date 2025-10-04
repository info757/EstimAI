"""
Apryse PDFNet runtime utilities.

This module provides functions to initialize and work with Apryse PDFNet
for PDF document processing.
"""
import logging
from typing import Optional, Iterator, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Global state
_initialized = False
_pdfnet_available = False

def init(license_key: Optional[str] = None) -> None:
    """
    Initialize Apryse PDFNet. Idempotent.
    """
    global _initialized, _pdfnet_available
    
    if _initialized:
        logger.debug("PDFNet already initialized.")
        return
    
    try:
        # Try to import PDFNet
        import pdftron
        from pdftron import PDFNet
        from pdftron.SDF import SDFDoc
        from pdftron.PDF import PDFDoc, Page
        
        if license_key:
            PDFNet.Initialize(license_key)
            logger.info("PDFNet initialized with license key.")
        else:
            PDFNet.Initialize()
            logger.warning("PDFNet initialized in demo mode (no license key provided).")
        
        _pdfnet_available = True
        _initialized = True
        
    except ImportError:
        logger.warning("PDFNet not available - pdftron module not found")
        _pdfnet_available = False
        _initialized = True
    except Exception as e:
        logger.error(f"Failed to initialize PDFNet: {e}")
        _pdfnet_available = False
        _initialized = True
        raise


def open_doc(path_or_bytes: str | bytes) -> Any:
    """
    Open a PDF document from a file path or bytes.
    Returns a mock document for testing when PDFNet is not available.
    """
    if not _pdfnet_available:
        # Return a mock document for testing
        return MockPDFDoc(path_or_bytes)
    
    try:
        import pdftron
        from pdftron.PDF import PDFDoc
        
        doc = PDFDoc()
        if isinstance(path_or_bytes, str):
            doc.InitSecurityHandler()
            doc.Open(path_or_bytes)
            logger.debug(f"Opened PDF from path: {path_or_bytes}")
        elif isinstance(path_or_bytes, bytes):
            reader = pdftron.Filters.MemoryFilter(path_or_bytes)
            doc.InitSecurityHandler()
            doc.Open(reader)
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
