"""Tests for legend detection functionality."""
import pytest
from unittest.mock import Mock, patch

from backend.app.services.detectors.legend import (
    BBox, SymbolSnippet, find_legend_regions, sample_symbol_snippets,
    _expand_bbox_for_legend, _merge_overlapping_bboxes, _filter_vectors_in_region,
    _filter_texts_in_region, _group_symbols_in_region, _create_symbol_snippet
)
from backend.app.services.ingest.extract import VectorEl, TextEl


class TestBBox:
    """Test BBox dataclass."""
    
    def test_bbox_creation(self):
        """Test BBox creation."""
        bbox = BBox(0.0, 0.0, 10.0, 10.0)
        assert bbox.x1 == 0.0
        assert bbox.y1 == 0.0
        assert bbox.x2 == 10.0
        assert bbox.y2 == 10.0
    
    def test_bbox_area(self):
        """Test BBox area calculation."""
        bbox = BBox(0.0, 0.0, 10.0, 10.0)
        assert bbox.area() == 100.0
        
        bbox2 = BBox(0.0, 0.0, 5.0, 8.0)
        assert bbox2.area() == 40.0
    
    def test_bbox_contains(self):
        """Test BBox contains method."""
        bbox = BBox(0.0, 0.0, 10.0, 10.0)
        
        # Test points inside
        assert bbox.contains(5.0, 5.0) == True
        assert bbox.contains(0.0, 0.0) == True
        assert bbox.contains(10.0, 10.0) == True
        
        # Test points outside
        assert bbox.contains(-1.0, 5.0) == False
        assert bbox.contains(5.0, -1.0) == False
        assert bbox.contains(11.0, 5.0) == False
        assert bbox.contains(5.0, 11.0) == False
    
    def test_bbox_overlaps(self):
        """Test BBox overlaps method."""
        bbox1 = BBox(0.0, 0.0, 10.0, 10.0)
        bbox2 = BBox(5.0, 5.0, 15.0, 15.0)
        bbox3 = BBox(20.0, 20.0, 30.0, 30.0)
        
        # Test overlapping boxes
        assert bbox1.overlaps(bbox2) == True
        assert bbox2.overlaps(bbox1) == True
        
        # Test non-overlapping boxes
        assert bbox1.overlaps(bbox3) == False
        assert bbox3.overlaps(bbox1) == False


class TestLegendDetection:
    """Test legend region detection."""
    
    def test_find_legend_regions_empty(self):
        """Test finding legend regions with empty text list."""
        texts = []
        regions = find_legend_regions(texts)
        assert regions == []
    
    def test_find_legend_regions_no_matches(self):
        """Test finding legend regions with no matches."""
        texts = [
            TextEl("Some random text", (0, 0, 100, 20), []),
            TextEl("Another text", (0, 20, 100, 40), [])
        ]
        regions = find_legend_regions(texts)
        assert regions == []
    
    def test_find_legend_regions_with_matches(self):
        """Test finding legend regions with matches."""
        texts = [
            TextEl("LEGEND", (0, 0, 100, 20), []),
            TextEl("Some random text", (0, 20, 100, 40), []),
            TextEl("SYMBOLS", (0, 40, 100, 60), [])
        ]
        regions = find_legend_regions(texts)
        assert len(regions) > 0
    
    def test_find_legend_regions_case_insensitive(self):
        """Test finding legend regions with case insensitive matching."""
        texts = [
            TextEl("legend", (0, 0, 100, 20), []),
            TextEl("ABBREVIATIONS", (0, 20, 100, 40), []),
            TextEl("General Notes", (0, 40, 100, 60), [])
        ]
        regions = find_legend_regions(texts)
        assert len(regions) > 0
    
    def test_find_legend_regions_multiple_patterns(self):
        """Test finding legend regions with multiple patterns."""
        texts = [
            TextEl("LEGEND", (0, 0, 100, 20), []),
            TextEl("ABBREV", (0, 20, 100, 40), []),
            TextEl("SYMBOLS", (0, 40, 100, 60), []),
            TextEl("GENERAL NOTES", (0, 60, 100, 80), [])
        ]
        regions = find_legend_regions(texts)
        assert len(regions) > 0


