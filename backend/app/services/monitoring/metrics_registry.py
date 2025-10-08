"""
Extensible metrics registry for evaluating agent performance.

Supports adding new metrics as we expand beyond pipes to earthwork, pavement, buildings, etc.
"""
import logging
from typing import Any, Dict, List, Optional, Protocol
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class Metric(ABC):
    """Base class for all metrics."""
    
    @abstractmethod
    def compute(self, predicted: Any, ground_truth: Any) -> float:
        """
        Compute metric score.
        
        Returns:
            Score between 0.0 and 1.0 (1.0 = perfect)
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Metric name."""
        pass


class PipeCountAccuracy(Metric):
    """Measures accuracy of pipe count detection."""
    
    @property
    def name(self) -> str:
        return "pipe_count_accuracy"
    
    def compute(self, predicted: Dict, ground_truth: Dict) -> float:
        pred_count = predicted.get("pipes_total", 0)
        
        # Ground truth might have pipes in different formats
        if "pipes" in ground_truth:
            gt_count = sum(len(ground_truth["pipes"].get(k, [])) for k in ["storm", "sanitary", "water"])
        elif "profiles" in ground_truth:
            gt_count = len(ground_truth.get("profiles", {}))
        else:
            gt_count = 0
        
        if gt_count == 0:
            return 1.0 if pred_count == 0 else 0.0
        
        error_rate = abs(pred_count - gt_count) / gt_count
        # Perfect = 1.0, 50% error = 0.0
        return max(0.0, 1.0 - (error_rate / 0.5))


class ElevationAccuracy(Metric):
    """Measures accuracy of invert elevation extraction."""
    
    @property
    def name(self) -> str:
        return "elevation_accuracy"
    
    def compute(self, predicted: Dict, ground_truth: Dict) -> float:
        """
        Compare predicted elevations to ground truth.
        
        Returns average accuracy across all pipes with elevation data.
        """
        scores = []
        
        # Get predicted pipes
        networks = predicted.get("proposed_review", {}).get("payload", {}).get("networks", {})
        
        # Get ground truth profiles
        gt_profiles = ground_truth.get("profiles", {})
        
        for network_name, gt_prof in gt_profiles.items():
            network = networks.get(network_name, {})
            pipes = network.get("pipes", [])
            
            if not pipes:
                continue
            
            # Compare first pipe (simplified - could match by ID)
            pipe = pipes[0]
            ie_in_pred = pipe.get("extra", {}).get("invert_in_ft")
            ie_out_pred = pipe.get("extra", {}).get("invert_out_ft")
            
            ie_in_gt = gt_prof.get("invert_start")
            ie_out_gt = gt_prof.get("invert_end")
            
            # Score each elevation
            if ie_in_pred is not None and ie_in_gt is not None:
                error = abs(ie_in_pred - ie_in_gt)
                # Within 1 ft = 100%, 5 ft = 0%
                scores.append(max(0.0, 1.0 - (error / 5.0)))
            
            if ie_out_pred is not None and ie_out_gt is not None:
                error = abs(ie_out_pred - ie_out_gt)
                scores.append(max(0.0, 1.0 - (error / 5.0)))
        
        return sum(scores) / len(scores) if scores else 0.0


class LengthAccuracy(Metric):
    """Measures accuracy of pipe length measurements."""
    
    @property
    def name(self) -> str:
        return "length_accuracy"
    
    def compute(self, predicted: Dict, ground_truth: Dict) -> float:
        """
        Compare predicted lengths to ground truth.
        
        Returns average accuracy across all pipes.
        """
        scores = []
        
        networks = predicted.get("proposed_review", {}).get("payload", {}).get("networks", {})
        gt_profiles = ground_truth.get("profiles", {})
        
        for network_name, gt_prof in gt_profiles.items():
            network = networks.get(network_name, {})
            pipes = network.get("pipes", [])
            
            if not pipes:
                continue
            
            pipe = pipes[0]
            pred_len = pipe.get("length_ft", 0)
            gt_len = gt_prof.get("end_station", 0)
            
            if gt_len == 0:
                continue
            
            error_pct = abs(pred_len - gt_len) / gt_len
            # Within 5% = 100%, 20% = 0%
            score = max(0.0, 1.0 - (error_pct / 0.20))
            scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0.0


