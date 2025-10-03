"""Quality Assurance rules for construction drawings."""
import json
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

from ..ingest.extract import VectorEl, TextEl
from ...domain.networks import Node, Edge, Network
from .earthwork_tables import EarthworkTable, CutFillSummary

logger = logging.getLogger(__name__)


@dataclass
class QARule:
    """Quality Assurance rule definition."""
    rule_id: str
    name: str
    description: str
    severity: str  # "error", "warning", "info"
    category: str  # "sewer", "ada", "schedule", etc.


@dataclass
class QAViolation:
    """Quality Assurance violation."""
    rule_id: str
    severity: str
    message: str
    location: Optional[Tuple[float, float]] = None
    details: Dict[str, Any] = None


class QARulesEngine:
    """Quality Assurance rules engine."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize QA rules engine."""
        self.config_path = config_path or "config/qa/nc.json"
        self.config = self._load_config()
        self.rules = self._initialize_rules()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load QA configuration."""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"QA config file not found: {self.config_path}")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading QA config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default QA configuration."""
        return {
            "sewer": {
                "min_slope_percent": 0.5,
                "min_cover_ft": 3.0,
                "max_slope_percent": 10.0
            },
            "ada": {
                "max_ramp_slope_percent": 8.33,
                "min_ramp_width_ft": 3.0,
                "max_cross_slope_percent": 2.0
            },
            "schedule": {
                "tolerance_percent": 10.0
            }
        }
    
    def _initialize_rules(self) -> List[QARule]:
        """Initialize QA rules."""
        rules = [
            QARule(
                rule_id="sewer_min_slope",
                name="Sewer Minimum Slope",
                description="Check sewer lines meet minimum slope requirements",
                severity="error",
                category="sewer"
            ),
            QARule(
                rule_id="sewer_min_cover",
                name="Sewer Minimum Cover",
                description="Check sewer lines have adequate cover",
                severity="error",
                category="sewer"
            ),
            QARule(
                rule_id="ada_ramp_slope",
                name="ADA Ramp Slope",
                description="Check ADA ramp slopes meet requirements",
                severity="error",
                category="ada"
            ),
            QARule(
                rule_id="ada_ramp_width",
                name="ADA Ramp Width",
                description="Check ADA ramp widths meet requirements",
                severity="error",
                category="ada"
            ),
            QARule(
                rule_id="schedule_reconciliation",
                name="Schedule Reconciliation",
                description="Check schedule vs measured quantities",
                severity="warning",
                category="schedule"
            )
        ]
        return rules
    
    def check_sewer_rules(self, network: Network) -> List[QAViolation]:
        """Check sewer network rules."""
        violations = []
        
        for edge in network.edges:
            # Check minimum slope
            if edge.slope_percent is not None:
                min_slope = self.config.get("sewer", {}).get("min_slope_percent", 0.5)
                if edge.slope_percent < min_slope:
                    violations.append(QAViolation(
                        rule_id="sewer_min_slope",
                        severity="error",
                        message=f"Sewer line {edge.id} has slope {edge.slope_percent:.2f}% < minimum {min_slope}%",
                        location=(edge.points_ft[0][0], edge.points_ft[0][1]) if edge.points_ft else None,
                        details={"edge_id": edge.id, "slope_percent": edge.slope_percent, "min_required": min_slope}
                    ))
                
                # Check maximum slope
                max_slope = self.config.get("sewer", {}).get("max_slope_percent", 10.0)
                if edge.slope_percent > max_slope:
                    violations.append(QAViolation(
                        rule_id="sewer_max_slope",
                        severity="warning",
                        message=f"Sewer line {edge.id} has slope {edge.slope_percent:.2f}% > maximum {max_slope}%",
                        location=(edge.points_ft[0][0], edge.points_ft[0][1]) if edge.points_ft else None,
                        details={"edge_id": edge.id, "slope_percent": edge.slope_percent, "max_allowed": max_slope}
                    ))
        
        return violations
    
    def check_ada_rules(self, vectors: List[VectorEl], texts: List[TextEl]) -> List[QAViolation]:
        """Check ADA compliance rules."""
        violations = []
        
        # Find ADA ramp vectors
        ramp_vectors = self._find_ada_ramps(vectors)
        
        for ramp in ramp_vectors:
            # Check ramp slope
            slope = self._calculate_ramp_slope(ramp)
            if slope is not None:
                max_slope = self.config.get("ada", {}).get("max_ramp_slope_percent", 8.33)
                if slope > max_slope:
                    violations.append(QAViolation(
                        rule_id="ada_ramp_slope",
                        severity="error",
                        message=f"ADA ramp has slope {slope:.2f}% > maximum {max_slope}%",
                        location=(ramp.points[0][0], ramp.points[0][1]) if ramp.points else None,
                        details={"slope_percent": slope, "max_allowed": max_slope}
                    ))
            
            # Check ramp width
            width = self._calculate_ramp_width(ramp)
            if width is not None:
                min_width = self.config.get("ada", {}).get("min_ramp_width_ft", 3.0)
                if width < min_width:
                    violations.append(QAViolation(
                        rule_id="ada_ramp_width",
                        severity="error",
                        message=f"ADA ramp has width {width:.2f} ft < minimum {min_width} ft",
                        location=(ramp.points[0][0], ramp.points[0][1]) if ramp.points else None,
                        details={"width_ft": width, "min_required": min_width}
                    ))
        
        return violations
    
    def check_schedule_reconciliation(
        self, 
        earthwork_tables: List[EarthworkTable], 
        measured_quantities: Dict[str, float]
    ) -> List[QAViolation]:
        """Check schedule vs measured quantities reconciliation."""
        violations = []
        
        tolerance_percent = self.config.get("schedule", {}).get("tolerance_percent", 10.0)
        
        for table in earthwork_tables:
            # Compare table totals with measured quantities
            if "earthwork_cut_yd3" in measured_quantities:
                table_cut = table.total_cut_yd3
                measured_cut = measured_quantities["earthwork_cut_yd3"]
                
                if table_cut > 0:
                    difference_percent = abs(measured_cut - table_cut) / table_cut * 100
                    if difference_percent > tolerance_percent:
                        violations.append(QAViolation(
                            rule_id="schedule_reconciliation",
                            severity="warning",
                            message=f"Earthwork cut: table {table_cut:.1f} YD3 vs measured {measured_cut:.1f} YD3 ({difference_percent:.1f}% difference)",
                            details={
                                "table_cut_yd3": table_cut,
                                "measured_cut_yd3": measured_cut,
                                "difference_percent": difference_percent,
                                "tolerance_percent": tolerance_percent
                            }
                        ))
            
            if "earthwork_fill_yd3" in measured_quantities:
                table_fill = table.total_fill_yd3
                measured_fill = measured_quantities["earthwork_fill_yd3"]
                
                if table_fill > 0:
                    difference_percent = abs(measured_fill - table_fill) / table_fill * 100
                    if difference_percent > tolerance_percent:
                        violations.append(QAViolation(
                            rule_id="schedule_reconciliation",
                            severity="warning",
                            message=f"Earthwork fill: table {table_fill:.1f} YD3 vs measured {measured_fill:.1f} YD3 ({difference_percent:.1f}% difference)",
                            details={
                                "table_fill_yd3": table_fill,
                                "measured_fill_yd3": measured_fill,
                                "difference_percent": difference_percent,
                                "tolerance_percent": tolerance_percent
                            }
                        ))
        
        return violations
    
    def _find_ada_ramps(self, vectors: List[VectorEl]) -> List[VectorEl]:
        """Find ADA ramp vectors."""
        ramp_vectors = []
        
        for vector in vectors:
            if self._is_ada_ramp(vector):
                ramp_vectors.append(vector)
        
        return ramp_vectors
    
    def _is_ada_ramp(self, vector: VectorEl) -> bool:
        """Check if vector represents an ADA ramp."""
        # Look for ramp characteristics
        if vector.kind in ["line", "polyline"] and vector.stroke_w > 0:
            # Check for ramp patterns (sloped lines)
            if len(vector.points) >= 2:
                # Calculate slope
                slope = self._calculate_ramp_slope(vector)
                if slope is not None and 0 < slope < 20:  # Reasonable ramp slope range
                    return True
        
        return False
    
    def _calculate_ramp_slope(self, vector: VectorEl) -> Optional[float]:
        """Calculate ramp slope percentage."""
        if len(vector.points) < 2:
            return None
        
        # Find start and end points
        start_point = vector.points[0]
        end_point = vector.points[-1]
        
        # Calculate horizontal distance
        horizontal_distance = math.sqrt(
            (end_point[0] - start_point[0]) ** 2 + 
            (end_point[1] - start_point[1]) ** 2
        )
        
        if horizontal_distance == 0:
            return None
        
        # For now, assume elevation difference is encoded in stroke width or attributes
        # In a real implementation, you'd need elevation data
        elevation_diff = vector.stroke_w * 0.1  # Simplified assumption
        
        slope_percent = (elevation_diff / horizontal_distance) * 100
        return slope_percent
    
    def _calculate_ramp_width(self, vector: VectorEl) -> Optional[float]:
        """Calculate ramp width."""
        if len(vector.points) < 2:
            return None
        
        # For now, use stroke width as proxy for ramp width
        # In a real implementation, you'd need to measure perpendicular distance
        return vector.stroke_w * 2.0  # Simplified assumption
    
    def run_all_checks(
        self, 
        networks: List[Network], 
        vectors: List[VectorEl], 
        texts: List[TextEl],
        earthwork_tables: List[EarthworkTable],
        measured_quantities: Dict[str, float]
    ) -> List[QAViolation]:
        """Run all QA checks."""
        all_violations = []
        
        # Check sewer networks
        for network in networks:
            if network.network_type == "sanitary":
                violations = self.check_sewer_rules(network)
                all_violations.extend(violations)
        
        # Check ADA compliance
        ada_violations = self.check_ada_rules(vectors, texts)
        all_violations.extend(ada_violations)
        
        # Check schedule reconciliation
        schedule_violations = self.check_schedule_reconciliation(earthwork_tables, measured_quantities)
        all_violations.extend(schedule_violations)
        
        logger.info(f"QA check completed: {len(all_violations)} violations found")
        return all_violations
    
    def export_violations(self, violations: List[QAViolation], file_path: str) -> bool:
        """Export QA violations to JSON file."""
        try:
            data = []
            for violation in violations:
                violation_data = {
                    "rule_id": violation.rule_id,
                    "severity": violation.severity,
                    "message": violation.message,
                    "location": violation.location,
                    "details": violation.details
                }
                data.append(violation_data)
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"QA violations exported to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting QA violations: {e}")
            return False
    
    def get_rule_summary(self, violations: List[QAViolation]) -> Dict[str, Any]:
        """Get summary of QA violations by rule."""
        summary = {
            "total_violations": len(violations),
            "by_severity": {},
            "by_rule": {},
            "by_category": {}
        }
        
        for violation in violations:
            # By severity
            severity = violation.severity
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
            
            # By rule
            rule_id = violation.rule_id
            summary["by_rule"][rule_id] = summary["by_rule"].get(rule_id, 0) + 1
            
            # By category
            rule = next((r for r in self.rules if r.rule_id == rule_id), None)
            if rule:
                category = rule.category
                summary["by_category"][category] = summary["by_category"].get(category, 0) + 1
        
        return summary
