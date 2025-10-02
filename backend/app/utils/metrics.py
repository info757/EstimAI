"""Metrics calculation utilities."""
from typing import Dict, List, Any, Tuple
import math
import statistics
from sqlalchemy.orm import Session
from ..models import CountItem

def compute_pr_f1(tp: int, fp: int, fn: int) -> Dict[str, float]:
    """
    Compute precision, recall, and F1 score from true positives, false positives, and false negatives.
    
    Args:
        tp: True positives
        fp: False positives  
        fn: False negatives
        
    Returns:
        Dictionary with precision, recall, and f1 scores
    """
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1
    }

def localization_stats(pairs: List[Tuple[Tuple[float, float], Tuple[float, float]]], ppf: float) -> Dict[str, float]:
    """
    Compute localization accuracy statistics from coordinate pairs.
    
    Args:
        pairs: List of (predicted_coords, ground_truth_coords) tuples
        ppf: Points per foot conversion factor
        
    Returns:
        Dictionary with mae_ft, p95_ft, max_ft (all in feet)
    """
    if not pairs:
        return {"mae_ft": 0.0, "p95_ft": 0.0, "max_ft": 0.0}
    
    distances_ft = []
    for (pred_x, pred_y), (gt_x, gt_y) in pairs:
        # Calculate Euclidean distance in PDF points
        distance_points = math.sqrt((pred_x - gt_x)**2 + (pred_y - gt_y)**2)
        # Convert to feet
        distance_ft = distance_points / ppf
        distances_ft.append(distance_ft)
    
    # Calculate statistics
    mae_ft = statistics.mean(distances_ft)
    distances_ft.sort()
    p95_index = int(0.95 * len(distances_ft))
    p95_ft = distances_ft[p95_index] if p95_index < len(distances_ft) else distances_ft[-1]
    max_ft = max(distances_ft)
    
    return {
        "mae_ft": mae_ft,
        "p95_ft": p95_ft,
        "max_ft": max_ft
    }

def precision_by_confidence(items: List[Tuple[float, bool]], bins: List[Tuple[float, float]]) -> List[Dict]:
    """
    Compute precision for confidence bins.
    
    Args:
        items: List of (confidence, is_tp) tuples
        bins: List of (min_confidence, max_confidence) tuples
        
    Returns:
        List of dictionaries with bin info and precision
    """
    results = []
    
    for min_conf, max_conf in bins:
        # Filter items in this confidence bin
        bin_items = [
            is_tp for confidence, is_tp in items 
            if min_conf <= confidence < max_conf
        ]
        
        if not bin_items:
            results.append({
                "min_confidence": min_conf,
                "max_confidence": max_conf,
                "count": 0,
                "precision": 0.0
            })
            continue
        
        # Calculate precision for this bin
        tp_count = sum(bin_items)
        total_count = len(bin_items)
        precision = tp_count / total_count if total_count > 0 else 0.0
        
        results.append({
            "min_confidence": min_conf,
            "max_confidence": max_conf,
            "count": total_count,
            "precision": precision
        })
    
    return results

def calculate_detection_metrics(count_items: List[CountItem]) -> Dict[str, Any]:
    """Calculate detection metrics for a list of count items."""
    if not count_items:
        return {
            "total_detections": 0,
            "average_confidence": 0.0,
            "confidence_distribution": {},
            "type_distribution": {}
        }
    
    total_detections = len(count_items)
    confidences = [item.confidence for item in count_items]
    average_confidence = sum(confidences) / len(confidences)
    
    # Confidence distribution
    confidence_ranges = {
        "high": len([c for c in confidences if c >= 0.8]),
        "medium": len([c for c in confidences if 0.5 <= c < 0.8]),
        "low": len([c for c in confidences if c < 0.5])
    }
    
    # Type distribution
    type_counts = {}
    for item in count_items:
        type_counts[item.type] = type_counts.get(item.type, 0) + 1
    
    return {
        "total_detections": total_detections,
        "average_confidence": round(average_confidence, 3),
        "confidence_distribution": confidence_ranges,
        "type_distribution": type_counts
    }

def calculate_review_metrics(count_items: List[CountItem]) -> Dict[str, Any]:
    """Calculate review metrics for a list of count items."""
    if not count_items:
        return {
            "total_items": 0,
            "pending": 0,
            "accepted": 0,
            "rejected": 0,
            "edited": 0,
            "completion_rate": 0.0,
            "acceptance_rate": 0.0
        }
    
    status_counts = {}
    for item in count_items:
        status_counts[item.status] = status_counts.get(item.status, 0) + 1
    
    total_items = len(count_items)
    completed = status_counts.get("accepted", 0) + status_counts.get("rejected", 0) + status_counts.get("edited", 0)
    accepted = status_counts.get("accepted", 0)
    
    return {
        "total_items": total_items,
        "pending": status_counts.get("pending", 0),
        "accepted": accepted,
        "rejected": status_counts.get("rejected", 0),
        "edited": status_counts.get("edited", 0),
        "completion_rate": round(completed / total_items, 3) if total_items > 0 else 0.0,
        "acceptance_rate": round(accepted / total_items, 3) if total_items > 0 else 0.0
    }

def get_quality_metrics(session: Session, file: str, pages: List[int]) -> Dict[str, Any]:
    """Get comprehensive quality metrics for a file and pages."""
    count_items = session.query(CountItem).filter(
        CountItem.file == file,
        CountItem.page.in_(pages)
    ).all()
    
    detection_metrics = calculate_detection_metrics(count_items)
    review_metrics = calculate_review_metrics(count_items)
    
    return {
        "detection": detection_metrics,
        "review": review_metrics,
        "file": file,
        "pages": pages,
        "total_items": len(count_items)
    }
