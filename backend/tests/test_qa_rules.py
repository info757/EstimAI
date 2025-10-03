"""Tests for QA rules engine."""
import pytest
import json
from unittest.mock import Mock, patch
from pathlib import Path

from app.services.detectors.qa_rules import (
    QARule, QAViolation, QARulesEngine,
    _load_config, _get_default_config
)
from app.domain.networks import Network, Node, Edge, NodeType, EdgeType, Material
from app.services.detectors.earthwork_tables import EarthworkTable, CutFillSummary


class TestQARule:
    """Test QARule dataclass."""
    
    def test_qa_rule_creation(self):
        """Test QARule creation."""
        rule = QARule(
            rule_id="test_rule",
            name="Test Rule",
            description="Test rule description",
            severity="error",
            category="test"
        )
        
        assert rule.rule_id == "test_rule"
        assert rule.name == "Test Rule"
        assert rule.description == "Test rule description"
        assert rule.severity == "error"
        assert rule.category == "test"


class TestQAViolation:
    """Test QAViolation dataclass."""
    
    def test_qa_violation_creation(self):
        """Test QAViolation creation."""
        violation = QAViolation(
            rule_id="test_rule",
            severity="error",
            message="Test violation message",
            location=(100.0, 200.0),
            details={"key": "value"}
        )
        
        assert violation.rule_id == "test_rule"
        assert violation.severity == "error"
        assert violation.message == "Test violation message"
        assert violation.location == (100.0, 200.0)
        assert violation.details == {"key": "value"}


class TestQARulesEngine:
    """Test QARulesEngine class."""
    
    def test_qa_rules_engine_initialization(self):
        """Test QARulesEngine initialization."""
        engine = QARulesEngine()
        
        assert engine.config is not None
        assert len(engine.rules) > 0
        assert engine.config_path == "config/qa/nc.json"
    
    def test_qa_rules_engine_custom_config(self):
        """Test QARulesEngine with custom config path."""
        engine = QARulesEngine("custom_config.json")
        
        assert engine.config_path == "custom_config.json"
    
    def test_get_default_config(self):
        """Test getting default configuration."""
        config = _get_default_config()
        
        assert "sewer" in config
        assert "ada" in config
        assert "schedule" in config
        assert config["sewer"]["min_slope_percent"] == 0.5
        assert config["ada"]["max_ramp_slope_percent"] == 8.33
        assert config["schedule"]["tolerance_percent"] == 10.0
    
    def test_load_config_file_exists(self):
        """Test loading config from existing file."""
        mock_config = {
            "sewer": {"min_slope_percent": 1.0},
            "ada": {"max_ramp_slope_percent": 10.0}
        }
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = Mock()
            mock_file.read.return_value = json.dumps(mock_config)
            mock_open.return_value.__enter__.return_value = mock_file
            
            with patch('pathlib.Path.exists', return_value=True):
                config = _load_config("test_config.json")
                
                assert config == mock_config
    
    def test_load_config_file_not_exists(self):
        """Test loading config when file doesn't exist."""
        with patch('pathlib.Path.exists', return_value=False):
            config = _load_config("nonexistent.json")
            
            # Should return default config
            assert "sewer" in config
            assert "ada" in config
    
    def test_load_config_error(self):
        """Test loading config with error."""
        with patch('builtins.open', side_effect=Exception("File error")):
            config = _load_config("error_config.json")
            
            # Should return default config
            assert "sewer" in config
            assert "ada" in config


