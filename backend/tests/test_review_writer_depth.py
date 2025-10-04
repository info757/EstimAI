"""
Unit tests for review_writer.py depth field persistence.

Tests that depth analysis fields are properly included in pipe attributes
when converting EstimAIResult to count items.
"""
import pytest
from backend.app.services.persistence.review_writer import _pipe_to_count_items, estimai_to_count_items
from backend.app.schemas_estimai import EstimAIResult, StormNetwork, Pipe


def test_pipe_to_count_items_with_depth_fields():
    """Test that depth fields are included in pipe attributes."""
    # Create a pipe with depth analysis in extra field
    pipe = Pipe(
        id="test_pipe_1",
        from_id="node_1",
        to_id="node_2", 
        length_ft=100.0,
        dia_in=12.0,
        mat="pvc"
    )
    
    # Add depth analysis to extra field
    pipe.extra = {
        "min_depth_ft": 2.5,
        "max_depth_ft": 8.0,
        "p95_depth_ft": 7.5,
        "buckets_lf": {
            "0-5": 30.0,
            "5-8": 50.0,
            "8-12": 20.0,
            "12+": 0.0
        },
        "trench_volume_cy": 150.0,
        "cover_ok": True,
        "deep_excavation": False
    }
    
    # Convert to count items
    items = _pipe_to_count_items([pipe], "storm_pipe", "Sheet1")
    
    assert len(items) == 1
    item = items[0]
    
    # Check basic fields
    assert item["category"] == "storm_pipe"
    assert item["subtype"] == "pvc"
    assert item["name"] == "test_pipe_1"
    assert item["quantity"] == 100.0
    assert item["unit"] == "LF"
    
    # Check attributes include depth fields
    attrs = item["attributes"]
    
    # Basic pipe attributes
    assert attrs["length_ft"] == 100.0
    assert attrs["diameter_in"] == 12.0
    assert attrs["material"] == "pvc"
    assert attrs["from_id"] == "node_1"
    assert attrs["to_id"] == "node_2"
    
    # Depth statistics
    assert attrs["min_depth_ft"] == 2.5
    assert attrs["max_depth_ft"] == 8.0
    assert attrs["p95_depth_ft"] == 7.5
    
    # Depth buckets
    assert attrs["d_0_5"] == 30.0
    assert attrs["d_5_8"] == 50.0
    assert attrs["d_8_12"] == 20.0
    assert attrs["d_12_plus"] == 0.0
    
    # Trench and validation fields
    assert attrs["trench_volume_cy"] == 150.0
    assert attrs["cover_ok"] is True
    assert attrs["deep_excavation"] is False


def test_pipe_to_count_items_without_extra():
    """Test that pipes without extra field work correctly."""
    pipe = Pipe(
        id="test_pipe_2",
        from_id="node_1",
        to_id="node_2",
        length_ft=50.0,
        dia_in=8.0,
        mat="pvc"
    )
    # No extra field
    
    items = _pipe_to_count_items([pipe], "sanitary_pipe", "Sheet1")
    
    assert len(items) == 1
    item = items[0]
    attrs = item["attributes"]
    
    # Basic fields should be present
    assert attrs["length_ft"] == 50.0
    assert attrs["diameter_in"] == 8.0
    assert attrs["material"] == "pvc"
    
    # Depth fields should not be present
    assert "min_depth_ft" not in attrs
    assert "max_depth_ft" not in attrs
    assert "p95_depth_ft" not in attrs
    assert "d_0_5" not in attrs
    assert "trench_volume_cy" not in attrs
    assert "cover_ok" not in attrs
    assert "deep_excavation" not in attrs


