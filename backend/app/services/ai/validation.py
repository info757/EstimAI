"""
LLM response validation and sanity checks.

Implements automatic retry logic for improbable results (e.g., 0 detections
when there are clear candidates and legend present).
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of validation check."""
    
    def __init__(self, is_valid: bool, reason: str = "", should_retry: bool = False):
        self.is_valid = is_valid
        self.reason = reason
        self.should_retry = should_retry


def validate_classification_result(
    detections: List[Any],
    candidate_count: int,
    legend_present: bool,
    label_count: int = 0,
    min_expected_rate: float = 0.05  # Expect at least 5% classification rate
) -> ValidationResult:
    """
    Validate classification result for sanity.
    
    Args:
        detections: List of pipe detections returned by LLM
        candidate_count: Number of polyline candidates sent
        legend_present: Whether legend/ontology was provided
        label_count: Number of text labels available
        min_expected_rate: Minimum expected classification rate
    
    Returns:
        ValidationResult indicating if result is valid and if retry is needed
    """
    detection_count = len(detections)
    
    # Log validation inputs
    logger.info(f"🔍 Validation check:")
    logger.info(f"  Candidates: {candidate_count}")
    logger.info(f"  Detections: {detection_count}")
    logger.info(f"  Legend present: {legend_present}")
    logger.info(f"  Label count: {label_count}")
    
    # Check 1: Zero detections when we have good context
    if detection_count == 0 and candidate_count > 0:
        if legend_present or label_count > 5:
            # This is improbable - we have clear hints but LLM found nothing
            reason = (
                f"IMPROBABLE_ZERO: {candidate_count} candidates, "
                f"legend={'yes' if legend_present else 'no'}, "
                f"labels={label_count}, but 0 detections"
            )
            logger.warning(f"⚠️ {reason}")
            return ValidationResult(
                is_valid=False,
                reason=reason,
                should_retry=True
            )
    
    # Check 2: Very low classification rate with good context
    if candidate_count > 10 and detection_count > 0:
        rate = detection_count / candidate_count
        if rate < min_expected_rate and (legend_present or label_count > 10):
            reason = (
                f"LOW_CLASSIFICATION_RATE: {detection_count}/{candidate_count} "
                f"= {rate:.1%} (expected >{min_expected_rate:.0%})"
            )
            logger.warning(f"⚠️ {reason}")
            return ValidationResult(
                is_valid=False,
                reason=reason,
                should_retry=True
            )
    
    # All checks passed
    logger.info("✅ Validation passed")
    return ValidationResult(is_valid=True)


def log_run_invariants(
    candidate_count: int,
    label_count: int,
    legend_present: bool,
    model: str,
    temperature: float,
    seed: Optional[int],
    token_budget_used: Optional[int] = None,
    content_hash: Optional[str] = None,
    detection_count: Optional[int] = None
) -> None:
    """
    Log run-time invariants for reproducibility and debugging.
    
    This creates a structured log entry with all key parameters that affect
    the LLM classification result.
    """
    invariants = {
        "candidate_count": candidate_count,
        "label_count": label_count,
        "legend_present": legend_present,
        "model": model,
        "temperature": temperature,
        "seed": seed,
        "token_budget_used": token_budget_used,
        "content_hash": content_hash[:16] if content_hash else None,
        "detection_count": detection_count,
    }
    
    logger.info("📊 Run-time invariants:")
    for key, value in invariants.items():
        logger.info(f"  {key}={value}")
    
    return invariants

