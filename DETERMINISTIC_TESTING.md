# 🎯 Deterministic Testing & Ground Truth Validation

## Overview

EstimAI now supports deterministic testing with ground truth validation to ensure reproducible and accurate takeoff results. This gives both developers and clients confidence in the system's reliability.

## 🔒 Deterministic Mode

### How It Works

When `ESTIMAI_SEED=42` is set, the system operates in deterministic mode:

1. **LLM Calls**: OpenAI API calls include a `seed` parameter for reproducible responses
2. **Temperature**: Already set to 0 for minimal creativity
3. **Sampling**: Consistent geometry sampling (no random jitter)
4. **Results**: Same PDF + same seed = same results every time

### Enabling Deterministic Mode

```bash
# Option 1: Set environment variable
export ESTIMAI_SEED=42
./backend/run_dev.sh

# Option 2: Set in .env file
echo "ESTIMAI_SEED=42" >> .env

# Option 3: One-time for testing
ESTIMAI_SEED=42 pytest backend/tests/test_ground_truth.py
```

## 📊 Golden Reference System

### Golden PDF

- **File**: `samples/280-utility-construction-plans.pdf` (3.8MB)
- **Description**: Full utility construction plans with sanitary, storm, and water networks
- **Why This PDF**: Real-world complexity with vector geometry and scale information

### Expected Metrics

The golden reference (`backend/tests/golden_reference.json`) defines expected results with tolerances:

```json
{
  "pipes_total": {
    "value": 6,
    "tolerance_pct": 0
  },
  "total_length_lf": {
    "value": 685.0,
    "tolerance_pct": 3.0
  },
  "depth_stats": {
    "avg_depth_ft": {
      "value": 6.8,
      "tolerance_pct": 5.0
    }
  },
  "trench_volume_cy": {
    "value": 456.7,
    "tolerance_pct": 5.0
  }
}
```

### Tolerance Rationale

| Metric | Tolerance | Reason |
|--------|-----------|--------|
| Pipe Count | 0% (exact) | Detection should be deterministic |
| Linear Feet | ±3% | Vector precision + sampling resolution |
| Depth | ±5% | Ground elevation sampling + profile interpolation |
| Trench Volume | ±5% | Geometry sampling resolution |

## 🧪 Running Ground Truth Tests

### One-Button Comparison

```bash
# Run the complete ground truth validation
./scripts/compare_ground_truth.sh
```

This script:
1. ✅ Sets `ESTIMAI_SEED=42` for reproducibility
2. ✅ Validates golden PDF exists
3. ✅ Runs agent on golden PDF
4. ✅ Compares all metrics against expected values
5. ✅ Reports pass/fail with detailed breakdown

### Manual Test Run

```bash
# Set deterministic mode
export ESTIMAI_SEED=42
export APR_USE_APRYSE=1

# Run ground truth tests only
PYTHONPATH=. pytest backend/tests/test_ground_truth.py -v -s -m ground_truth
```

### Expected Output

```
🎯 EstimAI Ground Truth Comparison
====================================

Environment:
  ESTIMAI_SEED=42 (deterministic mode)
  APR_USE_APRYSE=1

✅ Golden PDF found: samples/280-utility-construction-plans.pdf

Running ground truth comparison tests...

================================================================================
GROUND TRUTH COMPARISON RESULTS
================================================================================
✅ PASS: Total Pipes: 6 vs 6 (±0% = 0.00%)
✅ PASS: Total LF: 685.0 vs 685.0 (±3% = 0.00%)
✅ PASS: Sanitary Pipe Count: 2 vs 2 (±0% = 0.00%)
✅ PASS: Sanitary Total LF: 228.5 vs 228.5 (±3% = 0.00%)
✅ PASS: Storm Pipe Count: 2 vs 2 (±0% = 0.00%)
✅ PASS: Storm Total LF: 228.5 vs 228.5 (±3% = 0.00%)
✅ PASS: Water Pipe Count: 2 vs 2 (±0% = 0.00%)
✅ PASS: Water Total LF: 228.5 vs 228.5 (±3% = 0.00%)
✅ PASS: Average Depth: 6.8 vs 6.8 (±5% = 0.00%)
✅ PASS: Min Depth: 4.2 vs 4.2 (±5% = 0.00%)
✅ PASS: Max Depth: 12.1 vs 12.1 (±5% = 0.00%)
✅ PASS: Total Trench Volume (CY): 456.7 vs 456.7 (±5% = 0.00%)
✅ PASS: Depth Bucket D-0-5: 120 vs 120 (±3% = 0.00%)
✅ PASS: Depth Bucket D-5-8: 340 vs 340 (±3% = 0.00%)
✅ PASS: Depth Bucket D-8-12: 180 vs 180 (±3% = 0.00%)
✅ PASS: Depth Bucket D-12-PLUS: 45 vs 45 (±3% = 0.00%)
================================================================================
Results: 16/16 checks passed
================================================================================

✅ All ground truth checks passed!
```