def test_pipe_to_count_items_partial_extra():
    """Test that pipes with partial extra fields work correctly."""
    pipe = Pipe(
        id="test_pipe_3",
        from_id="node_1",
        to_id="node_2",
        length_ft=75.0,
        dia_in=10.0,
        mat="pvc"
    )
    
    # Partial extra field
    pipe.extra = {
        "min_depth_ft": 3.0,
        "max_depth_ft": 6.0,
        "trench_volume_cy": 100.0
        # Missing other fields
    }
    
    items = _pipe_to_count_items([pipe], "water_pipe", "Sheet1")
    
    assert len(items) == 1
    item = items[0]
    attrs = item["attributes"]
    
    # Present fields should be included
    assert attrs["min_depth_ft"] == 3.0
    assert attrs["max_depth_ft"] == 6.0
    assert attrs["trench_volume_cy"] == 100.0
    
    # Missing fields should not be present
    assert "p95_depth_ft" not in attrs
    assert "d_0_5" not in attrs
    assert "cover_ok" not in attrs


def test_estimai_to_count_items_with_depth():
    """Test complete EstimAIResult to count items conversion with depth fields."""
    # Create storm network with pipes that have depth analysis
    storm_pipe = Pipe(
        id="storm_pipe_1",
        from_id="inlet_1",
        to_id="inlet_2",
        length_ft=80.0,
        dia_in=15.0,
        mat="pvc"
    )
    storm_pipe.extra = {
        "min_depth_ft": 2.0,
        "max_depth_ft": 5.0,
        "p95_depth_ft": 4.8,
        "buckets_lf": {"0-5": 80.0, "5-8": 0.0, "8-12": 0.0, "12+": 0.0},
        "trench_volume_cy": 120.0,
        "cover_ok": True,
        "deep_excavation": False
    }
    
    storm_network = StormNetwork(pipes=[storm_pipe], structures=[])
    
    # Create EstimAIResult
    result = EstimAIResult(
        sheet_units="ft",
        networks={"storm": storm_network}
    )
    
    # Convert to count items
    items = estimai_to_count_items(result, "Sheet1")
    
    # Find the storm pipe item
    storm_items = [item for item in items if item["category"] == "storm_pipe"]
    assert len(storm_items) == 1
    
    storm_item = storm_items[0]
    attrs = storm_item["attributes"]
    
    # Verify depth fields are present
    assert attrs["min_depth_ft"] == 2.0
    assert attrs["max_depth_ft"] == 5.0
    assert attrs["p95_depth_ft"] == 4.8
    assert attrs["d_0_5"] == 80.0
    assert attrs["d_5_8"] == 0.0
    assert attrs["trench_volume_cy"] == 120.0
    assert attrs["cover_ok"] is True
    assert attrs["deep_excavation"] is False


def test_depth_buckets_mapping():
    """Test that depth buckets are correctly mapped to attribute names."""
    pipe = Pipe(
        id="test_pipe_4",
        from_id="node_1",
        to_id="node_2",
        length_ft=100.0,
        dia_in=12.0,
        mat="pvc"
    )
    
    pipe.extra = {
        "buckets_lf": {
            "0-5": 25.0,
            "5-8": 35.0,
            "8-12": 30.0,
            "12+": 10.0
        }
    }
    
    items = _pipe_to_count_items([pipe], "storm_pipe", "Sheet1")
    attrs = items[0]["attributes"]
    
    # Verify bucket mapping
    assert attrs["d_0_5"] == 25.0
    assert attrs["d_5_8"] == 35.0
    assert attrs["d_8_12"] == 30.0
    assert attrs["d_12_plus"] == 10.0


def test_boolean_fields_preservation():
    """Test that boolean fields are correctly preserved."""
    pipe = Pipe(
        id="test_pipe_5",
        from_id="node_1",
        to_id="node_2",
        length_ft=60.0,
        dia_in=8.0,
        mat="pvc"
    )
    
    pipe.extra = {
        "cover_ok": False,
        "deep_excavation": True
    }
    
    items = _pipe_to_count_items([pipe], "sanitary_pipe", "Sheet1")
    attrs = items[0]["attributes"]
    
    # Verify boolean fields are preserved
    assert attrs["cover_ok"] is False
    assert attrs["deep_excavation"] is True