class MaterialAccuracy(Metric):
    """Measures accuracy of material classification."""
    
    @property
    def name(self) -> str:
        return "material_accuracy"
    
    def compute(self, predicted: Dict, ground_truth: Dict) -> float:
        """Check if materials match (fuzzy matching)."""
        scores = []
        
        networks = predicted.get("proposed_review", {}).get("payload", {}).get("networks", {})
        gt_profiles = ground_truth.get("profiles", {})
        
        for network_name, gt_prof in gt_profiles.items():
            network = networks.get(network_name, {})
            pipes = network.get("pipes", [])
            
            if not pipes:
                continue
            
            pipe = pipes[0]
            pred_mat = (pipe.get("mat") or "").upper()
            gt_mat = (gt_prof.get("material") or "").upper()
            
            # Fuzzy matching
            if pred_mat in gt_mat or gt_mat in pred_mat:
                scores.append(1.0)
            elif any(abbrev in pred_mat for abbrev in ["PVC", "DI", "RCP", "HDPE"]):
                # Partial credit for getting material type
                scores.append(0.5)
            else:
                scores.append(0.0)
        
        return sum(scores) / len(scores) if scores else 0.0


class MetricsRegistry:
    """
    Central registry for all takeoff metrics.
    
    Extensible - add new categories and metrics as we expand beyond pipes.
    """
    
    def __init__(self):
        self.categories = {
            "pipes": {
                "count": PipeCountAccuracy(),
                "elevation": ElevationAccuracy(),
                "length": LengthAccuracy(),
                "material": MaterialAccuracy()
            }
            # Future categories:
            # "earthwork": {...},
            # "pavement": {...},
            # "buildings": {...}
        }
    
    def add_category(self, name: str):
        """Add a new category (e.g., 'earthwork', 'pavement')."""
        if name not in self.categories:
            self.categories[name] = {}
            logger.info(f"✅ Added metrics category: {name}")
    
    def add_metric(self, category: str, metric: Metric):
        """Add a metric to a category."""
        if category not in self.categories:
            self.add_category(category)
        
        self.categories[category][metric.name] = metric
        logger.info(f"✅ Added metric: {category}.{metric.name}")
    
    def evaluate(self, category: str, predicted: Dict, ground_truth: Dict) -> Dict[str, float]:
        """
        Run all metrics for a category.
        
        Args:
            category: Category name (e.g., "pipes")
            predicted: Agent output
            ground_truth: Expected output
        
        Returns:
            Dict of metric_name -> score
        """
        if category not in self.categories:
            logger.warning(f"Unknown category: {category}")
            return {}
        
        results = {}
        for metric_name, metric in self.categories[category].items():
            try:
                score = metric.compute(predicted, ground_truth)
                results[metric_name] = score
                logger.info(f"  {metric_name}: {score:.2%}")
            except Exception as e:
                logger.error(f"Failed to compute {metric_name}: {e}")
                results[metric_name] = 0.0
        
        return results
    
    def evaluate_all(self, predicted: Dict, ground_truth: Dict) -> Dict[str, Dict[str, float]]:
        """Run all metrics across all categories."""
        results = {}
        for category in self.categories:
            results[category] = self.evaluate(category, predicted, ground_truth)
        return results


# Singleton instance
_registry: Optional[MetricsRegistry] = None


def get_metrics_registry() -> MetricsRegistry:
    """Get or create the global metrics registry."""
    global _registry
    if _registry is None:
        _registry = MetricsRegistry()
    return _registry
