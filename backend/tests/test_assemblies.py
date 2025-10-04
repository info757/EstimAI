"""
Unit tests for assemblies mapping and pricing.

Tests the mapping of count items to construction assemblies with CSI codes,
pricing calculations, and stable key generation.
"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from backend.app.services.assemblies import (
    AssembliesMapper, AssemblyMapping, PricingItem, AssemblyType,
    map_count_items_to_assemblies, get_assemblies_mapper
)


class TestAssembliesMapper:
    """Test cases for AssembliesMapper."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.config_dir.mkdir(parents=True)
        
        # Create test configuration files
        self._create_test_configs()
        
        self.mapper = AssembliesMapper(str(self.config_dir))
    
    def _create_test_configs(self):
        """Create test configuration files."""
        # Create pricing config
        pricing_config = {
            "unit_costs": {
                "33-1000": {"description": "Storm Pipe - 12\" Concrete", "unit": "LF", "cost": 45.00},
                "33-2000": {"description": "Sanitary Pipe - 8\" PVC", "unit": "LF", "cost": 25.00},
                "33-3000": {"description": "Water Pipe - 6\" Ductile Iron", "unit": "LF", "cost": 35.00},
                "33-4000": {"description": "Trench Excavation - 0-5ft", "unit": "CY", "cost": 15.00},
                "33-5000": {"description": "Manhole - 4ft Diameter", "unit": "EA", "cost": 2500.00},
                "33-6000": {"description": "Curb - Concrete", "unit": "LF", "cost": 12.00}
            },
            "markup_percent": 15.0,
            "labor_factor": 1.25,
            "equipment_factor": 1.15
        }
        
        with open(self.config_dir / "pricing" / "assemblies.json", 'w') as f:
            json.dump(pricing_config, f)
        
        # Create assembly mappings
        assembly_mappings = {
            "pipe_mappings": {
                "storm": {"12": "33-1000", "15": "33-1001"},
                "sanitary": {"8": "33-2000", "10": "33-2001"},
                "water": {"6": "33-3000", "8": "33-3001"}
            },
            "trench_mappings": {
                "0-5": "33-4000",
                "5-8": "33-4001",
                "8-12": "33-4002",
                "12+": "33-4003"
            },
            "structure_mappings": {
                "manhole": "33-5000",
                "inlet": "33-5001"
            },
            "sitework_mappings": {
                "curb": "33-6000",
                "sidewalk": "33-6001"
            }
        }
        
        with open(self.config_dir / "assemblies" / "mappings.json", 'w') as f:
            json.dump(assembly_mappings, f)
    
    def test_mapper_initialization(self):
        """Test mapper initialization."""
        assert self.mapper.config_dir == self.config_dir
        assert self.mapper.pricing_config is not None
        assert self.mapper.assembly_mappings is not None
    
    def test_load_pricing_config(self):
        """Test loading pricing configuration."""
        config = self.mapper._load_pricing_config()
        
        assert "unit_costs" in config
        assert "33-1000" in config["unit_costs"]
        assert config["unit_costs"]["33-1000"]["cost"] == 45.00
        assert config["markup_percent"] == 15.0
    
    def test_load_assembly_mappings(self):
        """Test loading assembly mappings."""
        mappings = self.mapper._load_assembly_mappings()
        
        assert "pipe_mappings" in mappings
        assert "storm" in mappings["pipe_mappings"]
        assert mappings["pipe_mappings"]["storm"]["12"] == "33-1000"
    
    def test_map_pipe_to_assemblies(self):
        """Test mapping pipe data to assemblies."""
        pipe_data = {
            'type': 'storm',
            'dia_in': 12,
            'length_ft': 100.0,
            'mat': 'concrete',
            'extra': {
                'buckets_lf': {
                    '0-5': 50.0,
                    '5-8': 30.0,
                    '8-12': 20.0
                },
                'trench_volume_cy': 25.0
            }
        }
        
        assemblies = self.mapper.map_pipe_to_assemblies(pipe_data)
        
        assert len(assemblies) >= 1  # At least the main pipe assembly
        
        # Check main pipe assembly
        pipe_assembly = next((a for a in assemblies if a.assembly_type == AssemblyType.PIPE), None)
        assert pipe_assembly is not None
        assert pipe_assembly.csi_code == "33-1000"
        assert pipe_assembly.quantity == 100.0
        assert pipe_assembly.unit == "LF"
        
        # Check trench assemblies
        trench_assemblies = [a for a in assemblies if a.assembly_type == AssemblyType.TRENCH]
        assert len(trench_assemblies) >= 1
    
    def test_map_sitework_to_assemblies(self):
        """Test mapping sitework data to assemblies."""
        sitework_data = {
            'curb_lf': 200.0,
            'sidewalk_sf': 400.0,
            'silt_fence_lf': 100.0
        }
        
        assemblies = self.mapper.map_sitework_to_assemblies(sitework_data)
        
        assert len(assemblies) == 3
        
        # Check curb
        curb_assembly = next((a for a in assemblies if 'curb' in a.description.lower()), None)
        assert curb_assembly is not None
        assert curb_assembly.quantity == 200.0
        assert curb_assembly.unit == "LF"
        
        # Check sidewalk
        sidewalk_assembly = next((a for a in assemblies if 'sidewalk' in a.description.lower()), None)
        assert sidewalk_assembly is not None
        assert sidewalk_assembly.quantity == 400.0
        assert sidewalk_assembly.unit == "SF"
    
    def test_map_structures_to_assemblies(self):
        """Test mapping structure data to assemblies."""
        structures_data = [
            {'type': 'manhole', 'count': 2},
            {'type': 'inlet', 'count': 4}
        ]
        
        assemblies = self.mapper.map_structures_to_assemblies(structures_data)
        
        assert len(assemblies) == 2
        
        # Check manhole
        manhole_assembly = next((a for a in assemblies if 'manhole' in a.description.lower()), None)
        assert manhole_assembly is not None
        assert manhole_assembly.quantity == 2
        assert manhole_assembly.unit == "EA"
        
        # Check inlet
        inlet_assembly = next((a for a in assemblies if 'inlet' in a.description.lower()), None)
        assert inlet_assembly is not None
        assert inlet_assembly.quantity == 4
        assert inlet_assembly.unit == "EA"
    
    def test_get_pipe_csi_code(self):
        """Test getting CSI code for pipe."""
        # Test exact match
        csi_code = self.mapper._get_pipe_csi_code('storm', 12)
        assert csi_code == "33-1000"
        
        # Test closest match
        csi_code = self.mapper._get_pipe_csi_code('storm', 13)
        assert csi_code == "33-1000"  # Should match closest (12)
        
        # Test unknown type
        csi_code = self.mapper._get_pipe_csi_code('unknown', 12)
        assert csi_code is None
    
    def test_get_trench_csi_code(self):
        """Test getting CSI code for trench."""
        csi_code = self.mapper._get_trench_csi_code('0-5')
        assert csi_code == "33-4000"
        
        csi_code = self.mapper._get_trench_csi_code('5-8')
        assert csi_code == "33-4001"
        
        csi_code = self.mapper._get_trench_csi_code('unknown')
        assert csi_code is None
    
    def test_get_structure_csi_code(self):
        """Test getting CSI code for structure."""
        csi_code = self.mapper._get_structure_csi_code('manhole')
        assert csi_code == "33-5000"
        
        csi_code = self.mapper._get_structure_csi_code('inlet')
        assert csi_code == "33-5001"
        
        csi_code = self.mapper._get_structure_csi_code('unknown')
        assert csi_code is None
    
    def test_calculate_pricing(self):
        """Test pricing calculation."""
        assemblies = [
            AssemblyMapping(
                csi_code="33-1000",
                assembly_type=AssemblyType.PIPE,
                description="Storm Pipe - 12\" Concrete",
                unit="LF",
                quantity=100.0,
                attributes={},
                pricing_key="storm_12_concrete"
            ),
            AssemblyMapping(
                csi_code="33-4000",
                assembly_type=AssemblyType.TRENCH,
                description="Trench Excavation - 0-5ft",
                unit="CY",
                quantity=25.0,
                attributes={},
                pricing_key="trench_0-5"
            )
        ]
        
        pricing_items = self.mapper.calculate_pricing(assemblies)
        
        assert len(pricing_items) == 2
        
        # Check pipe pricing
        pipe_pricing = next((p for p in pricing_items if p.csi_code == "33-1000"), None)
        assert pipe_pricing is not None
        assert pipe_pricing.unit_cost == 45.00
        assert pipe_pricing.total_cost == 4500.00  # 100 * 45
        
        # Check trench pricing
        trench_pricing = next((p for p in pricing_items if p.csi_code == "33-4000"), None)
        assert trench_pricing is not None
        assert trench_pricing.unit_cost == 15.00
        assert trench_pricing.total_cost == 375.00  # 25 * 15
    
    def test_generate_assembly_summary(self):
        """Test assembly summary generation."""
        assemblies = [
            AssemblyMapping(
                csi_code="33-1000",
                assembly_type=AssemblyType.PIPE,
                description="Storm Pipe - 12\" Concrete",
                unit="LF",
                quantity=100.0,
                attributes={},
                pricing_key="storm_12_concrete"
            ),
            AssemblyMapping(
                csi_code="33-1000",
                assembly_type=AssemblyType.PIPE,
                description="Storm Pipe - 12\" Concrete",
                unit="LF",
                quantity=50.0,
                attributes={},
                pricing_key="storm_12_concrete"
            ),
            AssemblyMapping(
                csi_code="33-4000",
                assembly_type=AssemblyType.TRENCH,
                description="Trench Excavation - 0-5ft",
                unit="CY",
                quantity=25.0,
                attributes={},
                pricing_key="trench_0-5"
            )
        ]
        
        summary = self.mapper.generate_assembly_summary(assemblies)
        
        assert summary["total_assemblies"] == 3
        assert summary["by_type"]["pipe"] == 2
        assert summary["by_type"]["trench"] == 1
        assert summary["by_csi_code"]["33-1000"]["quantity"] == 150.0  # 100 + 50
        assert summary["total_quantities"]["LF"] == 150.0
        assert summary["total_quantities"]["CY"] == 25.0


