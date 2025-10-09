# Production Evaluation (Without Ground Truth)

## Overview

Production evaluation assesses takeoff quality **without** knowing the "correct" answers. This is essential for real-world PDFs where we don't have ground truth data.

## How It Works

### 1. Internal Consistency Checks

Validates that extracted data makes physical sense:

- **Elevation Flow**: Gravity pipes (storm/sanitary) should flow downhill
- **Depth Reasonableness**: Depths should be positive and within typical ranges (1-50 ft)
- **Length Reasonableness**: Pipe lengths should be realistic (5-5000 ft)
- **Material Validity**: Materials should be recognized types (PVC, DI, RCP, etc.)
- **Diameter Reasonableness**: Diameters should be typical (4-120 inches)
- **Network Consistency**: Disciplines should be consistent

### 2. Quality Metrics

Measures completeness and coverage:

- **Completeness**: % of pipes with all core attributes (material, diameter, length, discipline)
- **Elevation Coverage**: % of pipes with elevation data
- **Material Coverage**: % of pipes with material specified
- **Diameter Coverage**: % of pipes with diameter specified
- **Faithfulness**: % of extracted values that actually appear in the PDF text

### 3. Overall Confidence Score

Combines quality and consistency into a single score (0.0 to 1.0):

```
confidence = (quality_metrics * 0.6) + (consistency_checks * 0.4)
```

### 4. HITL Routing

Automatically flags low-confidence extractions for human review:

- **≥ 0.85**: High confidence - ready for use
- **0.70-0.85**: Acceptable - spot check recommended
- **0.50-0.70**: Low confidence - human review required
- **< 0.50**: Very low - manual takeoff recommended

## Usage

### API Endpoint

```bash
POST /v1/evaluate/production
```

**Request:**
```json
{
  "result": {
    "pipes": [...],
    "summary": {...}
  },
  "pdf_text": "Full text from PDF...",
  "confidence_threshold": 0.70
}
```

**Response:**
```json
{
  "confidence": 0.82,
  "quality_scores": {
    "completeness": 0.85,
    "elevation_coverage": 0.75,
    "faithfulness": 0.90,
    "material_coverage": 1.0,
    "diameter_coverage": 1.0
  },
  "needs_hitl_review": false,
  "flags": [
    {
      "check": "pipe_3_depth_shallow",
      "score": 0.5,
      "message": "Pipe 3 is very shallow: 0.8ft (<1ft)"
    }
  ],
  "recommendation": "High confidence - ready for use",
  "threshold": 0.70
}
```

### Python API

```python
from backend.app.services.monitoring.production_eval import evaluate_production_run

# Run evaluation
evaluation = evaluate_production_run(
    result=agent_output,
    pdf_text=full_pdf_text,
    confidence_threshold=0.70
)

# Check if human review needed
if evaluation["needs_hitl_review"]:
    print(f"⚠️ Low confidence: {evaluation['confidence']:.1%}")
    print(f"Flags: {len(evaluation['flags'])}")
    # Route to HITL queue
else:
    print(f"✅ High confidence: {evaluation['confidence']:.1%}")
    # Proceed with automated workflow
```

### Demo Script

```bash
./scripts/demo_production_eval.sh
```

This script:
1. Runs takeoff on a real PDF
2. Extracts PDF text for faithfulness checks
3. Evaluates quality without ground truth
4. Displays confidence scores and recommendations

## Metrics Registry Integration

Production quality is registered as a metric category:

```python
from backend.app.services.monitoring.metrics_registry import get_metrics_registry

registry = get_metrics_registry()

# Evaluate production quality
scores = registry.evaluate("production", agent_output, {"pdf_text": pdf_text})

print(f"Production Quality: {scores['production_quality']:.1%}")
```

## Testing

Run production evaluation tests:

```bash
pytest backend/tests/test_production_eval.py -v
```

Tests cover:
- Consistency checks (pass/fail scenarios)
- Quality assessment
- Overall confidence calculation
- HITL routing logic
- Metrics registry integration

## Comparison: Production vs. Benchmark

| Aspect | Production Evaluation | Benchmark Evaluation |
|--------|----------------------|---------------------|
| **Ground Truth** | Not required | Required |
| **Use Case** | Real-world PDFs | Synthetic PDFs, regression tests |
| **Metrics** | Consistency, faithfulness, completeness | Exact accuracy (count, length, elevation) |
| **Output** | Confidence score + HITL flag | Accuracy percentage |
| **Purpose** | Quality assurance in production | Development, tuning, testing |

## When to Use Each

### Use Production Evaluation When:
- Processing real customer PDFs
- You don't have "correct" answers
- You need to decide if human review is needed
- You want to monitor quality in production

### Use Benchmark Evaluation When:
- Testing with synthetic PDFs
- You have ground truth data
- You're measuring improvement over time
- You're doing regression testing

## Future Enhancements

1. **LLM-Based Faithfulness**: Use GPT-4 to verify that extracted values are supported by PDF content
2. **Cross-Reference Checks**: Verify that totals match sums, elevations are consistent across sheets
3. **Historical Comparison**: Flag extractions that differ significantly from similar past projects
4. **Confidence Calibration**: Track actual error rates vs. predicted confidence to improve thresholds
5. **Domain-Specific Rules**: Add construction-specific heuristics (e.g., typical pipe slopes, cover depths)

## Related Documentation

- [LLM Determinism](./LLM_DETERMINISM_COMPLETE.md) - How we ensure consistent LLM outputs
- [Benchmarking](./BENCHMARKING.md) - Evaluation with ground truth
- [HITL Workflow](./UNKNOWN_HANDLING.md) - How low-confidence items are routed to humans

