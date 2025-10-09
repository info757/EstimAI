# Evaluation Guide: With vs. Without Ground Truth

## Overview

EstimAI supports two types of evaluation:

1. **Production Evaluation** - Assess quality WITHOUT knowing the "correct" answers
2. **Benchmark Evaluation** - Measure accuracy WITH known ground truth

## Quick Comparison

| | Production Evaluation | Benchmark Evaluation |
|---|---|---|
| **Ground Truth** | Not required | Required |
| **Use Case** | Real-world PDFs | Synthetic PDFs, regression tests |
| **What It Measures** | Consistency, faithfulness, completeness | Exact accuracy (count, length, elevation) |
| **Output** | Confidence score (0.0-1.0) + HITL flag | Accuracy percentage per metric |
| **Purpose** | Quality assurance in production | Development, tuning, testing |
| **API Endpoint** | `/v1/evaluate/production` | `/v1/evaluate/benchmark` |

## When to Use Each

### Use Production Evaluation When:
✅ Processing real customer PDFs  
✅ You don't have "correct" answers  
✅ You need to decide if human review is needed  
✅ You want to monitor quality in production  
✅ You want to flag suspicious extractions  

**Example:** Customer uploads a site plan. You run takeoff and get 47 pipes. Is that good? Production evaluation checks if the data makes sense (elevations flow downhill, depths are reasonable, materials are valid) and gives you a confidence score.

### Use Benchmark Evaluation When:
✅ Testing with synthetic PDFs  
✅ You have ground truth data  
✅ You're measuring improvement over time  
✅ You're doing regression testing  
✅ You're tuning the LLM or extraction logic  

**Example:** You generate a synthetic PDF with exactly 3 water pipes, each 100ft long, 8" diameter, PVC. You run takeoff and compare the results to what you know is correct.

## Production Evaluation Details

### What It Checks

#### 1. Internal Consistency
- Gravity pipes flow downhill (IE_in > IE_out)
- Depths are positive and reasonable (1-50 ft)
- Lengths are realistic (5-5000 ft)
- Materials are recognized types
- Diameters are typical (4-120 in)

#### 2. Completeness
- % of pipes with all core attributes
- % of pipes with elevation data
- % of pipes with material/diameter

#### 3. Faithfulness
- % of extracted values that appear in PDF text
- Detects hallucinations

#### 4. Overall Confidence
```
confidence = (quality_metrics * 0.6) + (consistency_checks * 0.4)
```

### Confidence Thresholds

- **≥ 0.85**: 🟢 High confidence - ready for use
- **0.70-0.85**: 🟡 Acceptable - spot check recommended
- **0.50-0.70**: 🟠 Low confidence - human review required
- **< 0.50**: 🔴 Very low - manual takeoff recommended

### API Usage

```bash
curl -X POST http://localhost:8000/v1/evaluate/production \
  -H "Content-Type: application/json" \
  -d '{
    "result": {...},
    "pdf_text": "...",
    "confidence_threshold": 0.70
  }'
```

**Response:**
```json
{
  "confidence": 0.82,
  "quality_scores": {
    "completeness": 0.85,
    "elevation_coverage": 0.75,
    "faithfulness": 0.90
  },
  "needs_hitl_review": false,
  "flags": [...],
  "recommendation": "High confidence - ready for use"
}
```

### Python Usage

```python
from backend.app.services.monitoring.production_eval import evaluate_production_run

evaluation = evaluate_production_run(
    result=agent_output,
    pdf_text=full_pdf_text,
    confidence_threshold=0.70
)

if evaluation["needs_hitl_review"]:
    # Route to human review queue
    queue_for_hitl(agent_output, evaluation)
else:
    # Proceed with automated workflow
    commit_to_database(agent_output)
```

## Benchmark Evaluation Details

### What It Measures

#### 1. Pipe Count Accuracy
```
accuracy = 1.0 - (error_rate / 0.5)
```
Perfect = 1.0, 50% error = 0.0

#### 2. Elevation Accuracy
```
accuracy = 1.0 - (error_ft / 5.0)
```
Within 1 ft = 100%, 5 ft = 0%

#### 3. Length Accuracy
```
accuracy = 1.0 - (error_pct / 0.20)
```
Within 5% = 100%, 20% = 0%

#### 4. Material Accuracy
Fuzzy matching on material names

### API Usage

```bash
curl -X POST http://localhost:8000/v1/evaluate/benchmark \
  -H "Content-Type: application/json" \
  -d '{
    "result": {...},
    "ground_truth": {...},
    "categories": ["pipes"]
  }'
```

**Response:**
```json
{
  "scores": {
    "pipes": {
      "count": 1.0,
      "elevation": 0.95,
      "length": 0.98,
      "material": 1.0
    }
  },
  "overall_accuracy": 0.98
}
```

### Python Usage