class TestAssemblyMapping:
    """Test cases for AssemblyMapping dataclass."""
    
    def test_assembly_mapping_creation(self):
        """Test AssemblyMapping creation."""
        mapping = AssemblyMapping(
            csi_code="33-1000",
            assembly_type=AssemblyType.PIPE,
            description="Storm Pipe - 12\" Concrete",
            unit="LF",
            quantity=100.0,
            attributes={"diameter": 12, "material": "concrete"},
            pricing_key="storm_12_concrete"
        )
        
        assert mapping.csi_code == "33-1000"
        assert mapping.assembly_type == AssemblyType.PIPE
        assert mapping.description == "Storm Pipe - 12\" Concrete"
        assert mapping.unit == "LF"
        assert mapping.quantity == 100.0
        assert mapping.attributes["diameter"] == 12
        assert mapping.pricing_key == "storm_12_concrete"


class TestPricingItem:
    """Test cases for PricingItem dataclass."""
    
    def test_pricing_item_creation(self):
        """Test PricingItem creation."""
        item = PricingItem(
            csi_code="33-1000",
            description="Storm Pipe - 12\" Concrete",
            unit="LF",
            quantity=100.0,
            unit_cost=45.00,
            total_cost=4500.00,
            attributes={"diameter": 12}
        )
        
        assert item.csi_code == "33-1000"
        assert item.description == "Storm Pipe - 12\" Concrete"
        assert item.unit == "LF"
        assert item.quantity == 100.0
        assert item.unit_cost == 45.00
        assert item.total_cost == 4500.00
        assert item.attributes["diameter"] == 12


