"""
Unknown/unclassified pipe handling.

Collects pipes that couldn't be classified with confidence and routes them
to Human-In-The-Loop (HITL) review. Never silently drops candidates.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def collect_unknowns(
    all_detections: List[Any],
    classified_ids: set[str]
) -> Dict[str, Any]:
    """
    Collect pipes that weren't classified into any network.
    
    These are NOT silently dropped. Instead, they're flagged for HITL review.
    
    Args:
        all_detections: All pipe detections from LLM
        classified_ids: Set of polyline IDs that were assigned to storm/sanitary/water
        
    Returns:
        Network dict with unknown pipes and HITL flags
    """
    unknown_pipes = []
    
    for detection in all_detections:
        if detection.polyline_id not in classified_ids:
            # This pipe was excluded - find out why
            discipline = detection.attrs.discipline
            confidence = detection.attrs.confidence or 0.0
            reason = detection.reason
            
            # Determine exclusion reason
            if discipline is None or discipline == "unknown":
                exclusion_reason = "NO_DISCIPLINE"
            elif discipline not in ["storm", "sanitary", "water"]:
                exclusion_reason = f"INVALID_DISCIPLINE_{discipline}"
            elif confidence < 0.35:  # Using default threshold
                exclusion_reason = f"LOW_CONFIDENCE_{confidence:.2f}"
            else:
                exclusion_reason = "UNKNOWN"
            
            # Create pipe dict with HITL flag
            unknown_pipe = {
                "id": detection.polyline_id,
                "discipline": discipline,
                "material": detection.attrs.material,
                "dia_in": detection.attrs.dia_in,
                "length_ft": 0.0,  # Will be populated from geometry
                "confidence": confidence,
                "reason": reason,
                "exclusion_reason": exclusion_reason,
                "hitl_required": True,
                "qa_flags": [{
                    "code": f"UNCLASSIFIED_{exclusion_reason}",
                    "message": f"Pipe excluded from networks: {exclusion_reason}. Requires HITL review.",
                    "severity": "warning"
                }]
            }
            
            unknown_pipes.append(unknown_pipe)
            logger.info(
                f"🤔 Unknown: {detection.polyline_id} - {exclusion_reason} "
                f"(discipline={discipline}, conf={confidence:.2f})"
            )
    
    if unknown_pipes:
        logger.warning(
            f"⚠️ {len(unknown_pipes)} pipes flagged as UNKNOWN - routed to HITL, NOT silently dropped"
        )
    
    return {
        "nodes": [],
        "pipes": unknown_pipes,
        "qa_flags": [{
            "code": "UNKNOWNS_PRESENT",
            "message": f"{len(unknown_pipes)} unclassified pipes require HITL review",
            "severity": "warning"
        }] if unknown_pipes else []
    }


def merge_unknowns_into_response(
    networks: Dict[str, Any],
    unknown_network: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Add unknown network to response if it has pipes.
    
    Args:
        networks: Existing networks dict (storm, sanitary, water)
        unknown_network: Unknown network with HITL-flagged pipes
        
    Returns:
        Updated networks dict with unknown network if applicable
    """
    if unknown_network and unknown_network.get("pipes"):
        networks["unknown"] = unknown_network
        logger.info(
            f"Added 'unknown' network with {len(unknown_network['pipes'])} pipes for HITL"
        )
    
    return networks