class TestSymbolSnippets:
    """Test symbol snippet creation."""
    
    def test_sample_symbol_snippets_empty(self):
        """Test sampling symbol snippets with empty inputs."""
        vectors = []
        texts = []
        regions = []
        
        snippets = sample_symbol_snippets(vectors, texts, regions)
        assert snippets == []
    
    def test_sample_symbol_snippets_with_data(self):
        """Test sampling symbol snippets with data."""
        # Create test vectors
        vectors = [
            VectorEl(
                kind="line",
                points=[(0.0, 0.0), (10.0, 10.0)],
                stroke_rgba=(0, 0, 0, 255),
                fill_rgba=(0, 0, 0, 0),
                stroke_w=1.0,
                ocg_names=[],
                xform=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
            )
        ]
        
        # Create test texts
        texts = [
            TextEl("Sample text", (5.0, 5.0, 15.0, 15.0), [])
        ]
        
        # Create test regions
        regions = [BBox(0.0, 0.0, 20.0, 20.0)]
        
        snippets = sample_symbol_snippets(vectors, texts, regions)
        assert len(snippets) > 0
        
        # Check snippet properties
        snippet = snippets[0]
        assert isinstance(snippet, SymbolSnippet)
        assert snippet.stroke_pattern is not None
        assert snippet.stroke_width_stats is not None
        assert snippet.shape_hints is not None
        assert snippet.adjacent_text is not None


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_expand_bbox_for_legend(self):
        """Test expanding bounding box for legend."""
        bbox = BBox(0.0, 0.0, 100.0, 20.0)
        texts = [
            TextEl("Nearby text 1", (50.0, 30.0, 150.0, 50.0), []),
            TextEl("Far text", (200.0, 200.0, 300.0, 220.0), [])
        ]
        
        expanded_bbox = _expand_bbox_for_legend(bbox, texts)
        
        # Should include nearby text but not far text
        assert expanded_bbox.x1 <= 50.0
        assert expanded_bbox.x2 >= 150.0
        assert expanded_bbox.y1 <= 30.0
        assert expanded_bbox.y2 >= 50.0
    
    def test_merge_overlapping_bboxes(self):
        """Test merging overlapping bounding boxes."""
        bbox1 = BBox(0.0, 0.0, 10.0, 10.0)
        bbox2 = BBox(5.0, 5.0, 15.0, 15.0)
        bbox3 = BBox(20.0, 20.0, 30.0, 30.0)
        
        merged = _merge_overlapping_bboxes([bbox1, bbox2, bbox3])
        
        # Should have 2 merged boxes (bbox1+bbox2, bbox3)
        assert len(merged) == 2
        
        # First merged box should encompass bbox1 and bbox2
        first_merged = merged[0]
        assert first_merged.x1 <= 0.0
        assert first_merged.y1 <= 0.0
        assert first_merged.x2 >= 15.0
        assert first_merged.y2 >= 15.0
    
    def test_filter_vectors_in_region(self):
        """Test filtering vectors in region."""
        vectors = [
            VectorEl("line", [(5.0, 5.0), (15.0, 15.0)], (0, 0, 0, 255), (0, 0, 0, 0), 1.0, [], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]),
            VectorEl("line", [(25.0, 25.0), (35.0, 35.0)], (0, 0, 0, 255), (0, 0, 0, 0), 1.0, [], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        ]
        region = BBox(0.0, 0.0, 20.0, 20.0)
        
        filtered = _filter_vectors_in_region(vectors, region)
        assert len(filtered) == 1
        assert filtered[0] == vectors[0]
    
    def test_filter_texts_in_region(self):
        """Test filtering texts in region."""
        texts = [
            TextEl("Text 1", (5.0, 5.0, 15.0, 15.0), []),
            TextEl("Text 2", (25.0, 25.0, 35.0, 35.0), [])
        ]
        region = BBox(0.0, 0.0, 20.0, 20.0)
        
        filtered = _filter_texts_in_region(texts, region)
        assert len(filtered) == 1
        assert filtered[0] == texts[0]
    
    def test_group_symbols_in_region(self):
        """Test grouping symbols in region."""
        vectors = [
            VectorEl("line", [(5.0, 5.0), (15.0, 15.0)], (0, 0, 0, 255), (0, 0, 0, 0), 1.0, [], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        ]
        texts = [
            TextEl("Nearby text", (10.0, 10.0, 20.0, 20.0), [])
        ]
        region = BBox(0.0, 0.0, 30.0, 30.0)
        
        groups = _group_symbols_in_region(vectors, texts, region)
        assert len(groups) == 1
        
        group = groups[0]
        assert "vectors" in group
        assert "texts" in group
        assert "bbox" in group
        assert len(group["vectors"]) == 1
        assert len(group["texts"]) == 1
    
    def test_create_symbol_snippet(self):
        """Test creating symbol snippet."""
        group = {
            "vectors": [
                VectorEl("line", [(0.0, 0.0), (10.0, 10.0)], (0, 0, 0, 255), (0, 0, 0, 0), 1.0, [], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
            ],
            "texts": [
                TextEl("Sample text", (5.0, 5.0, 15.0, 15.0), [])
            ],
            "bbox": BBox(0.0, 0.0, 15.0, 15.0)
        }
        region = BBox(0.0, 0.0, 20.0, 20.0)
        
        snippet = _create_symbol_snippet(group, region)
        assert snippet is not None
        assert isinstance(snippet, SymbolSnippet)
        assert snippet.stroke_pattern is not None
        assert snippet.stroke_width_stats is not None
        assert snippet.shape_hints is not None
        assert snippet.adjacent_text is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
