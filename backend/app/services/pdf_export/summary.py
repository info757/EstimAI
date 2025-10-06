"""
PDF summary export service.

Generates one-pager PDF summaries with key metrics, QA flags, and legend snapshots.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white, grey
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

logger = logging.getLogger(__name__)


class SummaryExporter:
    """Exports takeoff summaries to PDF format."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom styles for the PDF."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=HexColor('#4a9eff'),
            alignment=TA_CENTER,
            spaceAfter=20
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=HexColor('#cccccc'),
            alignment=TA_CENTER,
            spaceAfter=30
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=HexColor('#4a9eff'),
            spaceAfter=12,
            spaceBefore=20
        ))
        
        # Metric style
        self.styles.add(ParagraphStyle(
            name='Metric',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=HexColor('#ffffff'),
            spaceAfter=6
        ))
        
        # QA flag styles
        self.styles.add(ParagraphStyle(
            name='QAError',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=white,
            backColor=HexColor('#ff4444'),
            alignment=TA_CENTER,
            spaceAfter=4
        ))
        
        self.styles.add(ParagraphStyle(
            name='QAWarning',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=black,
            backColor=HexColor('#ffaa00'),
            alignment=TA_CENTER,
            spaceAfter=4
        ))
        
        self.styles.add(ParagraphStyle(
            name='QAInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=white,
            backColor=HexColor('#4a9eff'),
            alignment=TA_CENTER,
            spaceAfter=4
        ))
    
    def generate_summary_data(self, session_id: str) -> Dict[str, Any]:
        """
        Generate summary data for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with summary data
        """
        # This would typically fetch data from the database
        # For now, we'll return mock data
        return {
            "session_id": session_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_pipes": 12,
            "storm_pipes": 4,
            "sanitary_pipes": 5,
            "water_pipes": 3,
            "total_length": 1250.5,
            "curb_lf": 450.0,
            "sidewalk_sf": 1200.0,
            "silt_fence_lf": 180.0,
            "inlet_protection_ea": 8,
            "depth_0_5": 320.5,
            "depth_5_8": 480.0,
            "depth_8_12": 300.0,
            "depth_12_plus": 150.0,
            "total_trench_cy": 125.5,
            "total_qa_flags": 3,
            "qa_flags": [
                {"code": "COVER_LOW", "severity": "error"},
                {"code": "DEEP_EXCAVATION", "severity": "warning"},
                {"code": "GROUND_FALLBACK", "severity": "info"}
            ],
            "legend_items": [
                {"label": "Storm Pipe", "color": "#4a9eff"},
                {"label": "Sanitary Pipe", "color": "#ff6b6b"},
                {"label": "Water Pipe", "color": "#51cf66"},
                {"label": "Manhole", "color": "#ffd43b"},
                {"label": "Inlet", "color": "#74c0fc"},
                {"label": "Hydrant", "color": "#ff8787"}
            ]
        }
    
    def _create_scope_summary_table(self, data: Dict[str, Any]) -> Table:
        """Create scope summary table."""
        scope_data = [
            ["Total Pipes", str(data["total_pipes"])],
            ["Storm Pipes", str(data["storm_pipes"])],
            ["Sanitary Pipes", str(data["sanitary_pipes"])],
            ["Water Pipes", str(data["water_pipes"])],
            ["Total Length", f"{data['total_length']} LF"]
        ]
        
        table = Table(scope_data, colWidths=[2*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#2a2a2a')),
            ('TEXTCOLOR', (0, 0), (-1, -1), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#444444'))
        ]))
        
        return table
    
    def _create_sitework_table(self, data: Dict[str, Any]) -> Table:
        """Create sitework quantities table."""
        sitework_data = [
            ["Curb & Gutter", f"{data['curb_lf']} LF"],
            ["Sidewalk", f"{data['sidewalk_sf']} SF"],
            ["Silt Fence", f"{data['silt_fence_lf']} LF"],
            ["Inlet Protection", f"{data['inlet_protection_ea']} EA"]
        ]
        
        table = Table(sitework_data, colWidths=[2*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#2a2a2a')),
            ('TEXTCOLOR', (0, 0), (-1, -1), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#444444'))
        ]))
        
        return table
    
    def _create_depth_analysis_table(self, data: Dict[str, Any]) -> Table:
        """Create depth analysis table."""
        depth_data = [
            ["Depth Range", "Linear Feet"],
            ["0-5 ft", f"{data['depth_0_5']} LF"],
            ["5-8 ft", f"{data['depth_5_8']} LF"],
            ["8-12 ft", f"{data['depth_8_12']} LF"],
            ["12+ ft", f"{data['depth_12_plus']} LF"],
            ["Total Trench Volume", f"{data['total_trench_cy']} CY"]
        ]
        
        table = Table(depth_data, colWidths=[2*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#2a2a2a')),
            ('TEXTCOLOR', (0, 0), (-1, -1), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#444444')),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#4a9eff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')
        ]))
        
        return table
    
    def _create_qa_flags_table(self, data: Dict[str, Any]) -> Table:
        """Create QA flags table."""
        qa_data = [["QA Flag", "Severity"]]
        
        for flag in data["qa_flags"]:
            qa_data.append([flag["code"], flag["severity"].upper()])
        
        table = Table(qa_data, colWidths=[2*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#2a2a2a')),
            ('TEXTCOLOR', (0, 0), (-1, -1), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#444444')),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#4a9eff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')
        ]))
        
        return table
    
    def _create_legend_table(self, data: Dict[str, Any]) -> Table:
        """Create legend table."""
        legend_data = [["Item", "Color"]]
        
        for item in data["legend_items"]:
            legend_data.append([item["label"], "●"])
        
        table = Table(legend_data, colWidths=[2*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#2a2a2a')),
            ('TEXTCOLOR', (0, 0), (-1, -1), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#444444')),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#4a9eff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')
        ]))
        
        return table
    
    def generate_pdf(self, session_id: str, output_path: str) -> str:
        """
        Generate PDF file for the summary.
        
        Args:
            session_id: Session identifier
            output_path: Path to save the PDF file
            
        Returns:
            Path to the generated PDF file
        """
        try:
            data = self.generate_summary_data(session_id)
            
            # Create PDF document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=0.5*inch,
                leftMargin=0.5*inch,
                topMargin=0.5*inch,
                bottomMargin=0.5*inch
            )
            
            # Build content
            story = []
            
            # Title
            story.append(Paragraph("EstimAI Takeoff Summary", self.styles['CustomTitle']))
            story.append(Paragraph(f"{session_id} • {data['timestamp']}", self.styles['CustomSubtitle']))
            story.append(Spacer(1, 20))
            
            # Create two-column layout
            # Left column
            left_content = []
            left_content.append(Paragraph("📊 Scope Summary", self.styles['SectionHeader']))
            left_content.append(self._create_scope_summary_table(data))
            left_content.append(Spacer(1, 20))
            left_content.append(Paragraph("🏗️ Sitework Quantities", self.styles['SectionHeader']))
            left_content.append(self._create_sitework_table(data))
            
            # Right column
            right_content = []
            right_content.append(Paragraph("📏 Depth Analysis", self.styles['SectionHeader']))
            right_content.append(self._create_depth_analysis_table(data))
            right_content.append(Spacer(1, 20))
            right_content.append(Paragraph("⚠️ Quality Assurance", self.styles['SectionHeader']))
            right_content.append(self._create_qa_flags_table(data))
            
            # Combine columns
            combined_data = [
                [left_content, right_content]
            ]
            
            # Create main table for layout
            main_table = Table(combined_data, colWidths=[3.5*inch, 3.5*inch])
            main_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0)
            ]))
            
            story.append(main_table)
            story.append(Spacer(1, 20))
            
            # Legend section
            story.append(Paragraph("🗺️ Legend Snapshot", self.styles['SectionHeader']))
            story.append(self._create_legend_table(data))
            
            # Footer
            story.append(Spacer(1, 30))
            story.append(Paragraph(f"Generated by EstimAI • {data['timestamp']}", 
                                 ParagraphStyle('Footer', parent=self.styles['Normal'], 
                                               fontSize=10, textColor=grey, alignment=TA_CENTER)))
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"PDF summary generated: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate PDF summary: {e}")
            raise
    
    def generate_pdf_bytes(self, session_id: str) -> bytes:
        """
        Generate PDF as bytes for API response.
        
        Args:
            session_id: Session identifier
            
        Returns:
            PDF content as bytes
        """
        try:
            # Create temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            # Generate PDF
            self.generate_pdf(session_id, tmp_path)
            
            # Read bytes
            with open(tmp_path, 'rb') as f:
                pdf_bytes = f.read()
            
            # Clean up
            import os
            os.unlink(tmp_path)
            
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Failed to generate PDF bytes: {e}")
            raise


def create_summary_exporter() -> SummaryExporter:
    """Create a summary exporter instance."""
    return SummaryExporter()


def export_session_summary(session_id: str, output_path: str) -> str:
    """
    Export session summary to PDF.
    
    Args:
        session_id: Session identifier
        output_path: Path to save the PDF file
        
    Returns:
        Path to the generated PDF file
    """
    exporter = create_summary_exporter()
    return exporter.generate_pdf(session_id, output_path)


def export_session_summary_bytes(session_id: str) -> bytes:
    """
    Export session summary as PDF bytes.
    
    Args:
        session_id: Session identifier
        
    Returns:
        PDF content as bytes
    """
    exporter = create_summary_exporter()
    return exporter.generate_pdf_bytes(session_id)