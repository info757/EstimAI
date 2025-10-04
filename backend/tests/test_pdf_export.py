"""
Unit tests for PDF export functionality.

Tests the PDF export service, template generation, and API endpoints.
"""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

from backend.app.services.pdf_export import PDFExportService, ExportSummary, get_pdf_export_service
from backend.app.schemas_estimai import EstimAIResult, Networks, StormNetwork, SanitaryNetwork, WaterNetwork, Roadway, ESC, Earthwork, Pipe, Node, QAFlag


class TestPDFExportService:
    """Test cases for PDFExportService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.service = PDFExportService(str(self.temp_dir))
    
    def test_service_initialization(self):
        """Test service initialization."""
        assert self.service.template_dir == Path(self.temp_dir)
        assert self.service.jinja_env is not None
        assert (self.temp_dir / "pdf_summary.html").exists()
    
    def test_create_default_template(self):
        """Test default template creation."""
        template_path = Path(self.temp_dir) / "pdf_summary.html"
        assert template_path.exists()
        
        content = template_path.read_text()
        assert "EstimAI Summary Report" in content
        assert "dark-mode" in content or "background: #1a1a1a" in content
        assert "{{ summary.project_name }}" in content
    
    def test_extract_scope(self):
        """Test scope extraction from EstimAI result."""
        # Create mock EstimAI result
        estimai_result = EstimAIResult(
            sheet_units="ft",
            networks=Networks(
                storm=StormNetwork(
                    pipes=[
                        Pipe(id="1", from_id="A", to_id="B", length_ft=100.0, dia_in=12, mat="concrete"),
                        Pipe(id="2", from_id="B", to_id="C", length_ft=150.0, dia_in=15, mat="concrete")
                    ],
                    structures=[]
                ),
                sanitary=SanitaryNetwork(
                    pipes=[
                        Pipe(id="3", from_id="D", to_id="E", length_ft=200.0, dia_in=8, mat="pvc")
                    ],
                    manholes=[]
                )
            ),
            roadway=Roadway(curb_lf=500.0, sidewalk_sf=1000.0),
            e_sc=ESC(silt_fence_lf=300.0, inlet_protection_ea=5),
            earthwork=Earthwork(cut_cy=100.0, fill_cy=80.0)
        )
        
        scope = self.service._extract_scope(estimai_result)
        
        assert "Storm Network" in scope
        assert scope["Storm Network"]["value"] == 2
        assert scope["Storm Network"]["unit"] == "pipes"
        
        assert "Sanitary Network" in scope
        assert scope["Sanitary Network"]["value"] == 1
        assert scope["Sanitary Network"]["unit"] == "pipes"
        
        assert "Curb" in scope
        assert scope["Curb"]["value"] == 500.0
        assert scope["Curb"]["unit"] == "LF"
        
        assert "Sidewalk" in scope
        assert scope["Sidewalk"]["value"] == 1000.0
        assert scope["Sidewalk"]["unit"] == "SF"
        
        assert "Silt Fence" in scope
        assert scope["Silt Fence"]["value"] == 300.0
        assert scope["Silt Fence"]["unit"] == "LF"
        
        assert "Earthwork Cut" in scope
        assert scope["Earthwork Cut"]["value"] == 100.0
        assert scope["Earthwork Cut"]["unit"] == "CY"
    
    def test_extract_quantities(self):
        """Test quantities extraction from EstimAI result."""
        estimai_result = EstimAIResult(
            sheet_units="ft",
            networks=Networks(
                storm=StormNetwork(
                    pipes=[
                        Pipe(id="1", from_id="A", to_id="B", length_ft=100.0, dia_in=12, mat="concrete"),
                        Pipe(id="2", from_id="B", to_id="C", length_ft=150.0, dia_in=15, mat="concrete")
                    ],
                    structures=[]
                )
            ),
            roadway=Roadway(curb_lf=500.0, sidewalk_sf=1000.0)
        )
        
        quantities = self.service._extract_quantities(estimai_result)
        
        assert "items" in quantities
        assert len(quantities["items"]) == 3  # 2 storm pipes + 1 curb + 1 sidewalk
        
        # Check storm pipes
        storm_pipes = [item for item in quantities["items"] if "Storm Pipe" in item["description"]]
        assert len(storm_pipes) == 2
        
        # Check sitework
        sitework_items = [item for item in quantities["items"] if "Concrete" in item["description"]]
        assert len(sitework_items) == 2
    
    def test_extract_qa_flags(self):
        """Test QA flags extraction."""
        estimai_result = EstimAIResult(
            sheet_units="ft",
            qa_flags=[
                QAFlag(code="SEWER_COVER_LOW", message="Insufficient cover depth", geom_id="pipe1"),
                QAFlag(code="DEEP_EXCAVATION", message="Excavation exceeds safety threshold", geom_id="pipe2"),
                QAFlag(code="WATER_PRESSURE_LOW", message="Low water pressure detected", geom_id="pipe3")
            ]
        )
        
        qa_flags = self.service._extract_qa_flags(estimai_result)
        
        assert len(qa_flags) == 3
        assert qa_flags[0]["code"] == "SEWER_COVER_LOW"
        assert qa_flags[0]["message"] == "Insufficient cover depth"
        assert qa_flags[0]["severity"] == "warning"
        
        assert qa_flags[1]["code"] == "DEEP_EXCAVATION"
        assert qa_flags[1]["severity"] == "error"
        
        assert qa_flags[2]["code"] == "WATER_PRESSURE_LOW"
        assert qa_flags[2]["severity"] == "info"
    
    def test_determine_severity(self):
        """Test QA flag severity determination."""
        assert self.service._determine_severity("SEWER_COVER_LOW") == "warning"
        assert self.service._determine_severity("MIN_DEPTH") == "warning"
        assert self.service._determine_severity("HIGH_PRESSURE") == "error"
        assert self.service._determine_severity("MAX_DEPTH") == "error"
        assert self.service._determine_severity("DEEP_EXCAVATION") == "error"
        assert self.service._determine_severity("UNKNOWN_FLAG") == "info"
    
    def test_generate_legend_snapshot(self):
        """Test legend snapshot generation."""
        estimai_result = EstimAIResult(
            sheet_units="ft",
            networks=Networks(
                storm=StormNetwork(pipes=[Pipe(id="1", from_id="A", to_id="B", length_ft=100.0)], structures=[]),
                sanitary=SanitaryNetwork(pipes=[Pipe(id="2", from_id="C", to_id="D", length_ft=150.0)], manholes=[]),
                water=WaterNetwork(pipes=[Pipe(id="3", from_id="E", to_id="F", length_ft=200.0)], hydrants=[], valves=[])
            ),
            roadway=Roadway(curb_lf=500.0, sidewalk_sf=1000.0)
        )
        
        legend_snapshot = self.service._generate_legend_snapshot(estimai_result)
        
        assert legend_snapshot is not None
        assert "Storm Network" in legend_snapshot
        assert "Sanitary Network" in legend_snapshot
        assert "Water Network" in legend_snapshot
        assert "Sitework" in legend_snapshot
        assert "legend-color" in legend_snapshot
        assert "legend-label" in legend_snapshot
    
    def test_generate_legend_snapshot_empty(self):
        """Test legend snapshot generation with empty result."""
        estimai_result = EstimAIResult(sheet_units="ft")
        
        legend_snapshot = self.service._generate_legend_snapshot(estimai_result)
        
        assert legend_snapshot is None
    
    def test_calculate_confidence_score(self):
        """Test confidence score calculation."""
        estimai_result = EstimAIResult(sheet_units="ft")
        
        confidence_score = self.service._calculate_confidence_score(estimai_result)
        
        assert confidence_score is not None
        assert 0.0 <= confidence_score <= 1.0
    
    @patch('weasyprint.HTML')
    def test_generate_summary_pdf(self, mock_weasyprint):
        """Test PDF generation."""
        # Mock weasyprint
        mock_html = Mock()
        mock_html.write_pdf.return_value = b"fake_pdf_content"
        mock_weasyprint.return_value = mock_html
        
        # Create test data
        estimai_result = EstimAIResult(
            sheet_units="ft",
            networks=Networks(
                storm=StormNetwork(
                    pipes=[Pipe(id="1", from_id="A", to_id="B", length_ft=100.0, dia_in=12, mat="concrete")],
                    structures=[]
                )
            ),
            roadway=Roadway(curb_lf=500.0),
            qa_flags=[QAFlag(code="TEST_FLAG", message="Test message")]
        )
        
        # Generate PDF
        pdf_bytes = self.service.generate_summary_pdf(
            estimai_result=estimai_result,
            project_name="Test Project",
            file_name="test.pdf",
            page_number=1
        )
        
        assert pdf_bytes == b"fake_pdf_content"
        mock_weasyprint.assert_called_once()
    
    def test_export_summary_creation(self):
        """Test ExportSummary dataclass creation."""
        summary = ExportSummary(
            project_name="Test Project",
            file_name="test.pdf",
            page_number=1,
            generated_at=datetime.now(),
            scope={"Test": {"value": 100, "unit": "LF"}},
            quantities={"items": []},
            qa_flags=[],
            legend_snapshot="<div>Test</div>",
            total_cost=1000.0,
            confidence_score=0.85
        )
        
        assert summary.project_name == "Test Project"
        assert summary.file_name == "test.pdf"
        assert summary.page_number == 1
        assert summary.total_cost == 1000.0
        assert summary.confidence_score == 0.85


class TestGetPDFExportService:
    """Test cases for get_pdf_export_service function."""
    
    def test_get_pdf_export_service_singleton(self):
        """Test that get_pdf_export_service returns singleton instance."""
        service1 = get_pdf_export_service()
        service2 = get_pdf_export_service()
        
        assert service1 is service2
        assert isinstance(service1, PDFExportService)


class TestTemplateRendering:
    """Test cases for template rendering."""
    
    def test_template_variables(self):
        """Test that template contains all required variables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = PDFExportService(temp_dir)
            template_path = Path(temp_dir) / "pdf_summary.html"
            
            content = template_path.read_text()
            
            # Check for required template variables
            required_vars = [
                "{{ summary.project_name }}",
                "{{ summary.file_name }}",
                "{{ summary.page_number }}",
                "{{ summary.generated_at.strftime",
                "{{ summary.scope.items() }}",
                "{{ summary.quantities.items }}",
                "{{ summary.qa_flags }}",
                "{{ summary.legend_snapshot|safe }}",
                "{{ summary.total_cost }}",
                "{{ summary.confidence_score }}"
            ]
            
            for var in required_vars:
                assert var in content, f"Template variable {var} not found in template"
    
    def test_template_styling(self):
        """Test that template contains dark-mode styling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = PDFExportService(temp_dir)
            template_path = Path(temp_dir) / "pdf_summary.html"
            
            content = template_path.read_text()
            
            # Check for dark-mode styling
            dark_mode_styles = [
                "background: #1a1a1a",
                "color: #ffffff",
                "background: #2d2d2d",
                "border-left: 4px solid #4a9eff",
                "color: #4a9eff"
            ]
            
            for style in dark_mode_styles:
                assert style in content, f"Dark-mode style {style} not found in template"
    
    def test_template_responsive_design(self):
        """Test that template contains responsive design elements."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = PDFExportService(temp_dir)
            template_path = Path(temp_dir) / "pdf_summary.html"
            
            content = template_path.read_text()
            
            # Check for responsive design elements
            responsive_elements = [
                "grid-template-columns: repeat(auto-fit",
                "display: flex",
                "flex-wrap: wrap",
                "@media print"
            ]
            
            for element in responsive_elements:
                assert element in content, f"Responsive element {element} not found in template"