class TestMapCountItemsToAssemblies:
    """Test cases for map_count_items_to_assemblies function."""
    
    def test_map_pipe_count_items(self):
        """Test mapping pipe count items to assemblies."""
        count_items = [
            {
                'id': '1',
                'type': 'storm_pipe',
                'quantity': 100.0,
                'attributes': {
                    'diameter_in': 12,
                    'material': 'concrete',
                    'buckets_lf': {
                        '0-5': 50.0,
                        '5-8': 30.0,
                        '8-12': 20.0
                    },
                    'trench_volume_cy': 25.0
                }
            }
        ]
        
        assemblies, pricing_items = map_count_items_to_assemblies(count_items)
        
        assert len(assemblies) >= 1
        assert len(pricing_items) >= 1
        
        # Check pipe assembly
        pipe_assembly = next((a for a in assemblies if a.assembly_type == AssemblyType.PIPE), None)
        assert pipe_assembly is not None
        assert pipe_assembly.quantity == 100.0
    
    def test_map_sitework_count_items(self):
        """Test mapping sitework count items to assemblies."""
        count_items = [
            {
                'id': '1',
                'type': 'curb',
                'quantity': 200.0,
                'attributes': {'material': 'concrete'}
            },
            {
                'id': '2',
                'type': 'sidewalk',
                'quantity': 400.0,
                'attributes': {'material': 'concrete'}
            }
        ]
        
        assemblies, pricing_items = map_count_items_to_assemblies(count_items)
        
        assert len(assemblies) >= 2
        
        # Check curb assembly
        curb_assembly = next((a for a in assemblies if 'curb' in a.description.lower()), None)
        assert curb_assembly is not None
        assert curb_assembly.quantity == 200.0
        
        # Check sidewalk assembly
        sidewalk_assembly = next((a for a in assemblies if 'sidewalk' in a.description.lower()), None)
        assert sidewalk_assembly is not None
        assert sidewalk_assembly.quantity == 400.0
    
    def test_map_structure_count_items(self):
        """Test mapping structure count items to assemblies."""
        count_items = [
            {
                'id': '1',
                'type': 'manhole',
                'quantity': 2,
                'attributes': {'diameter_ft': 4}
            },
            {
                'id': '2',
                'type': 'inlet',
                'quantity': 4,
                'attributes': {'type': 'A'}
            }
        ]
        
        assemblies, pricing_items = map_count_items_to_assemblies(count_items)
        
        assert len(assemblies) >= 2
        
        # Check manhole assembly
        manhole_assembly = next((a for a in assemblies if 'manhole' in a.description.lower()), None)
        assert manhole_assembly is not None
        assert manhole_assembly.quantity == 2
        
        # Check inlet assembly
        inlet_assembly = next((a for a in assemblies if 'inlet' in a.description.lower()), None)
        assert inlet_assembly is not None
        assert inlet_assembly.quantity == 4
    
    def test_empty_count_items(self):
        """Test mapping empty count items."""
        assemblies, pricing_items = map_count_items_to_assemblies([])
        
        assert len(assemblies) == 0
        assert len(pricing_items) == 0
    
    def test_mixed_count_items(self):
        """Test mapping mixed count items."""
        count_items = [
            {
                'id': '1',
                'type': 'storm_pipe',
                'quantity': 100.0,
                'attributes': {
                    'diameter_in': 12,
                    'material': 'concrete',
                    'buckets_lf': {'0-5': 100.0},
                    'trench_volume_cy': 25.0
                }
            },
            {
                'id': '2',
                'type': 'curb',
                'quantity': 200.0,
                'attributes': {'material': 'concrete'}
            },
            {
                'id': '3',
                'type': 'manhole',
                'quantity': 1,
                'attributes': {'diameter_ft': 4}
            }
        ]
        
        assemblies, pricing_items = map_count_items_to_assemblies(count_items)
        
        assert len(assemblies) >= 3
        
        # Check that we have pipe, sitework, and structure assemblies
        assembly_types = {a.assembly_type for a in assemblies}
        assert AssemblyType.PIPE in assembly_types
        assert AssemblyType.SITEWORK in assembly_types
        assert AssemblyType.STRUCTURE in assembly_types


