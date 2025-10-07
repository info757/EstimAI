"""
Parse legend/notes from construction drawings to extract utility network hints.

Legends typically contain material specifications like:
- "Water - PVC C900 8\"" 
- "Sanitary Sewer - PVC SDR-35"
- "Storm Drain - RCP 18\""
- "SD = Storm Drain"
- "SS = Sanitary Sewer"
"""

import re
import logging
from typing import List, Dict, Set

logger = logging.getLogger(__name__)


def parse_legend_from_text(full_page_text: str) -> List[str]:
    """
    Extract legend tokens from full page text.
    
    Looks for common patterns in legend/notes sections:
    - Material specs: "PVC C900", "RCP", "SDR-35"
    - Discipline keywords: "Storm", "Sanitary", "Water"
    - Abbreviations: "SD = Storm Drain"
    
    Args:
        full_page_text: Complete text content from PDF page
        
    Returns:
        List of legend tokens (e.g., ["Storm - RCP", "Water - PVC C900"])
        
    Examples:
        >>> text = "NOTES:\\n1. Storm Drain - RCP 18\\"\\n2. Water - PVC C900"
        >>> parse_legend_from_text(text)
        ['Storm Drain - RCP', 'Water - PVC C900']
    """
    if not full_page_text:
        return []
    
    text_lower = full_page_text.lower()
    tokens = []
    
    # Pattern 1: "Discipline [Sewer/Drain/Line] - Material [Size]"
    # Examples: "Storm Drain - RCP 18\"", "Sanitary Sewer - PVC SDR-35"
    discipline_material_pattern = re.compile(
        r'(storm|sanitary|sani|water|wat)\s*(drain|sewer|line|pipe)?\s*[-–—:]\s*'
        r'(rcp|pvc|hdpe|di|ductile\s*iron|cast\s*iron|c900|sdr[-\s]?35|sdr[-\s]?26)',
        re.IGNORECASE
    )
    
    for match in discipline_material_pattern.finditer(full_page_text):
        token = match.group(0).strip()
        tokens.append(token)
        logger.debug(f"Found legend token (pattern 1): {token}")
    
    # Pattern 2: Abbreviation definitions
    # Examples: "SD = Storm Drain", "SS = Sanitary Sewer", "WL = Water Line"
    abbrev_pattern = re.compile(
        r'\b(sd|ss|wl|wd|stm|san)\s*[=:]\s*(storm|sanitary|water)[\w\s]*',
        re.IGNORECASE
    )
    
    for match in abbrev_pattern.finditer(full_page_text):
        token = match.group(0).strip()
        tokens.append(token)
        logger.debug(f"Found legend token (pattern 2): {token}")
    
    # Pattern 3: Material-only specs in notes
    # Examples: "RCP pipe", "PVC SDR-35", "C900 water main"
    material_pattern = re.compile(
        r'\b(rcp|pvc\s+c900|pvc\s+sdr[-\s]?35|ductile\s+iron|hdpe)\b[\w\s]*',
        re.IGNORECASE
    )
    
    # Limit to first 20 matches to avoid noise
    for i, match in enumerate(material_pattern.finditer(full_page_text)):
        if i >= 20:
            break
        token = match.group(0).strip()
        # Only include if it's in a "notes" or "legend" section (heuristic: appears early or late in text)
        match_pos = match.start()
        text_len = len(full_page_text)
        if match_pos < text_len * 0.2 or match_pos > text_len * 0.8:
            tokens.append(token)
            logger.debug(f"Found legend token (pattern 3): {token}")
    
    # Pattern 4: Common layer/discipline keywords near material specs
    # Look for lines that mention both discipline and material
    lines = full_page_text.split('\n')
    for line in lines:
        line_lower = line.lower()
        has_discipline = any(d in line_lower for d in ['storm', 'sanitary', 'sani', 'water', 'wat'])
        has_material = any(m in line_lower for m in ['rcp', 'pvc', 'sdr', 'c900', 'ductile', 'hdpe'])
        
        if has_discipline and has_material:
            # Clean up the line
            cleaned = re.sub(r'^\d+[\.\)]\s*', '', line.strip())  # Remove leading numbers
            cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize whitespace
            if len(cleaned) < 100:  # Avoid capturing full paragraphs
                tokens.append(cleaned)
                logger.debug(f"Found legend token (pattern 4): {cleaned[:60]}")
    
    # Deduplicate while preserving order
    seen = set()
    unique_tokens = []
    for token in tokens:
        token_norm = token.lower().strip()
        if token_norm not in seen and len(token) > 3:
            seen.add(token_norm)
            unique_tokens.append(token)
    
    logger.info(f"Parsed {len(unique_tokens)} legend tokens from page text")
    return unique_tokens[:10]  # Limit to top 10 to avoid overwhelming the LLM


def extract_material_hints(legend_tokens: List[str]) -> Dict[str, Set[str]]:
    """
    Extract material hints per discipline from legend tokens.
    
    Args:
        legend_tokens: List of legend strings
        
    Returns:
        Dict mapping discipline -> set of material keywords
        
    Examples:
        >>> tokens = ["Storm Drain - RCP", "Water - PVC C900"]
        >>> extract_material_hints(tokens)
        {'storm': {'rcp'}, 'water': {'pvc', 'c900'}}
    """
    hints = {
        'storm': set(),
        'sanitary': set(),
        'water': set()
    }
    
    for token in legend_tokens:
        token_lower = token.lower()
        
        # Identify discipline
        discipline = None
        if any(x in token_lower for x in ['storm', 'stm', 'sd']):
            discipline = 'storm'
        elif any(x in token_lower for x in ['sanitary', 'sani', 'sewer', 'ss']):
            discipline = 'sanitary'
        elif any(x in token_lower for x in ['water', 'wat', 'wl']):
            discipline = 'water'
        
        if discipline:
            # Extract materials
            if 'rcp' in token_lower:
                hints[discipline].add('rcp')
            if 'pvc' in token_lower:
                hints[discipline].add('pvc')
            if 'sdr' in token_lower:
                hints[discipline].add('sdr-35')
            if 'c900' in token_lower:
                hints[discipline].add('c900')
            if 'ductile' in token_lower or 'di' in token_lower:
                hints[discipline].add('ductile iron')
            if 'hdpe' in token_lower:
                hints[discipline].add('hdpe')
    
    return hints


__all__ = ["parse_legend_from_text", "extract_material_hints"]