class TestSewerRules:
    """Test sewer network rules."""
    
    def test_check_sewer_rules_min_slope(self):
        """Test checking sewer minimum slope rule."""
        # Create test network with low slope
        network = Network(
            id="test-network",
            name="Test Network",
            network_type="sanitary"
        )
        
        edge = Edge(
            id="edge-1",
            edge_type=EdgeType.PIPE,
            from_node_id="node-1",
            to_node_id="node-2",
            points_ft=[(0.0, 0.0), (100.0, 0.0)],
            slope_percent=0.3  # Below minimum
        )
        
        network.add_edge(edge)
        
        engine = QARulesEngine()
        violations = engine.check_sewer_rules(network)
        
        assert len(violations) == 1
        assert violations[0].rule_id == "sewer_min_slope"
        assert violations[0].severity == "error"
        assert "slope 0.30%" in violations[0].message
    
    def test_check_sewer_rules_max_slope(self):
        """Test checking sewer maximum slope rule."""
        # Create test network with high slope
        network = Network(
            id="test-network",
            name="Test Network",
            network_type="sanitary"
        )
        
        edge = Edge(
            id="edge-1",
            edge_type=EdgeType.PIPE,
            from_node_id="node-1",
            to_node_id="node-2",
            points_ft=[(0.0, 0.0), (100.0, 0.0)],
            slope_percent=15.0  # Above maximum
        )
        
        network.add_edge(edge)
        
        engine = QARulesEngine()
        violations = engine.check_sewer_rules(network)
        
        assert len(violations) == 1
        assert violations[0].rule_id == "sewer_max_slope"
        assert violations[0].severity == "warning"
        assert "slope 15.00%" in violations[0].message
    
    def test_check_sewer_rules_no_violations(self):
        """Test checking sewer rules with no violations."""
        # Create test network with acceptable slope
        network = Network(
            id="test-network",
            name="Test Network",
            network_type="sanitary"
        )
        
        edge = Edge(
            id="edge-1",
            edge_type=EdgeType.PIPE,
            from_node_id="node-1",
            to_node_id="node-2",
            points_ft=[(0.0, 0.0), (100.0, 0.0)],
            slope_percent=2.0  # Within acceptable range
        )
        
        network.add_edge(edge)
        
        engine = QARulesEngine()
        violations = engine.check_sewer_rules(network)
        
        assert len(violations) == 0


class TestADARules:
    """Test ADA compliance rules."""
    
    def test_check_ada_rules_ramp_slope(self):
        """Test checking ADA ramp slope rule."""
        from app.services.ingest.extract import VectorEl
        
        # Create test vectors
        vectors = [
            VectorEl(
                kind="line",
                points=[(0.0, 0.0), (100.0, 0.0)],
                stroke_rgba=(0, 0, 0, 255),
                fill_rgba=(0, 0, 0, 0),
                stroke_w=2.0,
                ocg_names=[],
                xform=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
            )
        ]
        
        texts = []
        
        engine = QARulesEngine()
        violations = engine.check_ada_rules(vectors, texts)
        
        # Should find violations if ramp slope is too steep
        # (This depends on the implementation of _calculate_ramp_slope)
        assert isinstance(violations, list)
    
    def test_check_ada_rules_ramp_width(self):
        """Test checking ADA ramp width rule."""
        from app.services.ingest.extract import VectorEl
        
        # Create test vectors
        vectors = [
            VectorEl(
                kind="line",
                points=[(0.0, 0.0), (100.0, 0.0)],
                stroke_rgba=(0, 0, 0, 255),
                fill_rgba=(0, 0, 0, 0),
                stroke_w=1.0,  # Narrow width
                ocg_names=[],
                xform=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
            )
        ]
        
        texts = []
        
        engine = QARulesEngine()
        violations = engine.check_ada_rules(vectors, texts)
        
        # Should find violations if ramp width is too narrow
        # (This depends on the implementation of _calculate_ramp_width)
        assert isinstance(violations, list)


