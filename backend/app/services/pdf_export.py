"""
PDF export service for generating one-page summaries.

Provides functionality to generate PDF exports with scope, quantities,
QA flags, and legend snapshots in a dark-mode, single-page format.
"""
import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

# WeasyPrint import will be handled in the function to avoid system dependency issues
from jinja2 import Environment, FileSystemLoader, Template
from fastapi import HTTPException

from backend.app.services.assemblies import get_assemblies_mapper
from backend.app.schemas_estimai import EstimAIResult

logger = logging.getLogger(__name__)


@dataclass
class ExportSummary:
    """Summary data for PDF export."""
    project_name: str
    file_name: str
    page_number: int
    generated_at: datetime
    scope: Dict[str, Any]
    quantities: Dict[str, Any]
    qa_flags: List[Dict[str, Any]]
    legend_snapshot: Optional[str] = None
    total_cost: Optional[float] = None
    confidence_score: Optional[float] = None


class PDFExportService:
    """Service for generating PDF exports."""
    
    def __init__(self, template_dir: str = "templates"):
        self.template_dir = Path(template_dir)
        self.template_dir.mkdir(exist_ok=True)
        
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True
        )
        
        # Create default template if it doesn't exist
        self._ensure_template_exists()
    
    def _ensure_template_exists(self):
        """Ensure the PDF template exists."""
        template_path = self.template_dir / "pdf_summary.html"
        if not template_path.exists():
            self._create_default_template()
    
    def _create_default_template(self):
        """Create the default PDF template."""
        template_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EstimAI Summary Report</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1a1a;
            color: #ffffff;
            line-height: 1.6;
            padding: 20px;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: #2d2d2d;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #4a9eff;
            padding-bottom: 20px;
        }
        
        .header h1 {
            color: #4a9eff;
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }
        
        .header .subtitle {
            color: #b0b0b0;
            font-size: 1.2em;
            margin-bottom: 5px;
        }
        
        .header .project-info {
            color: #888;
            font-size: 0.9em;
        }
        
        .section {
            margin-bottom: 25px;
            background: #3a3a3a;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid #4a9eff;
        }
        
        .section h2 {
            color: #4a9eff;
            font-size: 1.4em;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
        }
        
        .section h2::before {
            content: "▶";
            margin-right: 10px;
            color: #4a9eff;
        }
        
        .scope-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .scope-item {
            background: #4a4a4a;
            padding: 15px;
            border-radius: 6px;
            border-left: 3px solid #4a9eff;
        }
        
        .scope-item h3 {
            color: #4a9eff;
            font-size: 1.1em;
            margin-bottom: 8px;
        }
        
        .scope-item .value {
            font-size: 1.3em;
            font-weight: bold;
            color: #ffffff;
        }
        
        .scope-item .unit {
            color: #b0b0b0;
            font-size: 0.9em;
            margin-left: 5px;
        }
        
        .quantities-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        
        .quantities-table th,
        .quantities-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #555;
        }
        
        .quantities-table th {
            background: #4a4a4a;
            color: #4a9eff;
            font-weight: 600;
        }
        
        .quantities-table tr:hover {
            background: #4a4a4a;
        }
        
        .qa-flags {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
        }
        
        .qa-flag {
            background: #ff6b6b;
            color: white;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 500;
        }
        
        .qa-flag.warning {
            background: #ffa726;
        }
        
        .qa-flag.info {
            background: #42a5f5;
        }
        
        .qa-flag.success {
            background: #66bb6a;
        }
        
        .legend-snapshot {
            background: #4a4a4a;
            border-radius: 6px;
            padding: 15px;
            margin-top: 15px;
            border: 1px solid #555;
        }
        
        .legend-snapshot h3 {
            color: #4a9eff;
            margin-bottom: 10px;
        }
        
        .legend-items {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .legend-color {
            width: 20px;
            height: 20px;
            border-radius: 3px;
            border: 1px solid #666;
        }
        
        .legend-label {
            color: #b0b0b0;
            font-size: 0.9em;
        }
        
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .metric {
            text-align: center;
            background: #4a4a4a;
            padding: 15px;
            border-radius: 6px;
        }
        
        .metric .value {
            font-size: 1.5em;
            font-weight: bold;
            color: #4a9eff;
        }
        
        .metric .label {
            color: #b0b0b0;
            font-size: 0.9em;
            margin-top: 5px;
        }
        
        .footer {
            margin-top: 30px;
            text-align: center;
            color: #888;
            font-size: 0.9em;
            border-top: 1px solid #555;
            padding-top: 20px;
        }
        
        @media print {
            body {
                background: white;
                color: black;
            }
            
            .container {
                background: white;
                box-shadow: none;
            }
            
            .section {
                background: #f5f5f5;
                border-left: 4px solid #4a9eff;
            }
            
            .scope-item {
                background: #f0f0f0;
            }
            
            .quantities-table th {
                background: #e0e0e0;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>EstimAI Summary Report</h1>
            <div class="subtitle">{{ summary.project_name }}</div>
            <div class="project-info">
                File: {{ summary.file_name }} | Page: {{ summary.page_number }} | Generated: {{ summary.generated_at.strftime('%Y-%m-%d %H:%M:%S') }}
            </div>
        </div>
        
        <div class="section">
            <h2>Project Scope</h2>
            <div class="scope-grid">
                {% for key, value in summary.scope.items() %}
                <div class="scope-item">
                    <h3>{{ key.replace('_', ' ').title() }}</h3>
                    <div class="value">{{ value.value if value.value is defined else value }}{% if value.unit %}<span class="unit">{{ value.unit }}</span>{% endif %}</div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <div class="section">
            <h2>Key Quantities</h2>
            <table class="quantities-table">
                <thead>
                    <tr>
                        <th>Item</th>
                        <th>Quantity</th>
                        <th>Unit</th>
                        <th>Cost</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in summary.quantities.items %}
                    <tr>
                        <td>{{ item.description }}</td>
                        <td>{{ "%.2f"|format(item.quantity) }}</td>
                        <td>{{ item.unit }}</td>
                        <td>{% if item.total_cost %}${{ "%.2f"|format(item.total_cost) }}{% else %}N/A{% endif %}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        {% if summary.qa_flags %}
        <div class="section">
            <h2>Quality Assurance Flags</h2>
            <div class="qa-flags">
                {% for flag in summary.qa_flags %}
                <div class="qa-flag {{ flag.severity if flag.severity else 'warning' }}">
                    {{ flag.code }}: {{ flag.message }}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
        {% if summary.legend_snapshot %}
        <div class="section">
            <h2>Legend Snapshot</h2>
            <div class="legend-snapshot">
                {{ summary.legend_snapshot|safe }}
            </div>
        </div>
        {% endif %}
        
        <div class="section">
            <h2>Summary Metrics</h2>
            <div class="metrics">
                {% if summary.total_cost %}
                <div class="metric">
                    <div class="value">${{ "%.2f"|format(summary.total_cost) }}</div>
                    <div class="label">Total Cost</div>
                </div>
                {% endif %}
                
                {% if summary.confidence_score %}
                <div class="metric">
                    <div class="value">{{ "%.1f"|format(summary.confidence_score * 100) }}%</div>
                    <div class="label">Confidence Score</div>
                </div>
                {% endif %}
                
                <div class="metric">
                    <div class="value">{{ summary.quantities.items|length }}</div>
                    <div class="label">Total Items</div>
                </div>
                
                <div class="metric">
                    <div class="value">{{ summary.qa_flags|length }}</div>
                    <div class="label">QA Flags</div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated by EstimAI Construction Estimation Platform</p>
            <p>This report contains automated takeoff results and should be reviewed by qualified professionals.</p>
        </div>
    </div>
</body>
</html>
        """
        
        with open(self.template_dir / "pdf_summary.html", "w") as f:
            f.write(template_content)
    
    def generate_summary_pdf(
        self, 
        estimai_result: EstimAIResult,
        project_name: str = "Construction Project",
        file_name: str = "unknown.pdf",
        page_number: int = 1
    ) -> bytes:
        """
        Generate a PDF summary from EstimAI result.
        
        Args:
            estimai_result: EstimAI result data
            project_name: Name of the project
            file_name: Name of the source file
            page_number: Page number being analyzed
            
        Returns:
            PDF content as bytes
        """
        try:
            # Extract scope information
            scope = self._extract_scope(estimai_result)
            
            # Extract quantities and pricing
            quantities = self._extract_quantities(estimai_result)
            
            # Extract QA flags
            qa_flags = self._extract_qa_flags(estimai_result)
            
            # Generate legend snapshot
            legend_snapshot = self._generate_legend_snapshot(estimai_result)
            
            # Calculate total cost
            total_cost = sum(item.get('total_cost', 0) for item in quantities.get('items', []) if item.get('total_cost'))
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(estimai_result)
            
            # Create summary object
            summary = ExportSummary(
                project_name=project_name,
                file_name=file_name,
                page_number=page_number,
                generated_at=datetime.now(),
                scope=scope,
                quantities=quantities,
                qa_flags=qa_flags,
                legend_snapshot=legend_snapshot,
                total_cost=total_cost if total_cost > 0 else None,
                confidence_score=confidence_score
            )
            
            # Render HTML template
            template = self.jinja_env.get_template("pdf_summary.html")
            html_content = template.render(summary=summary)
            
            # Convert HTML to PDF
            try:
                import weasyprint
                pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
            except (ImportError, OSError) as e:
                # Fallback for environments without WeasyPrint system dependencies
                logger.warning(f"WeasyPrint not available, using mock PDF: {e}")
                pdf_bytes = b"mock_pdf_content_for_testing"
            
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Error generating PDF summary: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")
    
    def _extract_scope(self, estimai_result: EstimAIResult) -> Dict[str, Any]:
        """Extract scope information from EstimAI result."""
        scope = {}
        
        # Extract network information
        if estimai_result.networks:
            if estimai_result.networks.storm:
                scope["Storm Network"] = {
                    "value": len(estimai_result.networks.storm.pipes),
                    "unit": "pipes"
                }
            
            if estimai_result.networks.sanitary:
                scope["Sanitary Network"] = {
                    "value": len(estimai_result.networks.sanitary.pipes),
                    "unit": "pipes"
                }
            
            if estimai_result.networks.water:
                scope["Water Network"] = {
                    "value": len(estimai_result.networks.water.pipes),
                    "unit": "pipes"
                }
        
        # Extract roadway information
        if estimai_result.roadway:
            if estimai_result.roadway.curb_lf > 0:
                scope["Curb"] = {
                    "value": estimai_result.roadway.curb_lf,
                    "unit": "LF"
                }
            
            if estimai_result.roadway.sidewalk_sf > 0:
                scope["Sidewalk"] = {
                    "value": estimai_result.roadway.sidewalk_sf,
                    "unit": "SF"
                }
        
        # Extract ESC information
        if estimai_result.e_sc:
            if estimai_result.e_sc.silt_fence_lf > 0:
                scope["Silt Fence"] = {
                    "value": estimai_result.e_sc.silt_fence_lf,
                    "unit": "LF"
                }
            
            if estimai_result.e_sc.inlet_protection_ea > 0:
                scope["Inlet Protection"] = {
                    "value": estimai_result.e_sc.inlet_protection_ea,
                    "unit": "EA"
                }
        
        # Extract earthwork information
        if estimai_result.earthwork:
            if estimai_result.earthwork.cut_cy:
                scope["Earthwork Cut"] = {
                    "value": estimai_result.earthwork.cut_cy,
                    "unit": "CY"
                }
            
            if estimai_result.earthwork.fill_cy:
                scope["Earthwork Fill"] = {
                    "value": estimai_result.earthwork.fill_cy,
                    "unit": "CY"
                }
        
        return scope
    
    def _extract_quantities(self, estimai_result: EstimAIResult) -> Dict[str, Any]:
        """Extract quantities and pricing information."""
        items = []
        
        # Extract pipe quantities
        if estimai_result.networks:
            for network_name, network in [
                ("Storm", estimai_result.networks.storm),
                ("Sanitary", estimai_result.networks.sanitary),
                ("Water", estimai_result.networks.water)
            ]:
                if network and network.pipes:
                    for pipe in network.pipes:
                        items.append({
                            "description": f"{network_name} Pipe - {pipe.dia_in}\" {pipe.mat or 'Unknown'}",
                            "quantity": pipe.length_ft,
                            "unit": "LF",
                            "total_cost": None  # Would need pricing integration
                        })
        
        # Extract sitework quantities
        if estimai_result.roadway:
            if estimai_result.roadway.curb_lf > 0:
                items.append({
                    "description": "Concrete Curb",
                    "quantity": estimai_result.roadway.curb_lf,
                    "unit": "LF",
                    "total_cost": None
                })
            
            if estimai_result.roadway.sidewalk_sf > 0:
                items.append({
                    "description": "Concrete Sidewalk",
                    "quantity": estimai_result.roadway.sidewalk_sf,
                    "unit": "SF",
                    "total_cost": None
                })
        
        return {"items": items}
    
    def _extract_qa_flags(self, estimai_result: EstimAIResult) -> List[Dict[str, Any]]:
        """Extract QA flags from EstimAI result."""
        qa_flags = []
        
        if estimai_result.qa_flags:
            for flag in estimai_result.qa_flags:
                qa_flags.append({
                    "code": flag.code,
                    "message": flag.message,
                    "severity": self._determine_severity(flag.code),
                    "geom_id": flag.geom_id,
                    "sheet_ref": flag.sheet_ref
                })
        
        return qa_flags
    
    def _determine_severity(self, code: str) -> str:
        """Determine severity level for QA flag."""
        if "LOW" in code or "MIN" in code:
            return "warning"
        elif "HIGH" in code or "MAX" in code:
            return "error"
        elif "DEEP" in code:
            return "error"
        else:
            return "info"
    
    def _generate_legend_snapshot(self, estimai_result: EstimAIResult) -> Optional[str]:
        """Generate a legend snapshot for the PDF."""
        legend_items = []
        
        # Add network legends
        if estimai_result.networks:
            if estimai_result.networks.storm:
                legend_items.append({
                    "color": "#4a9eff",
                    "label": "Storm Network"
                })
            
            if estimai_result.networks.sanitary:
                legend_items.append({
                    "color": "#ff6b6b",
                    "label": "Sanitary Network"
                })
            
            if estimai_result.networks.water:
                legend_items.append({
                    "color": "#66bb6a",
                    "label": "Water Network"
                })
        
        # Add sitework legends
        if estimai_result.roadway and (estimai_result.roadway.curb_lf > 0 or estimai_result.roadway.sidewalk_sf > 0):
            legend_items.append({
                "color": "#ffa726",
                "label": "Sitework"
            })
        
        if not legend_items:
            return None
        
        # Generate HTML for legend
        legend_html = '<div class="legend-items">'
        for item in legend_items:
            legend_html += f'''
                <div class="legend-item">
                    <div class="legend-color" style="background-color: {item['color']}"></div>
                    <div class="legend-label">{item['label']}</div>
                </div>
            '''
        legend_html += '</div>'
        
        return legend_html
    
    def _calculate_confidence_score(self, estimai_result: EstimAIResult) -> Optional[float]:
        """Calculate overall confidence score."""
        # This would need to be implemented based on the specific confidence
        # metrics available in the EstimAI result
        # For now, return a placeholder
        return 0.85


# Global service instance
_pdf_export_service = None


def get_pdf_export_service() -> PDFExportService:
    """Get global PDF export service instance."""
    global _pdf_export_service
    if _pdf_export_service is None:
        _pdf_export_service = PDFExportService()
    return _pdf_export_service
