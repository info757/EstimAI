"""
API endpoints for evaluating takeoff quality (with or without ground truth).
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from backend.app.services.monitoring.production_eval import evaluate_production_run
from backend.app.services.monitoring.metrics_registry import get_metrics_registry

logger = logging.getLogger(__name__)

router = APIRouter()


class EvaluationRequest(BaseModel):
    """Request to evaluate a takeoff result."""
    result: dict[str, Any] = Field(..., description="Agent output to evaluate")
    pdf_text: str = Field(default="", description="Full text from PDF (for faithfulness check)")
    confidence_threshold: float = Field(default=0.70, ge=0.0, le=1.0)


class EvaluationResponse(BaseModel):
    """Response from production evaluation."""
    confidence: float = Field(..., description="Overall confidence score (0.0 to 1.0)")
    quality_scores: dict[str, float] = Field(..., description="Individual quality metrics")
    needs_hitl_review: bool = Field(..., description="Whether human review is recommended")
    flags: list[dict[str, Any]] = Field(..., description="List of warnings/failures")
    recommendation: str = Field(..., description="Human-readable recommendation")
    threshold: float = Field(..., description="Confidence threshold used")


class BenchmarkRequest(BaseModel):
    """Request to benchmark against ground truth."""
    result: dict[str, Any] = Field(..., description="Agent output")
    ground_truth: dict[str, Any] = Field(..., description="Expected output")
    categories: list[str] = Field(default=["pipes"], description="Categories to evaluate")


class BenchmarkResponse(BaseModel):
    """Response from benchmark evaluation."""
    scores: dict[str, dict[str, float]] = Field(..., description="Scores by category and metric")
    overall_accuracy: float = Field(..., description="Average accuracy across all metrics")


@router.post("/production", response_model=EvaluationResponse)
async def evaluate_production(req: EvaluationRequest):
    """
    Evaluate takeoff quality WITHOUT ground truth.
    
    Uses internal consistency checks, faithfulness, and completeness metrics.
    Useful for real-world PDFs where we don't have "answers".
    """
    try:
        logger.info("🔍 Evaluating production run (no ground truth)")
        
        evaluation = evaluate_production_run(
            result=req.result,
            pdf_text=req.pdf_text,
            confidence_threshold=req.confidence_threshold
        )
        
        return EvaluationResponse(
            confidence=evaluation["confidence"],
            quality_scores=evaluation["quality_scores"],
            needs_hitl_review=evaluation["needs_hitl_review"],
            flags=evaluation["flags"],
            recommendation=evaluation["recommendation"],
            threshold=evaluation["threshold"]
        )
    
    except Exception as e:
        logger.error(f"Production evaluation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e}")


@router.post("/benchmark", response_model=BenchmarkResponse)
async def evaluate_benchmark(req: BenchmarkRequest):
    """
    Benchmark takeoff accuracy WITH ground truth.
    
    Compares predicted values to known correct values.
    Useful for synthetic PDFs and regression testing.
    """
    try:
        logger.info(f"📊 Benchmarking against ground truth (categories: {req.categories})")
        
        registry = get_metrics_registry()
        
        all_scores = {}
        total_scores = []
        
        for category in req.categories:
            if category not in registry.categories:
                logger.warning(f"Unknown category: {category}")
                continue
            
            scores = registry.evaluate(category, req.result, req.ground_truth)
            all_scores[category] = scores
            total_scores.extend(scores.values())
        
        overall_accuracy = sum(total_scores) / len(total_scores) if total_scores else 0.0
        
        logger.info(f"✅ Benchmark complete: {overall_accuracy:.1%} accuracy")
        
        return BenchmarkResponse(
            scores=all_scores,
            overall_accuracy=overall_accuracy
        )
    
    except Exception as e:
        logger.error(f"Benchmark evaluation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Benchmark failed: {e}")


@router.get("/metrics")
async def list_metrics():
    """
    List all available metrics and categories.
    
    Useful for discovering what can be evaluated.
    """
    registry = get_metrics_registry()
    
    metrics_info = {}
    for category, metrics in registry.categories.items():
        metrics_info[category] = {
            name: metric.__class__.__doc__ or "No description"
            for name, metric in metrics.items()
        }
    
    return {
        "categories": list(registry.categories.keys()),
        "metrics": metrics_info
    }

