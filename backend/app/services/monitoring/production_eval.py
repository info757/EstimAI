"""
Production evaluation for real PDFs without ground truth.

Assesses extraction quality using:
- Internal consistency checks
- Faithfulness (values actually in PDF)
- Completeness metrics
- Physical reasonableness
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def check_consistency(result: dict[str, Any]) -> list[tuple[str, float, str]]:
    """
    Validate internal consistency without ground truth.
    
    Returns list of (check_name, score, message) tuples.
    Score: 1.0 = pass, 0.5 = warning, 0.0 = fail
    """
    checks = []
    
    pipes = result.get("pipes", [])
    if not pipes:
        return [("no_pipes", 0.0, "No pipes detected")]
    
    # Check 1: Elevations make physical sense
    for i, pipe in enumerate(pipes):
        ie_in = pipe.get("invert_in")
        ie_out = pipe.get("invert_out")
        gl = pipe.get("ground_level")
        
        # Gravity pipes should flow downhill (storm/sanitary)
        discipline = pipe.get("discipline", "").lower()
        if ie_in and ie_out and discipline in ["storm", "sanitary"]:
            if ie_in < ie_out:
                checks.append((
                    f"pipe_{i}_elevation_flow",
                    0.5,
                    f"Pipe {i} flows uphill? IE_in={ie_in:.1f} < IE_out={ie_out:.1f}"
                ))
            else:
                checks.append((f"pipe_{i}_elevation_flow", 1.0, "OK"))
        
        # Depth should be positive and reasonable
        if gl and ie_in:
            depth = gl - ie_in
            if depth < 0:
                checks.append((
                    f"pipe_{i}_depth_sign",
                    0.0,
                    f"Pipe {i} has negative depth: {depth:.1f}ft"
                ))
            elif depth > 50:
                checks.append((
                    f"pipe_{i}_depth_reasonable",
                    0.5,
                    f"Pipe {i} is very deep: {depth:.1f}ft (>50ft)"
                ))
            elif depth < 1:
                checks.append((
                    f"pipe_{i}_depth_shallow",
                    0.5,
                    f"Pipe {i} is very shallow: {depth:.1f}ft (<1ft)"
                ))
            else:
                checks.append((f"pipe_{i}_depth_reasonable", 1.0, "OK"))
    
    # Check 2: Lengths are reasonable
    for i, pipe in enumerate(pipes):
        length = pipe.get("length_ft", 0)
        if length < 5:
            checks.append((
                f"pipe_{i}_length_min",
                0.5,
                f"Pipe {i} is very short: {length:.1f}ft"
            ))
        elif length > 5000:
            checks.append((
                f"pipe_{i}_length_max",
                0.5,
                f"Pipe {i} is very long: {length:.1f}ft (>5000ft)"
            ))
        else:
            checks.append((f"pipe_{i}_length_reasonable", 1.0, "OK"))
    
    # Check 3: Materials are valid
    valid_materials = ["PVC", "DI", "RCP", "HDPE", "VCP", "CONCRETE", "COPPER", "PE", "DUCTILE"]
    for i, pipe in enumerate(pipes):
        mat = (pipe.get("material") or "").upper()
        if not mat:
            checks.append((
                f"pipe_{i}_material_missing",
                0.5,
                f"Pipe {i} has no material specified"
            ))
        elif any(vm in mat for vm in valid_materials):
            checks.append((f"pipe_{i}_material_valid", 1.0, "OK"))
        else:
            checks.append((
                f"pipe_{i}_material_unknown",
                0.5,
                f"Pipe {i} has unknown material: {mat}"
            ))
    
    # Check 4: Diameters are reasonable
    for i, pipe in enumerate(pipes):
        dia = pipe.get("dia_in", 0)
        if dia < 4:
            checks.append((
                f"pipe_{i}_dia_small",
                0.5,
                f"Pipe {i} has small diameter: {dia}in (<4in)"
            ))
        elif dia > 120:
            checks.append((
                f"pipe_{i}_dia_large",
                0.5,
                f"Pipe {i} has large diameter: {dia}in (>120in)"
            ))
        else:
            checks.append((f"pipe_{i}_dia_reasonable", 1.0, "OK"))
    
    # Check 5: Network consistency
    disciplines = [p.get("discipline") for p in pipes if p.get("discipline")]
    if disciplines:
        unique_disciplines = set(disciplines)
        if len(unique_disciplines) > 5:
            checks.append((
                "network_diversity",
                0.5,
                f"Many different disciplines detected: {unique_disciplines}"
            ))
        else:
            checks.append(("network_diversity", 1.0, "OK"))
    
    return checks


def assess_extraction_quality(result: dict[str, Any], pdf_text: str) -> dict[str, float]:
    """
    Score extraction quality without ground truth.
    
    Returns dict of quality scores (0.0 to 1.0).
    """
    scores = {}
    
    pipes = result.get("pipes", [])
    if not pipes:
        return {
            "completeness": 0.0,
            "elevation_coverage": 0.0,
            "faithfulness": 0.0,
            "material_coverage": 0.0,
            "diameter_coverage": 0.0
        }
    
    # Completeness: How many pipes have all core attributes?
    complete_pipes = sum(
        1 for p in pipes
        if p.get("material") and p.get("dia_in") and p.get("length_ft") and p.get("discipline")
    )
    scores["completeness"] = complete_pipes / len(pipes)
    
    # Elevation coverage: How many pipes have elevation data?
    pipes_with_elevations = sum(
        1 for p in pipes
        if p.get("invert_in") or p.get("invert_out") or p.get("ground_level")
    )
    scores["elevation_coverage"] = pipes_with_elevations / len(pipes)
    
    # Material coverage
    pipes_with_material = sum(1 for p in pipes if p.get("material"))
    scores["material_coverage"] = pipes_with_material / len(pipes)
    
    # Diameter coverage
    pipes_with_diameter = sum(1 for p in pipes if p.get("dia_in"))
    scores["diameter_coverage"] = pipes_with_diameter / len(pipes)
    
    # Faithfulness: Are extracted values actually in the PDF?
    # (Simplified check - looks for material names and elevation numbers)
    values_found_in_pdf = 0
    values_checked = 0
    
    pdf_text_upper = pdf_text.upper()
    
    for pipe in pipes:
        # Check material
        if pipe.get("material"):
            values_checked += 1
            mat = pipe["material"].upper()
            # Check if material or common abbreviation appears
            if mat in pdf_text_upper or any(
                abbr in pdf_text_upper for abbr in [mat[:3], mat[:2]]
            ):
                values_found_in_pdf += 1
        
        # Check elevations (look for the number as a string)
        for elev_key in ["invert_in", "invert_out", "ground_level"]:
            if pipe.get(elev_key):
                values_checked += 1
                elev_str = f"{pipe[elev_key]:.1f}".replace(".0", "")
                if elev_str in pdf_text:
                    values_found_in_pdf += 1
    
    scores["faithfulness"] = values_found_in_pdf / values_checked if values_checked else 0.0
    
    return scores


def calculate_overall_confidence(
    quality_scores: dict[str, float],
    consistency_checks: list[tuple[str, float, str]]
) -> float:
    """
    Calculate overall confidence score from quality and consistency.
    
    Returns float 0.0 to 1.0.
    """
    # Quality component (weighted average)
    quality_confidence = (
        quality_scores.get("completeness", 0) * 0.25 +
        quality_scores.get("elevation_coverage", 0) * 0.25 +
        quality_scores.get("faithfulness", 0) * 0.30 +
        quality_scores.get("material_coverage", 0) * 0.10 +
        quality_scores.get("diameter_coverage", 0) * 0.10
    )
    
    # Consistency component (average of all checks)
    if consistency_checks:
        consistency_scores = [score for _, score, _ in consistency_checks]
        consistency_confidence = sum(consistency_scores) / len(consistency_scores)
    else:
        consistency_confidence = 0.0
    
    # Overall: 60% quality, 40% consistency
    overall = quality_confidence * 0.6 + consistency_confidence * 0.4
    
    return overall


def evaluate_production_run(
    result: dict[str, Any],
    pdf_text: str,
    confidence_threshold: float = 0.70
) -> dict[str, Any]:
    """
    Evaluate a production run without ground truth.
    
    Args:
        result: Agent output (dict with "pipes", "summary", etc.)
        pdf_text: All text extracted from the PDF
        confidence_threshold: Minimum confidence to avoid HITL review
    
    Returns:
        dict with:
            - confidence: overall score 0.0 to 1.0
            - quality_scores: dict of individual quality metrics
            - consistency_checks: list of (name, score, message)
            - needs_hitl_review: bool
            - flags: list of failed/warning checks
            - recommendation: str
    """
    logger.info("🔍 Evaluating production run (no ground truth)")
    
    # Run consistency checks
    consistency_checks = check_consistency(result)
    
    # Assess quality
    quality_scores = assess_extraction_quality(result, pdf_text)
    
    # Calculate overall confidence
    overall_confidence = calculate_overall_confidence(quality_scores, consistency_checks)
    
    # Flag for HITL if low confidence
    needs_review = overall_confidence < confidence_threshold
    
    # Collect flags (warnings and failures)
    flags = [
        {"check": name, "score": score, "message": msg}
        for name, score, msg in consistency_checks
        if score < 1.0
    ]
    
    # Generate recommendation
    if overall_confidence >= 0.85:
        recommendation = "High confidence - ready for use"
    elif overall_confidence >= confidence_threshold:
        recommendation = "Acceptable confidence - spot check recommended"
    elif overall_confidence >= 0.50:
        recommendation = "Low confidence - human review required"
    else:
        recommendation = "Very low confidence - manual takeoff recommended"
    
    evaluation = {
        "confidence": overall_confidence,
        "quality_scores": quality_scores,
        "consistency_checks": consistency_checks,
        "needs_hitl_review": needs_review,
        "flags": flags,
        "recommendation": recommendation,
        "threshold": confidence_threshold
    }
    
    logger.info(
        f"📊 Evaluation complete: confidence={overall_confidence:.2f}, "
        f"needs_review={needs_review}, flags={len(flags)}"
    )
    
    return evaluation

