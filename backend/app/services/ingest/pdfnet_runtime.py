"""Apryse PDFNet runtime initialization and document handling."""
import os
from pathlib import Path
from typing import Union, Iterator, Optional
import logging

logger = logging.getLogger(__name__)

# Module-level initialization flag
_initialized = False

# PDFNet types (will be imported when needed)
PDFDoc = None
Page = None
PDFNet = None


def init(license_key: Optional[str] = None) -> None:
    """
    Initialize PDFNet runtime. Idempotent - safe to call multiple times.
    
    Args:
        license_key: Apryse license key. If None, uses demo mode.
    """
    global _initialized, PDFDoc, Page, PDFNet
    
    if _initialized:
        logger.debug("PDFNet already initialized, skipping")
        return
    
    try:
        # Import PDFNet only when needed
        import pdftron
        from pdftron.PDFNet import PDFDoc as _PDFDoc, Page as _Page, PDFNet as _PDFNet
        
        PDFDoc = _PDFDoc
        Page = _Page
        PDFNet = _PDFNet
        
        # Initialize PDFNet
        if license_key:
            PDFNet.Initialize(license_key)
            logger.info("PDFNet initialized with license key")
        else:
            PDFNet.Initialize()
            logger.info("PDFNet initialized in demo mode")
        
        _initialized = True
        logger.info("PDFNet runtime initialized successfully")
        
    except ImportError as e:
        logger.error(f"Failed to import PDFNet: {e}")
        raise RuntimeError("PDFNet not available. Install pdftron package.") from e
    except Exception as e:
        logger.error(f"Failed to initialize PDFNet: {e}")
        raise RuntimeError(f"PDFNet initialization failed: {e}") from e


def open_doc(path_or_bytes: Union[str, Path, bytes]) -> 'PDFDoc':
    """
    Open a PDF document from file path or bytes.
    
    Args:
        path_or_bytes: File path (str/Path) or PDF bytes
        
    Returns:
        PDFDoc instance
        
    Raises:
        RuntimeError: If PDFNet not initialized
        ValueError: If invalid input
    """
    if not _initialized:
        raise RuntimeError("PDFNet not initialized. Call init() first.")
    
    if PDFDoc is None:
        raise RuntimeError("PDFNet not available")
    
    try:
        if isinstance(path_or_bytes, (str, Path)):
            # File path
            path = Path(path_or_bytes)
            if not path.exists():
                raise FileNotFoundError(f"PDF file not found: {path}")
            
            doc = PDFDoc(str(path))
            logger.debug(f"Opened PDF from file: {path}")
            
        elif isinstance(path_or_bytes, bytes):
            # Bytes data
            doc = PDFDoc(path_or_bytes)
            logger.debug("Opened PDF from bytes")
            
        else:
            raise ValueError(f"Invalid input type: {type(path_or_bytes)}")
        
        # Check if document is valid
        if not doc.InitSecurityHandler():
            logger.warning("PDF document has security restrictions")
        
        return doc
        
    except Exception as e:
        logger.error(f"Failed to open PDF document: {e}")
        raise RuntimeError(f"Failed to open PDF: {e}") from e


def iter_pages(doc: 'PDFDoc') -> Iterator['Page']:
    """
    Iterate over pages in a PDF document.
    
    Args:
        doc: PDFDoc instance
        
    Yields:
        Page instances
        
    Raises:
        RuntimeError: If PDFNet not initialized
    """
    if not _initialized:
        raise RuntimeError("PDFNet not initialized. Call init() first.")
    
    if Page is None:
        raise RuntimeError("PDFNet not available")
    
    try:
        page_count = doc.GetPageCount()
        logger.debug(f"Iterating over {page_count} pages")
        
        for page_num in range(1, page_count + 1):  # PDFNet uses 1-based indexing
            try:
                page = doc.GetPage(page_num)
                yield page
            except Exception as e:
                logger.warning(f"Failed to get page {page_num}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Failed to iterate pages: {e}")
        raise RuntimeError(f"Failed to iterate pages: {e}") from e


def is_initialized() -> bool:
    """Check if PDFNet is initialized."""
    return _initialized


def get_version() -> Optional[str]:
    """Get PDFNet version if available."""
    if not _initialized or PDFNet is None:
        return None
    
    try:
        return PDFNet.GetVersion()
    except Exception:
        return None
