"""
Test pipe bucket processing functionality.

Tests depth bucket flattening, CSI mapping, and pricing calculations.
"""
import json
import tempfile
import os
from pathlib import Path
from backend.app.services.counts.pipe_buckets import (
    PipeBucketProcessor, PipeBucketItem, TrenchItem,
    process_networks_to_count_items
)
from backend.app.services.pricing.stub import PricingStub, calculate_pricing_totals


class TestPipeBucketProcessor:
    """Test pipe bucket processor functionality."""
    
    def test_processor_initialization(self):
        """Test processor initialization."""
        processor = PipeBucketProcessor()
        
        assert processor.assemblies_config_path == Path("config/assemblies/pipes.json")
        assert processor.pricing_config_path == Path("config/pricing/pipes_stub.json")
        assert isinstance(processor.assemblies_config, dict)
        assert isinstance(processor.pricing_config, dict)
    
    def test_load_assemblies_config(self):
        """Test loading assemblies configuration."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "pipe.sanitary.0_5": {
                    "csi": "33 30 00",
                    "uom": "LF",
                    "description": "Sanitary Sewer Piping (0-5ft depth)"
                }
            }
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            processor = PipeBucketProcessor(assemblies_config=config_path)
            assert "pipe.sanitary.0_5" in processor.assemblies_config
            assert processor.assemblies_config["pipe.sanitary.0_5"]["csi"] == "33 30 00"
        finally:
            os.unlink(config_path)
    
    def test_load_pricing_config(self):
        """Test loading pricing configuration."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "pipe.sanitary.0_5": {
                    "unit_price": 25.50,
                    "currency": "USD",
                    "description": "Sanitary Sewer Piping (0-5ft depth) per LF"
                }
            }
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            processor = PipeBucketProcessor(pricing_config=config_path)
            assert "pipe.sanitary.0_5" in processor.pricing_config
            assert processor.pricing_config["pipe.sanitary.0_5"]["unit_price"] == 25.50
        finally:
            os.unlink(config_path)
    
    def test_process_pipe_buckets(self):
        """Test processing pipe depth buckets."""
        # Create temporary config files
        assemblies_config = {
            "pipe.sanitary.0_5": {"csi": "33 30 00", "uom": "LF"},
            "pipe.sanitary.5_8": {"csi": "33 30 00", "uom": "LF"}
        }
        
        pricing_config = {
            "pipe.sanitary.0_5": {"unit_price": 25.50},
            "pipe.sanitary.5_8": {"unit_price": 28.75}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(assemblies_config, f)
            assemblies_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(pricing_config, f)
            pricing_path = f.name
        
        try:
            processor = PipeBucketProcessor(assemblies_path, pricing_path)
            
            # Test pipes with depth buckets
            pipes = [
                {
                    "id": "sanitary_pipe_1",
                    "dia_in": 8.0,
                    "mat": "pvc",
                    "avg_depth_ft": 3.5,
                    "extra": {
                        "buckets_lf": {
                            "0-5": 50.0,
                            "5-8": 30.0,
                            "8-12": 0.0,
                            "12+": 0.0
                        },
                        "min_depth_ft": 3.0,
                        "max_depth_ft": 4.0,
                        "cover_ok": True,
                        "deep_excavation": False,
                        "_ground_source": "surface"
                    }
                }
            ]
            
            bucket_items = processor.process_pipe_buckets(pipes, "sanitary")
            
            assert len(bucket_items) == 2  # 0-5 and 5-8 buckets
            
            # Check first bucket (0-5)
            item_0_5 = bucket_items[0]
            assert item_0_5.category == "pipe.sanitary.0_5"
            assert item_0_5.csi == "33 30 00"
            assert item_0_5.uom == "LF"
            assert item_0_5.quantity == 50.0
            assert item_0_5.unit_price == 25.50
            assert item_0_5.total_price == 1275.0  # 25.50 * 50.0
            assert item_0_5.attributes["diameter_in"] == 8.0
            assert item_0_5.attributes["material"] == "pvc"
            assert item_0_5.attributes["avg_depth_ft"] == 3.5
            
            # Check second bucket (5-8)
            item_5_8 = bucket_items[1]
            assert item_5_8.category == "pipe.sanitary.5_8"
            assert item_5_8.quantity == 30.0
            assert item_5_8.unit_price == 28.75
            assert item_5_8.total_price == 862.5  # 28.75 * 30.0
            
        finally:
            os.unlink(assemblies_path)
            os.unlink(pricing_path)
    
    def test_process_trench_excavation(self):
        """Test processing trench excavation volumes."""
        # Create temporary config files
        assemblies_config = {
            "trench.excavation": {"csi": "31 23 33", "uom": "CY"}
        }
        
        pricing_config = {
            "trench.excavation": {"unit_price": 15.25}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(assemblies_config, f)
            assemblies_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(pricing_config, f)
            pricing_path = f.name
        
        try:
            processor = PipeBucketProcessor(assemblies_path, pricing_path)
            
            # Test pipes with trench volumes
            pipes = [
                {
                    "id": "sanitary_pipe_1",
                    "dia_in": 8.0,
                    "mat": "pvc",
                    "avg_depth_ft": 3.5,
                    "extra": {
                        "trench_volume_cy": 12.5,
                        "min_depth_ft": 3.0,
                        "max_depth_ft": 4.0,
                        "cover_ok": True,
                        "deep_excavation": False,
                        "_ground_source": "surface"
                    }
                }
            ]
            
            trench_items = processor.process_trench_excavation(pipes, "sanitary")
            
            assert len(trench_items) == 1
            
            trench_item = trench_items[0]
            assert trench_item.category == "trench.excavation"
            assert trench_item.csi == "31 23 33"
            assert trench_item.uom == "CY"
            assert trench_item.quantity == 12.5
            assert trench_item.unit_price == 15.25
            assert trench_item.total_price == 190.625  # 15.25 * 12.5
            assert trench_item.attributes["discipline"] == "sanitary"
            assert trench_item.attributes["diameter_in"] == 8.0
            
        finally:
            os.unlink(assemblies_path)
            os.unlink(pricing_path)
    
    def test_process_all_pipes(self):
        """Test processing all pipes from networks."""
        # Create temporary config files
        assemblies_config = {
            "pipe.sanitary.0_5": {"csi": "33 30 00", "uom": "LF"},
            "trench.excavation": {"csi": "31 23 33", "uom": "CY"}
        }
        
        pricing_config = {
            "pipe.sanitary.0_5": {"unit_price": 25.50},
            "trench.excavation": {"unit_price": 15.25}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(assemblies_config, f)
            assemblies_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(pricing_config, f)
            pricing_path = f.name
        
        try:
            processor = PipeBucketProcessor(assemblies_path, pricing_path)
            
            # Test networks with pipes
            networks = {
                "sanitary": {
                    "pipes": [
                        {
                            "id": "sanitary_pipe_1",
                            "dia_in": 8.0,
                            "mat": "pvc",
                            "avg_depth_ft": 3.5,
                            "extra": {
                                "buckets_lf": {"0-5": 50.0, "5-8": 0.0, "8-12": 0.0, "12+": 0.0},
                                "trench_volume_cy": 12.5,
                                "min_depth_ft": 3.0,
                                "max_depth_ft": 4.0,
                                "cover_ok": True,
                                "deep_excavation": False,
                                "_ground_source": "surface"
                            }
                        }
                    ]
                },
                "storm": {"pipes": []},
                "water": {"pipes": []}
            }
            
            count_items = processor.process_all_pipes(networks)
            
            assert len(count_items) == 2  # 1 pipe bucket + 1 trench
            
            # Check pipe bucket item
            pipe_item = count_items[0]
            assert pipe_item["category"] == "pipe.sanitary.0_5"
            assert pipe_item["quantity"] == 50.0
            assert pipe_item["total_price"] == 1275.0
            
            # Check trench item
            trench_item = count_items[1]
            assert trench_item["category"] == "trench.excavation"
            assert trench_item["quantity"] == 12.5
            assert trench_item["total_price"] == 190.625
            
        finally:
            os.unlink(assemblies_path)
            os.unlink(pricing_path)
    
    def test_get_assembly_summary(self):
        """Test assembly summary generation."""
        # Create temporary config files
        assemblies_config = {
            "pipe.sanitary.0_5": {"csi": "33 30 00", "uom": "LF"},
            "trench.excavation": {"csi": "31 23 33", "uom": "CY"}
        }
        
        pricing_config = {
            "pipe.sanitary.0_5": {"unit_price": 25.50},
            "trench.excavation": {"unit_price": 15.25}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(assemblies_config, f)
            assemblies_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(pricing_config, f)
            pricing_path = f.name
        
        try:
            processor = PipeBucketProcessor(assemblies_path, pricing_path)
            
            # Test count items
            count_items = [
                {
                    "category": "pipe.sanitary.0_5",
                    "csi": "33 30 00",
                    "uom": "LF",
                    "quantity": 50.0,
                    "total_price": 1275.0
                },
                {
                    "category": "trench.excavation",
                    "csi": "31 23 33",
                    "uom": "CY",
                    "quantity": 12.5,
                    "total_price": 190.625
                }
            ]
            
            summary = processor.get_assembly_summary(count_items)
            
            assert summary["total_items"] == 2
            assert summary["total_quantity"] == 62.5  # 50.0 + 12.5
            assert summary["total_price"] == 1465.625  # 1275.0 + 190.625
            assert summary["pricing_available"] == True
            assert "pipe.sanitary.0_5" in summary["by_category"]
            assert "33 30 00" in summary["by_csi"]
            
        finally:
            os.unlink(assemblies_path)
            os.unlink(pricing_path)


class TestPricingStub:
    """Test pricing stub functionality."""
    
    def test_pricing_stub_initialization(self):
        """Test pricing stub initialization."""
        pricing_stub = PricingStub()
        
        assert pricing_stub.pricing_config_path == Path("config/pricing/pipes_stub.json")
        assert isinstance(pricing_stub.pricing_config, dict)
    
    def test_calculate_totals(self):
        """Test pricing totals calculation."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "pipe.sanitary.0_5": {
                    "unit_price": 25.50,
                    "currency": "USD"
                },
                "trench.excavation": {
                    "unit_price": 15.25,
                    "currency": "USD"
                }
            }
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            pricing_stub = PricingStub(config_path)
            
            # Test count items
            count_items = [
                {
                    "category": "pipe.sanitary.0_5",
                    "csi": "33 30 00",
                    "uom": "LF",
                    "quantity": 50.0,
                    "unit_price": 25.50,
                    "total_price": 1275.0
                },
                {
                    "category": "trench.excavation",
                    "csi": "31 23 33",
                    "uom": "CY",
                    "quantity": 12.5,
                    "unit_price": 15.25,
                    "total_price": 190.625
                }
            ]
            
            summary = pricing_stub.calculate_totals(count_items)
            
            assert summary.total_cost == 1465.625
            assert summary.currency == "USD"
            assert summary.item_count == 2
            assert summary.priced_items == 2
            assert summary.unpriced_items == 0
            assert "pipe.sanitary.0_5" in summary.by_category
            assert "33 30 00" in summary.by_csi
            
        finally:
            os.unlink(config_path)
    
    def test_get_unit_price(self):
        """Test getting unit price for category."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "pipe.sanitary.0_5": {"unit_price": 25.50},
                "pipe.storm.0_5": {"unit_price": 18.75}
            }
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            pricing_stub = PricingStub(config_path)
            
            assert pricing_stub.get_unit_price("pipe.sanitary.0_5") == 25.50
            assert pricing_stub.get_unit_price("pipe.storm.0_5") == 18.75
            assert pricing_stub.get_unit_price("nonexistent") is None
            
        finally:
            os.unlink(config_path)
    
    def test_is_pricing_available(self):
        """Test pricing availability check."""
        # Test with no config
        pricing_stub = PricingStub("nonexistent.json")
        assert not pricing_stub.is_pricing_available()
        
        # Test with config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {"test": {"unit_price": 10.0}}
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            pricing_stub = PricingStub(config_path)
            assert pricing_stub.is_pricing_available()
        finally:
            os.unlink(config_path)


class TestIntegration:
    """Test integration between pipe buckets and pricing."""
    
    def test_process_networks_to_count_items(self):
        """Test end-to-end processing of networks to count items."""
        # Create temporary config files
        assemblies_config = {
            "pipe.sanitary.0_5": {"csi": "33 30 00", "uom": "LF"},
            "trench.excavation": {"csi": "31 23 33", "uom": "CY"}
        }
        
        pricing_config = {
            "pipe.sanitary.0_5": {"unit_price": 25.50},
            "trench.excavation": {"unit_price": 15.25}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(assemblies_config, f)
            assemblies_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(pricing_config, f)
            pricing_path = f.name
        
        try:
            # Mock the processor to use our temp files
            import backend.app.services.counts.pipe_buckets as pb_module
            original_processor = pb_module.PipeBucketProcessor
            
            class MockProcessor(original_processor):
                def __init__(self):
                    self.assemblies_config_path = Path(assemblies_path)
                    self.pricing_config_path = Path(pricing_path)
                    self.assemblies_config = self._load_assemblies_config()
                    self.pricing_config = self._load_pricing_config()
            
            pb_module.PipeBucketProcessor = MockProcessor
            
            try:
                # Test networks
                networks = {
                    "sanitary": {
                        "pipes": [
                            {
                                "id": "sanitary_pipe_1",
                                "dia_in": 8.0,
                                "mat": "pvc",
                                "avg_depth_ft": 3.5,
                                "extra": {
                                    "buckets_lf": {"0-5": 50.0, "5-8": 0.0, "8-12": 0.0, "12+": 0.0},
                                    "trench_volume_cy": 12.5,
                                    "min_depth_ft": 3.0,
                                    "max_depth_ft": 4.0,
                                    "cover_ok": True,
                                    "deep_excavation": False,
                                    "_ground_source": "surface"
                                }
                            }
                        ]
                    },
                    "storm": {"pipes": []},
                    "water": {"pipes": []}
                }
                
                count_items = process_networks_to_count_items(networks)
                
                assert len(count_items) == 2
                assert count_items[0]["category"] == "pipe.sanitary.0_5"
                assert count_items[1]["category"] == "trench.excavation"
                
            finally:
                pb_module.PipeBucketProcessor = original_processor
                
        finally:
            os.unlink(assemblies_path)
            os.unlink(pricing_path)