```python
from backend.app.services.monitoring.metrics_registry import get_metrics_registry

registry = get_metrics_registry()

scores = registry.evaluate("pipes", agent_output, ground_truth)

print(f"Count Accuracy: {scores['count']:.1%}")
print(f"Elevation Accuracy: {scores['elevation']:.1%}")
print(f"Length Accuracy: {scores['length']:.1%}")
print(f"Material Accuracy: {scores['material']:.1%}")
```

## Demo Scripts

### Production Evaluation Demo
```bash
./scripts/demo_production_eval.sh
```

This script:
1. Runs takeoff on a real PDF
2. Extracts PDF text for faithfulness checks
3. Evaluates quality without ground truth
4. Displays confidence scores and recommendations

### Benchmark Demo
```bash
./scripts/run_benchmarks.sh
```

This script:
1. Generates synthetic PDFs with known ground truth
2. Runs takeoff on each
3. Compares results to expected values
4. Reports accuracy metrics
5. Logs to LangSmith for tracking

## Testing

### Production Evaluation Tests
```bash
pytest backend/tests/test_production_eval.py -v
```

### Benchmark Tests
```bash
pytest backend/tests/test_agent_benchmarks.py -v -m benchmark
```

## Extending the System

### Adding a New Production Check

```python
# In backend/app/services/monitoring/production_eval.py

def check_consistency(result):
    # ... existing checks ...
    
    # Add your new check
    for i, pipe in enumerate(pipes):
        slope = calculate_slope(pipe)
        if slope < 0.001:  # Too flat
            checks.append((
                f"pipe_{i}_slope_flat",
                0.5,
                f"Pipe {i} has very flat slope: {slope:.4f}"
            ))
```

### Adding a New Benchmark Metric

```python
# In backend/app/services/monitoring/metrics_registry.py

class SlopeAccuracy(Metric):
    @property
    def name(self) -> str:
        return "slope_accuracy"
    
    def compute(self, predicted: Dict, ground_truth: Dict) -> float:
        # Compare predicted slopes to ground truth
        ...

# Register it
registry = get_metrics_registry()
registry.add_metric("pipes", SlopeAccuracy())
```

## Best Practices

### For Production
1. **Always extract PDF text** for faithfulness checks
2. **Set appropriate thresholds** based on your risk tolerance
3. **Route low-confidence to HITL** - don't auto-commit suspicious data
4. **Track confidence over time** - are you getting better?
5. **Investigate flags** - what patterns cause failures?

### For Benchmarking
1. **Use diverse synthetic PDFs** - simple, medium, complex
2. **Test edge cases** - very deep pipes, unusual materials, etc.
3. **Run in CI** - catch regressions early
4. **Track metrics over time** - use LangSmith datasets
5. **Compare approaches** - Vision vs. Apryse+LLM

## Workflow Integration

### Typical Production Flow

```
PDF Upload
    ↓
Run Takeoff Agent
    ↓
Extract PDF Text
    ↓
Production Evaluation
    ↓
    ├─ High Confidence (≥0.85)
    │   → Auto-commit to database
    │   → Send to customer
    │
    ├─ Medium Confidence (0.70-0.85)
    │   → Commit with warning
    │   → Flag for spot check
    │
    └─ Low Confidence (<0.70)
        → Queue for HITL review
        → Notify estimator
```

### Typical Development Flow

```
Code Change
    ↓
Run Benchmark Suite
    ↓
Compare to Baseline
    ↓
    ├─ Accuracy Improved
    │   → Update baseline
    │   → Merge PR
    │
    ├─ Accuracy Same
    │   → Merge PR
    │
    └─ Accuracy Degraded
        → Investigate regression
        → Fix or justify
```

## Related Documentation

- [Production Evaluation](./PRODUCTION_EVALUATION.md) - Deep dive on production eval
- [LLM Determinism](./LLM_DETERMINISM_COMPLETE.md) - Ensuring consistent outputs
- [Benchmarking](./BENCHMARKING.md) - Ground truth evaluation
- [Environment Setup](./ENVIRONMENT_SETUP.md) - LangSmith API keys, etc.

## FAQ

**Q: Can I use both evaluations on the same PDF?**  
A: Yes! Use benchmark evaluation during development with synthetic PDFs, then use production evaluation in production on real PDFs.

**Q: What if I have partial ground truth?**  
A: Use production evaluation and manually review the flags. You can also create a hybrid metric that uses ground truth where available and consistency checks elsewhere.

**Q: How do I improve my confidence scores?**  
A: Focus on the failing checks. If faithfulness is low, improve text extraction. If consistency is low, add validation rules or improve the LLM prompt.

**Q: Can I customize the confidence threshold?**  
A: Yes! Pass `confidence_threshold` in the API request. Adjust based on your risk tolerance and HITL capacity.

**Q: How do I track evaluation metrics over time?**  
A: Use LangSmith! Both production and benchmark evaluations can log to LangSmith datasets for historical tracking and comparison.

