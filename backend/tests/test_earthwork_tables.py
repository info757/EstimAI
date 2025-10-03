"""Tests for earthwork table parsing."""
import pytest
from unittest.mock import Mock

from app.services.detectors.earthwork_tables import (
    CutFillSummary, EarthworkTable, parse_earthwork_tables,
    _find_earthwork_headers, _parse_earthwork_table, _parse_table_rows,
    _parse_station_range, _parse_volume, _parse_area, export_earthwork_summary,
    validate_earthwork_data
)
from app.services.ingest.extract import TextEl


class TestCutFillSummary:
    """Test CutFillSummary dataclass."""
    
    def test_cut_fill_summary_creation(self):
        """Test CutFillSummary creation."""
        summary = CutFillSummary(
            station_start="0+00",
            station_end="1+00",
            cut_yd3=100.0,
            fill_yd3=50.0,
            net_yd3=50.0,
            area_sf=1000.0,
            notes="Test station"
        )
        
        assert summary.station_start == "0+00"
        assert summary.station_end == "1+00"
        assert summary.cut_yd3 == 100.0
        assert summary.fill_yd3 == 50.0
        assert summary.net_yd3 == 50.0
        assert summary.area_sf == 1000.0
        assert summary.notes == "Test station"


class TestEarthworkTable:
    """Test EarthworkTable dataclass."""
    
    def test_earthwork_table_creation(self):
        """Test EarthworkTable creation."""
        summary_rows = [
            CutFillSummary("0+00", "1+00", 100.0, 50.0, 50.0, 1000.0),
            CutFillSummary("1+00", "2+00", 200.0, 75.0, 125.0, 2000.0)
        ]
        
        table = EarthworkTable(
            title="Earthwork Summary",
            summary=summary_rows,
            total_cut_yd3=300.0,
            total_fill_yd3=125.0,
            net_yd3=175.0,
            table_bounds=(0.0, 0.0, 100.0, 100.0)
        )
        
        assert table.title == "Earthwork Summary"
        assert len(table.summary) == 2
        assert table.total_cut_yd3 == 300.0
        assert table.total_fill_yd3 == 125.0
        assert table.net_yd3 == 175.0
        assert table.table_bounds == (0.0, 0.0, 100.0, 100.0)