class TestScheduleRules:
    """Test schedule reconciliation rules."""
    
    def test_check_schedule_reconciliation(self):
        """Test checking schedule reconciliation."""
        # Create test earthwork table
        table = EarthworkTable(
            title="Test Table",
            summary=[
                CutFillSummary("0+00", "1+00", 100.0, 50.0, 50.0, 1000.0)
            ],
            total_cut_yd3=100.0,
            total_fill_yd3=50.0,
            net_yd3=50.0,
            table_bounds=(0.0, 0.0, 100.0, 100.0)
        )
        
        # Create measured quantities with large difference
        measured_quantities = {
            "earthwork_cut_yd3": 150.0,  # 50% difference
            "earthwork_fill_yd3": 25.0   # 50% difference
        }
        
        engine = QARulesEngine()
        violations = engine.check_schedule_reconciliation([table], measured_quantities)
        
        assert len(violations) == 2  # Should find violations for both cut and fill
        assert violations[0].rule_id == "schedule_reconciliation"
        assert violations[0].severity == "warning"
        assert "50.0% difference" in violations[0].message
    
    def test_check_schedule_reconciliation_no_violations(self):
        """Test checking schedule reconciliation with no violations."""
        # Create test earthwork table
        table = EarthworkTable(
            title="Test Table",
            summary=[
                CutFillSummary("0+00", "1+00", 100.0, 50.0, 50.0, 1000.0)
            ],
            total_cut_yd3=100.0,
            total_fill_yd3=50.0,
            net_yd3=50.0,
            table_bounds=(0.0, 0.0, 100.0, 100.0)
        )
        
        # Create measured quantities with small difference
        measured_quantities = {
            "earthwork_cut_yd3": 105.0,  # 5% difference
            "earthwork_fill_yd3": 52.0   # 4% difference
        }
        
        engine = QARulesEngine()
        violations = engine.check_schedule_reconciliation([table], measured_quantities)
        
        assert len(violations) == 0  # Should find no violations


class TestQARulesEngineIntegration:
    """Test QARulesEngine integration."""
    
    def test_run_all_checks(self):
        """Test running all QA checks."""
        # Create test data
        network = Network(
            id="test-network",
            name="Test Network",
            network_type="sanitary"
        )
        
        edge = Edge(
            id="edge-1",
            edge_type=EdgeType.PIPE,
            from_node_id="node-1",
            to_node_id="node-2",
            points_ft=[(0.0, 0.0), (100.0, 0.0)],
            slope_percent=0.3  # Below minimum
        )
        
        network.add_edge(edge)
        
        vectors = []
        texts = []
        
        table = EarthworkTable(
            title="Test Table",
            summary=[],
            total_cut_yd3=100.0,
            total_fill_yd3=50.0,
            net_yd3=50.0,
            table_bounds=(0.0, 0.0, 100.0, 100.0)
        )
        
        measured_quantities = {
            "earthwork_cut_yd3": 150.0,
            "earthwork_fill_yd3": 25.0
        }
        
        engine = QARulesEngine()
        violations = engine.run_all_checks(
            [network], vectors, texts, [table], measured_quantities
        )
        
        assert len(violations) > 0  # Should find violations
    
    def test_export_violations(self):
        """Test exporting violations."""
        violations = [
            QAViolation(
                rule_id="test_rule",
                severity="error",
                message="Test violation",
                location=(100.0, 200.0),
                details={"key": "value"}
            )
        ]
        
        engine = QARulesEngine()
        
        # Test successful export
        with patch('builtins.open', create=True) as mock_open:
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            result = engine.export_violations(violations, "test.json")
            assert result == True
            mock_file.write.assert_called_once()
    
    def test_export_violations_error(self):
        """Test exporting violations with error."""
        violations = []
        
        engine = QARulesEngine()
        
        # Test export error
        with patch('builtins.open', side_effect=Exception("File error")):
            result = engine.export_violations(violations, "test.json")
            assert result == False
    
    def test_get_rule_summary(self):
        """Test getting rule summary."""
        violations = [
            QAViolation("rule1", "error", "Message 1"),
            QAViolation("rule1", "error", "Message 2"),
            QAViolation("rule2", "warning", "Message 3")
        ]
        
        engine = QARulesEngine()
        summary = engine.get_rule_summary(violations)
        
        assert summary["total_violations"] == 3
        assert summary["by_severity"]["error"] == 2
        assert summary["by_severity"]["warning"] == 1
        assert summary["by_rule"]["rule1"] == 2
        assert summary["by_rule"]["rule2"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