## 📝 Updating Golden Reference

If you make intentional changes to the detection algorithm or depth calculations, update the golden reference:

### Step 1: Generate New Results

```bash
export ESTIMAI_SEED=42
curl -s -F "session_id=golden" -F "file=@samples/280-utility-construction-plans.pdf" \
  "http://localhost:8000/v1/agent/takeoff" > /tmp/new_golden.json
```

### Step 2: Extract Metrics

```bash
# View current results
cat /tmp/new_golden.json | jq '.summary'
cat /tmp/new_golden.json | jq '.proposed_review.payload.networks'
```

### Step 3: Update golden_reference.json

Manually update `backend/tests/golden_reference.json` with new expected values, documenting why they changed:

```json
{
  "notes": [
    "Updated 2025-10-06: Improved depth calculation accuracy",
    "Changed avg_depth_ft from 6.8 to 7.1 due to profile interpolation fix"
  ]
}
```

### Step 4: Verify

```bash
./scripts/compare_ground_truth.sh
```

## 🎭 Client Demonstration

### Showing Determinism to Clients

1. **First Run**:
   ```bash
   ESTIMAI_SEED=42 ./scripts/compare_ground_truth.sh
   ```
   *→ Show client: "16/16 checks passed"*

2. **Second Run** (same seed):
   ```bash
   ESTIMAI_SEED=42 ./scripts/compare_ground_truth.sh
   ```
   *→ Show client: "Identical results - system is deterministic"*

3. **Different Seed**:
   ```bash
   ESTIMAI_SEED=123 ./scripts/compare_ground_truth.sh
   ```
   *→ Show client: "Different seed = different results (but all within tolerance)"*

### Key Points for Clients

✅ **Deterministic**: Same input always produces same output with seed=42
✅ **Accurate**: Results within ±3% for LF, ±5% for volumes
✅ **Validated**: Every run is compared against ground truth
✅ **Transparent**: Full metrics breakdown shows what's being measured
✅ **Apryse + LLM Proven**: Pipeline transparency shows both are active

## 🔧 CI/CD Integration

Add to your GitHub Actions workflow:

```yaml
- name: Ground Truth Validation
  env:
    ESTIMAI_SEED: 42
    APR_USE_APRYSE: 1
  run: |
    source backend/.venv/bin/activate
    ./scripts/compare_ground_truth.sh
```

## 📊 Metrics Breakdown

### What We Measure

1. **Pipe Count** (exact match)
   - Total pipes detected
   - Per-network counts

2. **Linear Feet** (±3% tolerance)
   - Total LF across all networks
   - Per-network LF
   - Per-depth-bucket LF

3. **Depth Statistics** (±5% tolerance)
   - Average depth
   - Min/Max depth
   - Depth distribution

4. **Trench Volume** (±5% tolerance)
   - Total cubic yards
   - Accounts for geometry sampling

### Why Tolerances Exist

- **Vector Precision**: PDF coordinates are finite precision
- **Sampling Resolution**: Depth profiles sampled at intervals
- **LLM Variability**: Even with seed, minor floating-point differences
- **Geometry Complexity**: Curved pipes vs straight-line approximations

## 🐛 Troubleshooting

### Test Fails with "ESTIMAI_SEED must be set"

```bash
# Ensure seed is exported
export ESTIMAI_SEED=42
pytest backend/tests/test_ground_truth.py -m ground_truth
```

### Results Outside Tolerance

1. Check if PDF changed: `md5 samples/280-utility-construction-plans.pdf`
2. Check if algorithm updated: Review recent commits
3. Verify Apryse is enabled: `echo $APR_USE_APRYSE`
4. Check OpenAI API version: May affect seed behavior

### "Golden PDF not found"

```bash
# Verify file exists
ls -lh samples/280-utility-construction-plans.pdf

# If missing, check samples/ directory
ls samples/*.pdf
```

## 📚 Related Files

**Configuration:**
- `backend/app/core/config.py` - ESTIMAI_SEED setting
- `backend/app/core/llm.py` - Seed injection into OpenAI calls
- `.env` - Environment variable configuration

**Testing:**
- `backend/tests/golden_reference.json` - Expected metrics
- `backend/tests/test_ground_truth.py` - Comparison tests
- `scripts/compare_ground_truth.sh` - One-button validation
- `pytest.ini` - Test markers configuration

**Documentation:**
- `TRANSPARENCY_IMPLEMENTATION.md` - Pipeline transparency features
- This file - Deterministic testing guide

