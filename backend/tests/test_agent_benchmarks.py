"""
Agent benchmark tests using synthetic PDFs with ground truth.

Measures accuracy and tracks improvement over time using LangSmith.
"""
import pytest
import json
import time
from pathlib import Path
from typing import Dict, Any

from backend.app.services.monitoring import get_metrics_registry, trace_vision_takeoff
from backend.app.agent.takeoff_impl import create_default_agent


@pytest.mark.benchmark
@pytest.mark.parametrize("pdf_name", [
    "site_plan_lin_s10.pdf",
    "site_plan_lin_s11.pdf",
    "site_plan_s07.pdf",
])
def test_synthetic_pdf_accuracy(pdf_name):
    """
    Test agent accuracy against synthetic PDFs with known ground truth.
    
    This test:
    1. Runs takeoff on synthetic PDF
    2. Compares results to ground truth JSON
    3. Calculates accuracy metrics
    4. Logs to LangSmith for tracking over time
    """
    # Paths
    synthetic_dir = Path("synthetic")
    pdf_path = synthetic_dir / pdf_name
    
    # Derive ground truth filename
    gt_name = pdf_name.replace("site_plan_", "ground_truth_").replace(".pdf", ".json")
    gt_path = synthetic_dir / gt_name
    
    if not pdf_path.exists():
        pytest.skip(f"PDF not found: {pdf_path}")
    
    if not gt_path.exists():
        pytest.skip(f"Ground truth not found: {gt_path}")
    
    # Load ground truth
    ground_truth = json.loads(gt_path.read_text())
    
    # Run takeoff
    agent = create_default_agent()
    
    start_time = time.time()
    response = agent.run({
        "session_id": f"benchmark_{pdf_name}",
        "file_ref": str(pdf_path),
        "options": {}
    })
    latency_ms = (time.time() - start_time) * 1000
    
    # Convert to dict for metrics
    result_dict = response.model_dump() if hasattr(response, "model_dump") else response
    
    # Evaluate metrics
    registry = get_metrics_registry()
    metrics = registry.evaluate("pipes", result_dict, ground_truth)
    
    # Log to LangSmith
    trace_vision_takeoff(
        pdf_path=str(pdf_path),
        page_count=2,  # Our synthetic PDFs have 2 pages
        result=result_dict,
        latency_ms=latency_ms
    )
    
    # Print results
    print(f"\n{'='*60}")
    print(f"Benchmark: {pdf_name}")
    print(f"{'='*60}")
    for metric_name, score in metrics.items():
        print(f"  {metric_name}: {score:.2%}")
    print(f"  Latency: {latency_ms:.0f}ms")
    print(f"{'='*60}\n")
    
    # Assert minimum thresholds
    assert metrics.get("count", 0) > 0.80, f"Pipe count accuracy {metrics['count']:.2%} below 80%"
    
    # Elevation accuracy should be high (within 5ft)
    if metrics.get("elevation", 0) > 0:  # Only if elevations were extracted
        assert metrics["elevation"] > 0.70, f"Elevation accuracy {metrics['elevation']:.2%} below 70%"


@pytest.mark.benchmark
def test_benchmark_summary():
    """
    Run all synthetic PDFs and generate summary report.
    
    This test provides an overall view of agent performance.
    """
    synthetic_dir = Path("synthetic")
    pdf_files = list(synthetic_dir.glob("site_plan_*.pdf"))
    
    if not pdf_files:
        pytest.skip("No synthetic PDFs found")
    
    results = []
    registry = get_metrics_registry()
    
    for pdf_path in pdf_files[:5]:  # Limit to 5 for speed
        # Get ground truth
        gt_name = pdf_path.name.replace("site_plan_", "ground_truth_").replace(".pdf", ".json")
        gt_path = pdf_path.parent / gt_name
        
        if not gt_path.exists():
            continue
        
        ground_truth = json.loads(gt_path.read_text())
        
        # Run takeoff
        agent = create_default_agent()
        start_time = time.time()
        
        try:
            response = agent.run({
                "session_id": f"summary_{pdf_path.stem}",
                "file_ref": str(pdf_path),
                "options": {}
            })
            latency_ms = (time.time() - start_time) * 1000
            
            result_dict = response.model_dump() if hasattr(response, "model_dump") else response
            
            # Evaluate
            metrics = registry.evaluate("pipes", result_dict, ground_truth)
            
            results.append({
                "pdf": pdf_path.name,
                "metrics": metrics,
                "latency_ms": latency_ms,
                "success": True
            })
        
        except Exception as e:
            logger.error(f"Failed on {pdf_path.name}: {e}")
            results.append({
                "pdf": pdf_path.name,
                "error": str(e),
                "success": False
            })
    
    # Calculate averages
    successful = [r for r in results if r.get("success")]
    
    if not successful:
        pytest.fail("No successful runs")
    
    avg_metrics = {}
    for metric_name in ["count", "elevation", "length", "material"]:
        scores = [r["metrics"].get(metric_name, 0) for r in successful if metric_name in r.get("metrics", {})]
        if scores:
            avg_metrics[metric_name] = sum(scores) / len(scores)
    
    avg_latency = sum(r["latency_ms"] for r in successful) / len(successful)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"BENCHMARK SUMMARY ({len(successful)}/{len(results)} successful)")
    print(f"{'='*60}")
    for metric_name, score in avg_metrics.items():
        print(f"  Avg {metric_name}: {score:.2%}")
    print(f"  Avg latency: {avg_latency:.0f}ms")
    print(f"{'='*60}\n")
    
    # Assert overall quality
    assert avg_metrics.get("count", 0) > 0.75, "Average pipe count accuracy below 75%"


@pytest.mark.benchmark
def test_compare_vision_vs_apryse():
    """
    Compare Vision-only vs Apryse+LLM approaches.
    
    This test helps us understand trade-offs between approaches.
    """
    # This would run the same PDF through both pipelines
    # and compare accuracy, latency, and cost
    pytest.skip("Implement when both pipelines are stable")


if __name__ == "__main__":
    # Run benchmarks locally
    pytest.main([__file__, "-v", "-m", "benchmark"])
