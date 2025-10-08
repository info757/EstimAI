# EstimAI Agent Monitoring & Evaluation

This module provides observability and evaluation for EstimAI agents using **LangSmith** and **RAGAS**.

## Overview

### LangSmith (Tracing & Observability)
- Traces every LLM call with inputs/outputs
- Tracks latency, token usage, costs
- Visualizes agent decision flow
- Stores runs for historical analysis

### RAGAS (Evaluation Framework)
- Measures accuracy against ground truth
- Custom metrics for construction takeoff
- Tracks improvement over time

## Setup

### 1. Install Dependencies

```bash
pip install langsmith ragas langchain langchain-openai
```

### 2. Set Environment Variables

```bash
export LANGSMITH_API_KEY="your-api-key-here"
export LANGSMITH_PROJECT="estimai-takeoff"
export LANGSMITH_TRACING="true"
```

### 3. Run Benchmarks

```bash
# Run all benchmark tests
pytest backend/tests/test_agent_benchmarks.py -v -m benchmark

# Run specific test
pytest backend/tests/test_agent_benchmarks.py::test_synthetic_pdf_accuracy -v

# View results at https://smith.langchain.com
```

## Current Metrics

### Pipes (Implemented)
- **Count Accuracy**: Predicted vs ground truth pipe count
- **Elevation Accuracy**: IE values within ±5 ft
- **Length Accuracy**: LF within ±20%
- **Material Accuracy**: Fuzzy matching on material names

### Future Categories (Extensible)
- **Earthwork**: Volume accuracy, cut/fill detection
- **Pavement**: Area accuracy, thickness extraction
- **Buildings**: Count, area, height measurements

## Architecture

### Extensible Design

```python
# Add a new category
registry = get_metrics_registry()
registry.add_category("earthwork")

# Add metrics to the category
registry.add_metric("earthwork", VolumeAccuracy())
registry.add_metric("earthwork", CutFillAccuracy())

# Evaluate
metrics = registry.evaluate("earthwork", predicted, ground_truth)
```

### Hierarchical Tracing

```
Takeoff Agent (root)
├── Pipe Detection
│   ├── Vision LLM (storm)
│   ├── Vision LLM (sanitary)
│   └── Vision LLM (water)
├── Elevation Extraction
└── [Future] Earthwork Detection
    ├── Contour Extraction
    └── Volume Calculation
```

Each component traces independently, so adding new detectors doesn't affect existing traces.

## Usage Examples

### Trace a Vision Takeoff

```python
from backend.app.services.monitoring import trace_vision_takeoff

result = extract_pipes_from_pdf_vision(pdf_path, page_num=0)
trace_vision_takeoff(
    pdf_path=pdf_path,
    page_count=2,
    result=result,
    latency_ms=12500
)
```

### Trace Pipe Classification

```python
from backend.app.services.monitoring import trace_pipe_classification

detections = classifier.classify(patches)
trace_pipe_classification(
    patches=patches,
    model="gpt-4o-mini",
    detections=detections,
    latency_ms=3500,
    token_usage={"prompt": 1500, "completion": 800, "total": 2300}
)
```

### Evaluate Against Ground Truth

```python
from backend.app.services.monitoring import get_metrics_registry

registry = get_metrics_registry()
metrics = registry.evaluate("pipes", predicted_result, ground_truth)

print(f"Count accuracy: {metrics['count']:.2%}")
print(f"Elevation accuracy: {metrics['elevation']:.2%}")
```

## LangSmith Dashboard

View your traces at: https://smith.langchain.com

**Key Views:**
- **Runs**: See all takeoff operations with inputs/outputs
- **Traces**: Visualize nested LLM calls
- **Metrics**: Track accuracy trends over time
- **Comparisons**: A/B test different approaches (Vision vs Apryse)

## Adding New Metrics

### 1. Create Metric Class

```python
# backend/app/services/monitoring/metrics/earthwork.py

from backend.app.services.monitoring.metrics_registry import Metric

class VolumeAccuracy(Metric):
    @property
    def name(self) -> str:
        return "volume_accuracy"
    
    def compute(self, predicted: Dict, ground_truth: Dict) -> float:
        pred_vol = predicted.get("cut_volume_cy", 0)
        gt_vol = ground_truth.get("earthwork", {}).get("cut_volume_cy", 0)
        
        if gt_vol == 0:
            return 1.0 if pred_vol == 0 else 0.0
        
        error_pct = abs(pred_vol - gt_vol) / gt_vol
        # Within 10% = 100%, 30% = 0%
        return max(0.0, 1.0 - (error_pct / 0.30))
```

### 2. Register Metric

```python
# In your detector or startup code
from backend.app.services.monitoring import get_metrics_registry
from backend.app.services.monitoring.metrics.earthwork import VolumeAccuracy

registry = get_metrics_registry()
registry.add_metric("earthwork", VolumeAccuracy())
```

### 3. Use in Tests

```python
@pytest.mark.benchmark
def test_earthwork_accuracy():
    result = detect_earthwork(pdf_path)
    metrics = registry.evaluate("earthwork", result, ground_truth)
    assert metrics["volume_accuracy"] > 0.80
```

## Continuous Monitoring

### Track Trends Over Time

```python
from langsmith import Client

client = Client()
runs = client.list_runs(
    project_name="estimai-takeoff",
    start_time=datetime.now() - timedelta(days=7)
)

# Analyze trends
for run in runs:
    print(f"{run.name}: {run.outputs.get('metrics', {})}")
```

### Compare Approaches

```python
# Get all vision runs
vision_runs = client.list_runs(
    project_name="estimai-takeoff",
    filter='metadata.detector_type = "vision"'
)

# Get all Apryse runs
apryse_runs = client.list_runs(
    project_name="estimai-takeoff",
    filter='metadata.detector_type = "apryse"'
)

# Compare accuracy
vision_accuracy = calculate_avg_accuracy(vision_runs)
apryse_accuracy = calculate_avg_accuracy(apryse_runs)

print(f"Vision: {vision_accuracy:.1%}")
print(f"Apryse: {apryse_accuracy:.1%}")
```

## Benefits

✅ **Extensible**: Add new detectors/metrics without changing existing code
✅ **Historical**: Track improvement as you tune prompts and models
✅ **Comparative**: A/B test different approaches
✅ **Debuggable**: See exactly what the LLM saw and returned
✅ **Cost-aware**: Track token usage and API costs
✅ **Production-ready**: Monitor live agent performance

## Next Steps

1. Set your LANGSMITH_API_KEY
2. Run benchmarks: `pytest -m benchmark`
3. View results at https://smith.langchain.com
4. Add new categories as you expand beyond pipes