class TestGetAssembliesMapper:
    """Test cases for get_assemblies_mapper function."""
    
    def test_get_assemblies_mapper_singleton(self):
        """Test that get_assemblies_mapper returns singleton instance."""
        mapper1 = get_assemblies_mapper()
        mapper2 = get_assemblies_mapper()
        
        assert mapper1 is mapper2
        assert isinstance(mapper1, AssembliesMapper)


class TestAssemblyType:
    """Test cases for AssemblyType enum."""
    
    def test_assembly_type_values(self):
        """Test AssemblyType enum values."""
        assert AssemblyType.PIPE.value == "pipe"
        assert AssemblyType.TRENCH.value == "trench"
        assert AssemblyType.STRUCTURE.value == "structure"
        assert AssemblyType.SITEWORK.value == "sitework"
        assert AssemblyType.EARTHWORK.value == "earthwork"
    
    def test_assembly_type_enumeration(self):
        """Test AssemblyType enumeration."""
        types = list(AssemblyType)
        assert len(types) == 5
        assert AssemblyType.PIPE in types
        assert AssemblyType.TRENCH in types
        assert AssemblyType.STRUCTURE in types
        assert AssemblyType.SITEWORK in types
        assert AssemblyType.EARTHWORK in types


class TestConfigurationLoading:
    """Test cases for configuration loading."""
    
    def test_default_pricing_config(self):
        """Test default pricing configuration."""
        mapper = AssembliesMapper()
        config = mapper._get_default_pricing_config()
        
        assert "unit_costs" in config
        assert "markup_percent" in config
        assert "labor_factor" in config
        assert "equipment_factor" in config
        
        # Check some unit costs
        unit_costs = config["unit_costs"]
        assert "33-1000" in unit_costs
        assert unit_costs["33-1000"]["cost"] == 45.00
    
    def test_default_assembly_mappings(self):
        """Test default assembly mappings."""
        mapper = AssembliesMapper()
        mappings = mapper._get_default_assembly_mappings()
        
        assert "pipe_mappings" in mappings
        assert "trench_mappings" in mappings
        assert "structure_mappings" in mappings
        assert "sitework_mappings" in mappings
        
        # Check pipe mappings
        pipe_mappings = mappings["pipe_mappings"]
        assert "storm" in pipe_mappings
        assert "12" in pipe_mappings["storm"]
        assert pipe_mappings["storm"]["12"] == "33-1000"
    
    def test_missing_config_files(self):
        """Test behavior with missing configuration files."""
        # Create mapper with non-existent config directory
        mapper = AssembliesMapper("non_existent_dir")
        
        # Should fall back to defaults
        assert mapper.pricing_config is not None
        assert mapper.assembly_mappings is not None
        
        # Should have default unit costs
        assert "unit_costs" in mapper.pricing_config
        assert len(mapper.pricing_config["unit_costs"]) > 0