class TestEarthworkTableParsing:
    """Test earthwork table parsing functions."""
    
    def test_find_earthwork_headers(self):
        """Test finding earthwork headers."""
        texts = [
            TextEl("EARTHWORK SUMMARY", (0, 0, 100, 20), []),
            TextEl("Some other text", (0, 20, 100, 40), []),
            TextEl("CUT AND FILL SUMMARY", (0, 40, 100, 60), []),
            TextEl("Volume Summary", (0, 60, 100, 80), [])
        ]
        
        headers = _find_earthwork_headers(texts)
        assert len(headers) == 3  # Should find 3 headers
        
        # Check that correct headers were found
        header_texts = [h.text for h in headers]
        assert "EARTHWORK SUMMARY" in header_texts
        assert "CUT AND FILL SUMMARY" in header_texts
        assert "Volume Summary" in header_texts
    
    def test_parse_station_range(self):
        """Test parsing station range from text."""
        # Test single station
        start, end = _parse_station_range("STA 0+00")
        assert start == "0+00"
        assert end == "0+00"
        
        # Test station range
        start, end = _parse_station_range("STA 0+00 TO 1+00")
        assert start == "0+00"
        assert end == "1+00"
        
        # Test station range with dash
        start, end = _parse_station_range("0+00 - 1+00")
        assert start == "0+00"
        assert end == "1+00"
        
        # Test no station found
        start, end = _parse_station_range("No station here")
        assert start == ""
        assert end == ""
    
    def test_parse_volume(self):
        """Test parsing volume from text."""
        # Test cut volume
        text = "CUT 100.5 YD3 FILL 50.0 YD3"
        cut_volume = _parse_volume(text, "cut")
        assert cut_volume == 100.5
        
        fill_volume = _parse_volume(text, "fill")
        assert fill_volume == 50.0
        
        # Test with different units
        text = "100 CU.YD"
        volume = _parse_volume(text, "cut")
        assert volume == 100.0
        
        # Test with cubic yards
        text = "200 CUBIC YARDS"
        volume = _parse_volume(text, "cut")
        assert volume == 200.0
        
        # Test with CY abbreviation
        text = "150 CY"
        volume = _parse_volume(text, "cut")
        assert volume == 150.0
        
        # Test no volume found
        text = "No volume here"
        volume = _parse_volume(text, "cut")
        assert volume == 0.0
    
    def test_parse_area(self):
        """Test parsing area from text."""
        # Test square feet
        text = "Area 1000 SF"
        area = _parse_area(text)
        assert area == 1000.0
        
        # Test square feet abbreviation
        text = "500 SQ.FT"
        area = _parse_area(text)
        assert area == 500.0
        
        # Test square feet full
        text = "2000 SQUARE FEET"
        area = _parse_area(text)
        assert area == 2000.0
        
        # Test no area found
        text = "No area here"
        area = _parse_area(text)
        assert area == 0.0
    
    def test_parse_table_rows(self):
        """Test parsing table rows."""
        # Create mock texts representing table rows
        texts = [
            TextEl("STA 0+00", (0, 0, 50, 20), []),
            TextEl("100 YD3", (50, 0, 100, 20), []),
            TextEl("50 YD3", (100, 0, 150, 20), []),
            TextEl("1000 SF", (150, 0, 200, 20), []),
            TextEl("STA 1+00", (0, 20, 50, 40), []),
            TextEl("200 YD3", (50, 20, 100, 40), []),
            TextEl("75 YD3", (100, 20, 150, 40), []),
            TextEl("2000 SF", (150, 20, 200, 40), [])
        ]
        
        rows = _parse_table_rows(texts)
        assert len(rows) == 2  # Should parse 2 rows
        
        # Check first row
        row1 = rows[0]
        assert row1.station_start == "0+00"
        assert row1.cut_yd3 == 100.0
        assert row1.fill_yd3 == 50.0
        assert row1.area_sf == 1000.0
        
        # Check second row
        row2 = rows[1]
        assert row2.station_start == "1+00"
        assert row2.cut_yd3 == 200.0
        assert row2.fill_yd3 == 75.0
        assert row2.area_sf == 2000.0
    
    def test_parse_earthwork_table(self):
        """Test parsing complete earthwork table."""
        # Create mock header
        header = TextEl("EARTHWORK SUMMARY", (0, 0, 100, 20), [])
        
        # Create mock table texts
        table_texts = [
            TextEl("STA 0+00", (0, 20, 50, 40), []),
            TextEl("100 YD3", (50, 20, 100, 40), []),
            TextEl("50 YD3", (100, 20, 150, 40), []),
            TextEl("1000 SF", (150, 20, 200, 40), [])
        ]
        
        # Mock the helper functions
        with pytest.MonkeyPatch().context() as m:
            m.setattr('app.services.detectors.earthwork_tables._find_table_bounds', 
                     lambda h, t: (0.0, 0.0, 200.0, 40.0))
            m.setattr('app.services.detectors.earthwork_tables._filter_texts_in_bounds',
                     lambda t, b: table_texts)
            m.setattr('app.services.detectors.earthwork_tables._parse_table_rows',
                     lambda t: [CutFillSummary("0+00", "0+00", 100.0, 50.0, 50.0, 1000.0)])
            
            table = _parse_earthwork_table(header, [])
            
            assert table is not None
            assert table.title == "EARTHWORK SUMMARY"
            assert len(table.summary) == 1
            assert table.total_cut_yd3 == 100.0
            assert table.total_fill_yd3 == 50.0
            assert table.net_yd3 == 50.0


