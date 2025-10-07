"""
Heuristic rules for inferring pipe disciplines when LLM classification is uncertain.

These rules act as a fallback when:
- LLM returns discipline=None
- LLM returns a discipline that doesn't match the target network
- Confidence is low but material/text hints are strong
"""

from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


def infer_discipline(
    material: Optional[str] = None,
    nearby_text: Optional[List[str]] = None,
    layer_hint: Optional[str] = None
) -> Optional[str]:
    """
    Infer pipe discipline from material, nearby text, and layer hints.
    
    Args:
        material: Material code (e.g., "rcp", "pvc", "di")
        nearby_text: List of text snippets near the polyline
        layer_hint: PDF layer/OCG name
        
    Returns:
        One of "storm", "sanitary", "water", or None if no match
        
    Examples:
        >>> infer_discipline(material="rcp")
        'storm'
        >>> infer_discipline(material="sdr-35")
        'sanitary'
        >>> infer_discipline(nearby_text=["SD MH 1", "18\" RCP"])
        'storm'
        >>> infer_discipline(layer_hint="S-UTLITY-WATR")
        'water'
    """
    # Combine all text sources into a single searchable string
    text_parts = []
    if material:
        text_parts.append(material)
    if nearby_text:
        text_parts.extend(nearby_text)
    if layer_hint:
        text_parts.append(layer_hint)
    
    combined_text = " ".join(text_parts).lower()
    
    # Storm drainage indicators (strongest signals first)
    storm_signals = [
        "storm", "stm", "sd", "rcp", "culvert", "cb", "catch basin",
        "sd mh", "sd mh.", "storm drain", "drainage", "inlet"
    ]
    if any(signal in combined_text for signal in storm_signals):
        logger.debug(f"Inferred discipline=storm from text: {combined_text[:60]}")
        return "storm"
    
    # Sanitary sewer indicators
    sanitary_signals = [
        "san", "sanitary", "sani", "sewer", "ss", "sdr-35", "sdr 35",
        "mh (san)", "san mh", "san mh.", "foul", "wastewater"
    ]
    if any(signal in combined_text for signal in sanitary_signals):
        logger.debug(f"Inferred discipline=sanitary from text: {combined_text[:60]}")
        return "sanitary"
    
    # Water supply indicators
    water_signals = [
        "water", "wat", "wtr", "c900", "di", "ductile iron", "ductile",
        "hydrant", "valve", "ci", "cast iron", "pe", "hdpe"
    ]
    if any(signal in combined_text for signal in water_signals):
        logger.debug(f"Inferred discipline=water from text: {combined_text[:60]}")
        return "water"
    
    # Layer hint patterns (if we didn't match above)
    if layer_hint:
        lh = layer_hint.lower()
        # Common AutoCAD layer naming conventions
        if any(x in lh for x in ["stm", "sd", "storm", "drain"]):
            logger.debug(f"Inferred discipline=storm from layer: {layer_hint}")
            return "storm"
        if any(x in lh for x in ["san", "ss", "sewer", "sanitary"]):
            logger.debug(f"Inferred discipline=sanitary from layer: {layer_hint}")
            return "sanitary"
        if any(x in lh for x in ["wat", "wtr", "water"]):
            logger.debug(f"Inferred discipline=water from layer: {layer_hint}")
            return "water"
    
    # No match found
    logger.debug(f"No discipline inference from: {combined_text[:60]}")
    return None


def should_include_in_network(
    detection,
    target_discipline: str,
    patch_data: dict
) -> tuple[bool, Optional[str]]:
    """
    Determine if a detection should be included in the target network.
    
    Uses both LLM classification and heuristic fallback to make the decision.
    
    Args:
        detection: Detection object from PipeClassifier
        target_discipline: Target discipline ("storm", "sanitary", or "water")
        patch_data: Original patch dict with layer/text hints
        
    Returns:
        (include: bool, reason: str) - Whether to include and why
        
    Examples:
        >>> # LLM says storm, target is storm → include
        >>> should_include_in_network(det_storm, "storm", {})
        (True, "LLM: storm")
        
        >>> # LLM says None, but material is RCP, target is storm → include
        >>> should_include_in_network(det_none, "storm", {"material": "rcp"})
        (True, "Heuristic: storm (from material)")
        
        >>> # LLM says storm, target is sanitary, no heuristic match → exclude
        >>> should_include_in_network(det_storm, "sanitary", {})
        (False, "Discipline mismatch: storm != sanitary")
    """
    llm_discipline = detection.attrs.discipline
    
    # Case 1: LLM agrees with target
    if llm_discipline == target_discipline:
        return True, f"LLM: {llm_discipline}"
    
    # Case 2: LLM disagrees or is None - try heuristic fallback
    material = detection.attrs.material
    nearby_text = patch_data.get("nearby_text", [])
    layer_hint = patch_data.get("layer")
    
    inferred = infer_discipline(material, nearby_text, layer_hint)
    
    # Case 2a: Heuristic agrees with target
    if inferred == target_discipline:
        if llm_discipline is None:
            return True, f"Heuristic: {inferred} (LLM was None)"
        else:
            return True, f"Heuristic override: {inferred} (LLM said {llm_discipline})"
    
    # Case 2b: Heuristic disagrees or is None
    if llm_discipline is None and inferred is None:
        return False, f"No discipline match (LLM: None, Heuristic: None)"
    elif llm_discipline is not None and llm_discipline != target_discipline:
        return False, f"Discipline mismatch: {llm_discipline} != {target_discipline}"
    elif inferred is not None and inferred != target_discipline:
        return False, f"Heuristic mismatch: {inferred} != {target_discipline}"
    else:
        return False, f"No match for {target_discipline}"


