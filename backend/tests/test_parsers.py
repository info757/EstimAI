import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import csv
import json

# Import the parsers module
from app.services.parsers import (
    detect_type, parse_document, parse_csv, parse_docx, 
    parse_xlsx, parse_image_ocr, parse_pdf_stub, build_normalized
)


class TestDetectType:
    """Test document type detection."""
    
    def test_detect_type_csv(self):
        """Test CSV file type detection."""
        assert detect_type("data.csv") == "csv"
        assert detect_type("data.CSV") == "csv"
    
    def test_detect_type_docx(self):
        """Test DOCX file type detection."""
        assert detect_type("document.docx") == "docx"
        assert detect_type("document.DOCX") == "docx"
    
    def test_detect_type_xlsx(self):
        """Test XLSX file type detection."""
        assert detect_type("spreadsheet.xlsx") == "xlsx"
        assert detect_type("spreadsheet.XLSX") == "xlsx"
    
    def test_detect_type_image(self):
        """Test image file type detection."""
        assert detect_type("image.png") == "image"
        assert detect_type("photo.jpg") == "image"
        assert detect_type("scan.tiff") == "image"
        assert detect_type("picture.jpeg") == "image"
    
    def test_detect_type_pdf(self):
        """Test PDF file type detection."""
        assert detect_type("document.pdf") == "pdf"
        assert detect_type("document.PDF") == "pdf"
    
    def test_detect_type_unknown(self):
        """Test unknown file type detection."""
        assert detect_type("file.txt") == "unknown"
        assert detect_type("data.xml") == "unknown"