class TestPDFExportIntegration:
    """Integration tests for PDF export."""
    
    def test_full_pdf_generation_workflow(self):
        """Test the complete PDF generation workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = PDFExportService(temp_dir)
            
            # Create comprehensive EstimAI result
            estimai_result = EstimAIResult(
                sheet_units="ft",
                networks=Networks(
                    storm=StormNetwork(
                        pipes=[
                            Pipe(id="1", from_id="A", to_id="B", length_ft=100.0, dia_in=12, mat="concrete"),
                            Pipe(id="2", from_id="B", to_id="C", length_ft=150.0, dia_in=15, mat="concrete")
                        ],
                        structures=[
                            Node(id="inlet1", kind="inlet", x=100, y=200, attrs={})
                        ]
                    ),
                    sanitary=SanitaryNetwork(
                        pipes=[
                            Pipe(id="3", from_id="D", to_id="E", length_ft=200.0, dia_in=8, mat="pvc")
                        ],
                        manholes=[
                            Node(id="mh1", kind="manhole", x=300, y=400, attrs={})
                        ]
                    ),
                    water=WaterNetwork(
                        pipes=[
                            Pipe(id="4", from_id="F", to_id="G", length_ft=250.0, dia_in=6, mat="ductile_iron")
                        ],
                        hydrants=[
                            Node(id="hydrant1", kind="hydrant", x=500, y=600, attrs={})
                        ],
                        valves=[
                            Node(id="valve1", kind="valve", x=600, y=700, attrs={})
                        ]
                    )
                ),
                roadway=Roadway(curb_lf=500.0, sidewalk_sf=1000.0),
                e_sc=ESC(silt_fence_lf=300.0, inlet_protection_ea=5),
                earthwork=Earthwork(cut_cy=100.0, fill_cy=80.0),
                qa_flags=[
                    QAFlag(code="SEWER_COVER_LOW", message="Insufficient cover depth", geom_id="pipe1"),
                    QAFlag(code="DEEP_EXCAVATION", message="Excavation exceeds safety threshold", geom_id="pipe2")
                ]
            )
            
            # Mock weasyprint to avoid actual PDF generation
            with patch('weasyprint.HTML') as mock_weasyprint:
                mock_html = Mock()
                mock_html.write_pdf.return_value = b"test_pdf_content"
                mock_weasyprint.return_value = mock_html
                
                # Generate PDF
                pdf_bytes = service.generate_summary_pdf(
                    estimai_result=estimai_result,
                    project_name="Integration Test Project",
                    file_name="integration_test.pdf",
                    page_number=1
                )
                
                assert pdf_bytes == b"test_pdf_content"
                mock_weasyprint.assert_called_once()
                
                # Verify template was called with correct data
                call_args = mock_weasyprint.call_args
                html_content = call_args[1]['string']
                
                assert "Integration Test Project" in html_content
                assert "integration_test.pdf" in html_content
                assert "Storm Network" in html_content
                assert "Sanitary Network" in html_content
                assert "Water Network" in html_content
                assert "SEWER_COVER_LOW" in html_content
                assert "DEEP_EXCAVATION" in html_content
