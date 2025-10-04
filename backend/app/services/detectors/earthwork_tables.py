"""
Earthwork table parsing utilities.

This module provides functions to parse earthwork summary tables
from PDF text content.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re


@dataclass
class CutFillSummary:
    """Earthwork summary from tables."""
    cut_cy: Optional[float] = None
    fill_cy: Optional[float] = None
    undercut_cy: Optional[float] = None


def parse_earthwork_summary(texts: List[Dict[str, Any]]) -> CutFillSummary:
    """
    Parse earthwork summary from text elements.
    """
    # Look for earthwork-related text
    earthwork_keywords = ["cut", "fill", "earthwork", "excavation", "cy", "cubic yards"]
    
    cut_cy = None
    fill_cy = None
    undercut_cy = None
    
    for text_elem in texts:
        text = text_elem.get("text", "").strip()
        if not text:
            continue
        
        # Look for cut/fill patterns
        cut_match = re.search(r'cut[:\s]*(\d+(?:\.\d+)?)\s*cy', text, re.IGNORECASE)
        if cut_match:
            try:
                cut_cy = float(cut_match.group(1))
            except ValueError:
                pass
        
        fill_match = re.search(r'fill[:\s]*(\d+(?:\.\d+)?)\s*cy', text, re.IGNORECASE)
        if fill_match:
            try:
                fill_cy = float(fill_match.group(1))
            except ValueError:
                pass
        
        undercut_match = re.search(r'undercut[:\s]*(\d+(?:\.\d+)?)\s*cy', text, re.IGNORECASE)
        if undercut_match:
            try:
                undercut_cy = float(undercut_match.group(1))
            except ValueError:
                pass
    
    return CutFillSummary(
        cut_cy=cut_cy,
        fill_cy=fill_cy,
        undercut_cy=undercut_cy
    )