class TestCSVParser:
    """Test CSV parsing functionality."""
    
    def test_parse_csv_basic(self, tmp_path):
        """Test basic CSV parsing."""
        # Create a test CSV file
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Age", "City"])
            writer.writerow(["John", "30", "New York"])
            writer.writerow(["Jane", "25", "Los Angeles"])
        
        # Parse the CSV
        result = parse_csv(csv_file)
        
        # Assert structure
        assert "text" in result
        assert "tables" in result
        assert len(result["tables"]) == 1
        
        # Check table content
        table = result["tables"][0]
        assert table["name"] is None  # CSV doesn't have sheet names
        assert len(table["rows"]) == 3  # Header + 2 data rows
        
        # Check specific content
        assert table["rows"][0] == ["Name", "Age", "City"]
        assert table["rows"][1] == ["John", "30", "New York"]
        assert table["rows"][2] == ["Jane", "25", "Los Angeles"]
        
        # Check text content (flattened)
        assert "John" in result["text"]
        assert "Jane" in result["text"]
        assert "New York" in result["text"]
    
    def test_parse_csv_empty(self, tmp_path):
        """Test CSV parsing with empty file."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")
        
        result = parse_csv(csv_file)
        assert result["text"] == ""
        assert len(result["tables"]) == 0  # Empty CSV returns no tables


class TestDOCXParser:
    """Test DOCX parsing functionality."""
    
    @pytest.mark.skipif(
        not pytest.importorskip("docx", reason="python-docx not installed"),
        reason="python-docx not available"
    )
    def test_parse_docx_basic(self, tmp_path):
        """Test basic DOCX parsing."""
        from docx import Document
        
        # Create a test DOCX file
        doc = Document()
        doc.add_paragraph("This is a test paragraph.")
        doc.add_paragraph("This is another paragraph with some content.")
        
        # Add a table
        table = doc.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "Header1"
        table.cell(0, 1).text = "Header2"
        table.cell(1, 0).text = "Data1"
        table.cell(1, 1).text = "Data2"
        
        docx_file = tmp_path / "test.docx"
        doc.save(str(docx_file))
        
        # Parse the DOCX
        result = parse_docx(docx_file)
        
        # Assert structure
        assert "text" in result
        assert "tables" in result
        
        # Check text content
        assert "This is a test paragraph" in result["text"]
        assert "This is another paragraph with some content" in result["text"]
        
        # Check table content
        assert len(result["tables"]) == 1
        table = result["tables"][0]
        assert table["name"] == "Table_1"  # DOCX tables have auto-generated names
        assert len(table["rows"]) == 2
        
        # Check table data
        assert table["rows"][0] == ["Header1", "Header2"]
        assert table["rows"][1] == ["Data1", "Data2"]


class TestXLSXParser:
    """Test XLSX parsing functionality."""
    
    @pytest.mark.skipif(
        not pytest.importorskip("openpyxl", reason="openpyxl not installed"),
        reason="openpyxl not available"
    )
    def test_parse_xlsx_basic(self, tmp_path):
        """Test basic XLSX parsing."""
        from openpyxl import Workbook
        
        # Create a test XLSX file
        wb = Workbook()
        ws1 = wb.active
        ws1.title = "Sheet1"
        
        # Add data to first sheet
        ws1['A1'] = "Name"
        ws1['B1'] = "Age"
        ws1['A2'] = "John"
        ws1['B2'] = "30"
        ws1['A3'] = "Jane"
        ws1['B3'] = "25"
        
        # Add second sheet
        ws2 = wb.create_sheet("Sheet2")
        ws2['A1'] = "Product"
        ws2['B1'] = "Price"
        ws2['A2'] = "Widget"
        ws2['B2'] = "10.99"
        
        xlsx_file = tmp_path / "test.xlsx"
        wb.save(str(xlsx_file))
        
        # Parse the XLSX
        result = parse_xlsx(xlsx_file)
        
        # Assert structure
        assert "text" in result
        assert "tables" in result
        
        # Check tables (one per sheet)
        assert len(result["tables"]) == 2
        
        # Check first sheet
        sheet1 = result["tables"][0]
        assert sheet1["name"] == "Sheet1"
        assert len(sheet1["rows"]) == 3
        assert sheet1["rows"][0] == ["Name", "Age"]
        assert sheet1["rows"][1] == ["John", "30"]
        assert sheet1["rows"][2] == ["Jane", "25"]
        
        # Check second sheet
        sheet2 = result["tables"][1]
        assert sheet2["name"] == "Sheet2"
        assert len(sheet2["rows"]) == 2
        assert sheet2["rows"][0] == ["Product", "Price"]
        assert sheet2["rows"][1] == ["Widget", "10.99"]
        
        # Check text content (flattened)
        assert "John" in result["text"]
        assert "Jane" in result["text"]
        assert "Widget" in result["text"]
        assert "10.99" in result["text"]


class TestImageOCRParser:
    """Test image OCR parsing functionality."""
    
    def test_parse_image_ocr_disabled(self, tmp_path):
        """Test image parsing with OCR disabled."""
        # Create a minimal PNG file (just a few bytes)
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde')
        
        # Parse with OCR disabled
        result = parse_image_ocr(png_file, lang="eng", enabled=False)
        
        # Should return stub content
        assert "text" in result
        assert "tables" in result
        assert result["text"] == "(OCR disabled)"
        assert len(result["tables"]) == 0
    
    @pytest.mark.xfail(
        reason="Tesseract not installed or OCR not working",
        raises=(ImportError, OSError, Exception)
    )
    def test_parse_image_ocr_enabled(self, tmp_path):
        """Test image parsing with OCR enabled."""
        # Create a minimal PNG file
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde')
        
        # Parse with OCR enabled
        result = parse_image_ocr(png_file, lang="eng", enabled=True)
        
        # Should return OCR result or fallback
        assert "text" in result
        assert "tables" in result
        # OCR might return empty text for minimal images, which is fine
        assert isinstance(result["text"], str)


class TestPDFParser:
    """Test PDF parsing functionality."""
    
    def test_parse_pdf_stub(self, tmp_path):
        """Test PDF stub parsing."""
        # Create a dummy PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("%PDF-1.4\n%Test PDF content\n")
        
        result = parse_pdf_stub(pdf_file)
        
        # Should return stub content
        assert "text" in result
        assert "tables" in result
        assert result["text"] == "(PDF text extraction not yet implemented)"
        assert len(result["tables"]) == 0


class TestBuildNormalized:
    """Test normalized document model building."""
    
    def test_build_normalized(self):
        """Test building normalized document model."""
        doc_type = "csv"
        meta = {"filename": "test.csv", "content_hash": "abc123", "size": 100}
        text = "Sample text content"
        tables = [{"name": "Sheet1", "rows": [["A", "B"], ["1", "2"]]}]
        
        result = build_normalized(doc_type, meta, text, tables)
        
        # Check structure
        assert result["type"] == "csv"
        assert result["meta"] == meta
        assert result["content"]["text"] == text
        assert result["content"]["tables"] == tables


class TestParseDocument:
    """Test main document parsing function."""
    
    def test_parse_document_csv(self, tmp_path):
        """Test main parser with CSV file."""
        # Create a test CSV file
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Header"])
            writer.writerow(["Data"])
        
        # Parse using main function
        result = parse_document(csv_file, "csv")
        
        # Check normalized structure
        assert result["type"] == "csv"
        assert "meta" in result
        assert "content" in result
        assert result["meta"]["filename"] == "test.csv"
        assert result["content"]["text"] == "Header Data"
        assert len(result["content"]["tables"]) == 1
    
    def test_parse_document_unknown_type(self, tmp_path):
        """Test main parser with unknown file type."""
        # Create a dummy file
        unknown_file = tmp_path / "test.xyz"
        unknown_file.write_text("Some content")
        
        # Parse using main function
        result = parse_document(unknown_file, "unknown")
        
        # Check normalized structure
        assert result["type"] == "unknown"
        assert result["content"]["text"] == ""
        assert len(result["content"]["tables"]) == 0


class TestParserIntegration:
    """Test parser integration with ingest workflow."""
    
    def test_parser_with_ingest_metadata(self, tmp_path):
        """Test that parsers work with ingest metadata structure."""
        # Create a test CSV file
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Test"])
            writer.writerow(["Data"])
        
        # Simulate ingest workflow
        doc_type = detect_type(csv_file.name)
        parsed_content = parse_document(csv_file, doc_type)
        
        # Verify the structure matches ingest expectations
        assert parsed_content["type"] == "csv"
        assert "meta" in parsed_content
        assert "content" in parsed_content
        assert "text" in parsed_content["content"]
        assert "tables" in parsed_content["content"]
        
        # Verify content was actually parsed
        assert "Test" in parsed_content["content"]["text"]
        assert "Data" in parsed_content["content"]["text"]
        assert len(parsed_content["content"]["tables"]) > 0
