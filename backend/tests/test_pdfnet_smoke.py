"""Smoke tests for Apryse PDFNet integration."""
import pytest
import os
from pathlib import Path
from unittest.mock import patch

from app.core.config import settings
from app.services.ingest.pdfnet_runtime import init, open_doc, iter_pages, is_initialized, get_version


@pytest.mark.skipif(
    not settings.APR_USE_APRYSE,
    reason="Apryse PDFNet not enabled (APR_USE_APRYSE=false)"
)
class TestPDFNetSmoke:
    """Smoke tests for PDFNet functionality."""
    
    def test_init_without_license(self):
        """Test PDFNet initialization in demo mode."""
        # Reset initialization state
        import app.services.ingest.pdfnet_runtime as runtime
        runtime._initialized = False
        
        # Should not raise exception
        init(None)
        assert is_initialized()
        
        version = get_version()
        assert version is not None
        print(f"PDFNet version: {version}")
    
    def test_init_with_license(self):
        """Test PDFNet initialization with license key."""
        # Reset initialization state
        import app.services.ingest.pdfnet_runtime as runtime
        runtime._initialized = False
        
        license_key = settings.APR_LICENSE_KEY
        if license_key:
            init(license_key)
            assert is_initialized()
        else:
            # Skip if no license key provided
            pytest.skip("No license key provided")
    
    def test_init_idempotent(self):
        """Test that init() is idempotent."""
        # Reset initialization state
        import app.services.ingest.pdfnet_runtime as runtime
        runtime._initialized = False
        
        # First call
        init(None)
        assert is_initialized()
        
        # Second call should not fail
        init(None)
        assert is_initialized()
    
    def test_open_doc_with_sample_pdf(self):
        """Test opening a sample PDF document."""
        # Find a sample PDF in the files directory
        files_dir = settings.get_files_dir()
        sample_pdfs = list(files_dir.glob("*.pdf"))
        
        if not sample_pdfs:
            pytest.skip("No sample PDF files found")
        
        sample_pdf = sample_pdfs[0]
        print(f"Testing with sample PDF: {sample_pdf}")
        
        # Test opening from file path
        doc = open_doc(sample_pdf)
        assert doc is not None
        
        # Test page iteration
        pages = list(iter_pages(doc))
        assert len(pages) > 0
        print(f"Document has {len(pages)} pages")
        
        # Test first page
        first_page = pages[0]
        assert first_page is not None
        
        # Get page dimensions
        try:
            # This might not be available in all PDFNet versions
            width = first_page.GetPageWidth()
            height = first_page.GetPageHeight()
            print(f"First page dimensions: {width}x{height}")
        except AttributeError:
            print("Page dimension methods not available")
    
    def test_open_doc_with_bytes(self):
        """Test opening a PDF from bytes."""
        # Find a sample PDF
        files_dir = settings.get_files_dir()
        sample_pdfs = list(files_dir.glob("*.pdf"))
        
        if not sample_pdfs:
            pytest.skip("No sample PDF files found")
        
        sample_pdf = sample_pdfs[0]
        
        # Read PDF as bytes
        with open(sample_pdf, 'rb') as f:
            pdf_bytes = f.read()
        
        # Test opening from bytes
        doc = open_doc(pdf_bytes)
        assert doc is not None
        
        # Test page iteration
        pages = list(iter_pages(doc))
        assert len(pages) > 0
    
    def test_error_handling(self):
        """Test error handling for invalid inputs."""
        # Test with non-existent file
        with pytest.raises(FileNotFoundError):
            open_doc("non_existent.pdf")
        
        # Test with invalid bytes
        with pytest.raises(RuntimeError):
            open_doc(b"not a pdf")
        
        # Test with invalid type
        with pytest.raises(ValueError):
            open_doc(123)
    
    def test_runtime_not_initialized(self):
        """Test behavior when PDFNet is not initialized."""
        # Reset initialization state
        import app.services.ingest.pdfnet_runtime as runtime
        runtime._initialized = False
        
        # Should raise error when trying to use without init
        with pytest.raises(RuntimeError, match="PDFNet not initialized"):
            open_doc("test.pdf")
        
        with pytest.raises(RuntimeError, match="PDFNet not initialized"):
            list(iter_pages(None))


@pytest.mark.skipif(
    settings.APR_USE_APRYSE,
    reason="Apryse PDFNet is enabled, skipping disabled tests"
)
class TestPDFNetDisabled:
    """Tests for when PDFNet is disabled."""
    
    def test_disabled_initialization(self):
        """Test that PDFNet is not initialized when disabled."""
        assert not is_initialized()
        
        # Should not raise error when disabled
        # (This test mainly ensures the code path exists)
        pass


def test_import_safety():
    """Test that importing the module doesn't crash when PDFNet is unavailable."""
    # This should not raise an exception even if pdftron is not installed
    try:
        from app.services.ingest import pdfnet_runtime
        assert pdfnet_runtime is not None
    except ImportError:
        # This is expected if pdftron is not installed
        pass


if __name__ == "__main__":
    # Run smoke tests directly
    pytest.main([__file__, "-v"])
