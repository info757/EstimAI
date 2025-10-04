"""
Legend detection and symbol sampling utilities.

This module provides functions to find legend regions and sample
symbol snippets for symbol mapping.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
import math


@dataclass
class BBox:
    """Bounding box for regions."""
    x1: float
    y1: float
    x2: float
    y2: float


def find_legend_regions(texts: List[Dict[str, Any]]) -> List[BBox]:
    """
    Find legend regions in text elements.
    """
    regions = []
    
    # Look for text that might indicate legend areas
    legend_keywords = ["legend", "symbols", "notes", "abbreviations"]
    
    for text_elem in texts:
        text = text_elem.get("text", "").lower()
        if any(keyword in text for keyword in legend_keywords):
            # Create a bounding box around this text
            x = text_elem.get("x", 0)
            y = text_elem.get("y", 0)
            
            # Create a reasonable legend region
            region = BBox(
                x1=x - 50,
                y1=y - 50,
                x2=x + 200,
                y2=y + 300
            )
            regions.append(region)
    
    return regions


def sample_symbol_snippets(
    vectors: List[Dict[str, Any]], 
    texts: List[Dict[str, Any]], 
    regions: List[BBox]
) -> List[Dict[str, Any]]:
    """
    Sample symbol snippets from legend regions.
    """
    snippets = []
    
    for region in regions:
        # Find vectors and text within this region
        region_vectors = []
        region_texts = []
        
        for vector in vectors:
            x1, y1 = vector.get("x1", 0), vector.get("y1", 0)
            x2, y2 = vector.get("x2", 0), vector.get("y2", 0)
            
            # Check if vector is within region
            if (region.x1 <= x1 <= region.x2 and region.y1 <= y1 <= region.y2):
                region_vectors.append(vector)
        
        for text in texts:
            x, y = text.get("x", 0), text.get("y", 0)
            
            # Check if text is within region
            if (region.x1 <= x <= region.x2 and region.y1 <= y <= region.y2):
                region_texts.append(text)
        
        # Create snippet
        snippet = {
            "region": {
                "x1": region.x1, "y1": region.y1,
                "x2": region.x2, "y2": region.y2
            },
            "vectors": region_vectors,
            "texts": region_texts
        }
        snippets.append(snippet)
    
    return snippets