def assign_discipline_by_rules(
    material: Optional[str] = None,
    legend_tokens: Optional[List[str]] = None,
    layer_hint: Optional[str] = None
) -> tuple[Optional[str], str]:
    """
    Final fallback to assign discipline when LLM and heuristics both fail.
    
    Assignment priority:
    1. Material-only mapping (strongest signal)
    2. Dominant legend token
    3. Layer hint pattern
    4. None (unknown)
    
    Args:
        material: Material code
        legend_tokens: Legend tokens from page
        layer_hint: PDF layer name
        
    Returns:
        Tuple of (discipline, assignment_method)
        - discipline: "storm", "sanitary", "water", or None
        - assignment_method: "rule_material", "rule_legend", "rule_layer", or "unknown"
        
    Examples:
        >>> assign_discipline_by_rules(material="c900")
        ('water', 'rule_material')
        >>> assign_discipline_by_rules(material="sdr-35")
        ('sanitary', 'rule_material')
        >>> assign_discipline_by_rules(material="rcp")
        ('storm', 'rule_material')
    """
    # Rule 1: Material-only mapping (most reliable)
    if material:
        mat_lower = material.lower()
        
        # Water materials
        if any(x in mat_lower for x in ['c900', 'ductile', 'di', 'hdpe', 'pe']):
            logger.debug(f"Assigned water by material: {material}")
            return 'water', 'rule_material'
        
        # Sanitary materials
        if any(x in mat_lower for x in ['sdr-35', 'sdr 35', 'sdr35']):
            logger.debug(f"Assigned sanitary by material: {material}")
            return 'sanitary', 'rule_material'
        
        # Storm materials (RCP is most common)
        if 'rcp' in mat_lower:
            logger.debug(f"Assigned storm by material: {material}")
            return 'storm', 'rule_material'
        
        # PVC without specific grade - check other signals
        if 'pvc' in mat_lower:
            # PVC alone is ambiguous, continue to next rules
            pass
    
    # Rule 2: Dominant legend token
    if legend_tokens:
        legend_text = ' '.join(legend_tokens).lower()
        
        # Count discipline mentions
        storm_score = sum(1 for tok in ['storm', 'stm', 'sd', 'rcp'] if tok in legend_text)
        sanitary_score = sum(1 for tok in ['sanitary', 'sani', 'sewer', 'ss', 'sdr'] if tok in legend_text)
        water_score = sum(1 for tok in ['water', 'wat', 'wtr', 'c900', 'hydrant'] if tok in legend_text)
        
        max_score = max(storm_score, sanitary_score, water_score)
        if max_score > 0:
            if storm_score == max_score:
                logger.debug(f"Assigned storm by legend tokens (score={storm_score})")
                return 'storm', 'rule_legend'
            elif sanitary_score == max_score:
                logger.debug(f"Assigned sanitary by legend tokens (score={sanitary_score})")
                return 'sanitary', 'rule_legend'
            elif water_score == max_score:
                logger.debug(f"Assigned water by legend tokens (score={water_score})")
                return 'water', 'rule_legend'
    
    # Rule 3: Layer hint patterns
    if layer_hint:
        lh = layer_hint.lower()
        
        # Check for storm patterns
        if any(x in lh for x in ['stm', 'sd', 'storm', 'drain']):
            logger.debug(f"Assigned storm by layer: {layer_hint}")
            return 'storm', 'rule_layer'
        
        # Check for sanitary patterns
        if any(x in lh for x in ['san', 'ss', 'sewer', 'sanitary']):
            logger.debug(f"Assigned sanitary by layer: {layer_hint}")
            return 'sanitary', 'rule_layer'
        
        # Check for water patterns
        if any(x in lh for x in ['wat', 'wtr', 'water']):
            logger.debug(f"Assigned water by layer: {layer_hint}")
            return 'water', 'rule_layer'
    
    # Rule 4: Unable to assign
    logger.debug("Unable to assign discipline - no clear signals")
    return None, 'unknown'


__all__ = ["infer_discipline", "should_include_in_network", "assign_discipline_by_rules"]