class TestEarthworkTableExport:
    """Test earthwork table export functionality."""
    
    def test_export_earthwork_summary(self):
        """Test exporting earthwork summary."""
        tables = [
            EarthworkTable(
                title="Test Table",
                summary=[
                    CutFillSummary("0+00", "1+00", 100.0, 50.0, 50.0, 1000.0, "Test")
                ],
                total_cut_yd3=100.0,
                total_fill_yd3=50.0,
                net_yd3=50.0,
                table_bounds=(0.0, 0.0, 100.0, 100.0)
            )
        ]
        
        # Test successful export
        with pytest.MonkeyPatch().context() as m:
            m.setattr('builtins.open', create=True) as mock_open:
                mock_file = Mock()
                mock_open.return_value.__enter__.return_value = mock_file
                
                result = export_earthwork_summary(tables, "test.json")
                assert result == True
                mock_file.write.assert_called_once()
    
    def test_export_earthwork_summary_error(self):
        """Test exporting earthwork summary with error."""
        tables = []
        
        # Test export error
        with pytest.MonkeyPatch().context() as m:
            m.setattr('builtins.open', side_effect=Exception("File error")):
                result = export_earthwork_summary(tables, "test.json")
                assert result == False


class TestEarthworkDataValidation:
    """Test earthwork data validation."""
    
    def test_validate_earthwork_data_valid(self):
        """Test validating valid earthwork data."""
        tables = [
            EarthworkTable(
                title="Valid Table",
                summary=[
                    CutFillSummary("0+00", "1+00", 100.0, 50.0, 50.0, 1000.0)
                ],
                total_cut_yd3=100.0,
                total_fill_yd3=50.0,
                net_yd3=50.0,
                table_bounds=(0.0, 0.0, 100.0, 100.0)
            )
        ]
        
        warnings = validate_earthwork_data(tables)
        assert len(warnings) == 0
    
    def test_validate_earthwork_data_negative_volumes(self):
        """Test validating earthwork data with negative volumes."""
        tables = [
            EarthworkTable(
                title="Invalid Table",
                summary=[
                    CutFillSummary("0+00", "1+00", -100.0, 50.0, -150.0, 1000.0)
                ],
                total_cut_yd3=-100.0,
                total_fill_yd3=50.0,
                net_yd3=-150.0,
                table_bounds=(0.0, 0.0, 100.0, 100.0)
            )
        ]
        
        warnings = validate_earthwork_data(tables)
        assert len(warnings) == 1
        assert "Negative cut volume" in warnings[0]
    
    def test_validate_earthwork_data_large_net_volume(self):
        """Test validating earthwork data with large net volume."""
        tables = [
            EarthworkTable(
                title="Large Net Volume",
                summary=[
                    CutFillSummary("0+00", "1+00", 1000.0, 50.0, 950.0, 1000.0)
                ],
                total_cut_yd3=1000.0,
                total_fill_yd3=50.0,
                net_yd3=950.0,
                table_bounds=(0.0, 0.0, 100.0, 100.0)
            )
        ]
        
        warnings = validate_earthwork_data(tables)
        assert len(warnings) == 1
        assert "Large net volume" in warnings[0]
    
    def test_validate_earthwork_data_missing_station(self):
        """Test validating earthwork data with missing station data."""
        tables = [
            EarthworkTable(
                title="Missing Station",
                summary=[
                    CutFillSummary("", "", 100.0, 50.0, 50.0, 1000.0)
                ],
                total_cut_yd3=100.0,
                total_fill_yd3=50.0,
                net_yd3=50.0,
                table_bounds=(0.0, 0.0, 100.0, 100.0)
            )
        ]
        
        warnings = validate_earthwork_data(tables)
        assert len(warnings) == 1
        assert "Missing station data" in warnings[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
