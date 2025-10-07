# LLM Determinism Implementation

## Overview

EstimAI implements comprehensive determinism controls to ensure reproducible pipe classification results from the LLM.

## 1. Model Parameters (Fully Deterministic)

All LLM calls use these fixed parameters:

```python
{
    "model": "gpt-4o-mini",
    "temperature": 0,           # No randomness in token selection
    "top_p": 1,                 # Consider all tokens
    "frequency_penalty": 0,     # No frequency-based adjustment
    "presence_penalty": 0,      # No presence-based adjustment
    "max_tokens": 4000,         # Generous limit to prevent truncation
    "seed": 42,                 # Fixed seed (when ESTIMAI_SEED=42)
    "response_format": {"type": "json_object"}  # Structured output
}
```

**Location**: `backend/app/core/llm.py`

## 2. Input Canonicalization (Content Hash)

Before sending data to the LLM, we canonicalize the input to ensure identical inputs produce identical hashes:

### Float Quantization
- Round all floats to 3 decimals
- Convert `NaN` and `Infinity` to `null`
- Never use scientific notation

### Stable IDs
- Generate polyline IDs from content hash (geometry + layer)
- Format: `poly_{sha1_hash[:12]}`
- Avoids random UUIDs

### Stable Sorting
- Sort candidates by ID before sending
- Sort nearby_text arrays alphabetically

### Explicit Nulls
- Use `null` for missing values (not `undefined`)
- Always include all fields in schema

### Content Hashing
- Serialize with sorted keys: `json.dumps(context, sort_keys=True, separators=(',', ':'))`
- Create SHA256 hash of canonical JSON
- Log hash with every LLM call: `🔑 Content hash: abc123def456 (15 candidates)`

**Location**: `backend/app/services/ai/pipe_classifier.py` → `_build_context()`

## 3. Automatic Batching

To prevent timeouts and ensure reliability:

- **Batch size**: 15 candidates per LLM call
- **Strategy**: Split large datasets into batches automatically
- **Benefit**: Smaller payloads = faster processing, fewer timeouts

**Location**: `backend/app/services/ai/pipe_classifier.py` → `classify()`

## 4. Logging for Reproducibility

Every LLM call logs:

1. **Determinism config**:
   ```
   🎲 Deterministic mode: model=gpt-4o-mini, seed=42, temp=0, top_p=1, max_tokens=4000
   ```

2. **Content hash**:
   ```
   🔑 Content hash: abc123def456 (15 candidates)
   ```

3. **Batch progress**:
   ```
   Processing batch 2/5 (15 patches)
   Batch 2/5 complete: 12 detections
   ```

4. **Response confirmation**:
   ```
   ✅ LLM response received for hash abc123def456
   ```

## 5. Usage

### Enable Determinism

Set the seed in your environment:

```bash
export ESTIMAI_SEED=42
```

Or in `.env`:
```
ESTIMAI_SEED=42
```

### Run the Backend

```bash
cd /Users/williamholt/estimai
ESTIMAI_SEED=42 ./backend/run_dev.sh
```

### Verify Determinism

1. Upload the same PDF twice
2. Check logs for identical content hashes
3. Verify identical pipe detection results

## 6. Testing Ground Truth

For ground truth testing:

```bash
ESTIMAI_SEED=42 pytest backend/tests/ -m ground_truth
```

This ensures:
- Same input → same hash → same LLM result
- Tolerance: ±2-3% for LF (linear feet)
- Tolerance: ±5% for CY (cubic yards, due to sampling)

## 7. Local Cache (Reproducibility Guarantee)

EstimAI implements a local LLM response cache to ensure **100% reproducibility**, independent of OpenAI's infrastructure.

### Cache Key

Responses are cached by:
```
(model_name, prompt_version, schema_version, content_hash)
```

Example: `gpt-4o-mini_v1.0_v1.0_abc123def456.json`

### Cache Location

```
backend/artifacts/llm_cache/{cache_key}.json
```

Each cache file contains:
- **Request context**: Canonicalized input sent to LLM
- **Response**: Complete LLM output
- **Metadata**: Token counts, model fingerprint, timestamp

### Cache Management

**View stats**:
```bash
curl http://localhost:8000/v1/cache/stats
```

**Clear cache**:
```bash
curl -X DELETE http://localhost:8000/v1/cache/clear
```

**Get versions**:
```bash
curl http://localhost:8000/v1/cache/versions
```

### Cache Behavior

1. **Cache hit**: Reuse local response (instant, free, deterministic)
2. **Cache miss**: Call OpenAI, cache response for future use

### Why This Matters

- **Reproducibility**: Same input → same output, always
- **Offline replay**: Re-run analysis without API calls
- **Cost savings**: Don't pay for duplicate requests
- **Audit trail**: Full history of LLM interactions

## 8. Validation & Retry Logic

EstimAI implements automatic validation and retry for improbable results.

### Sanity Checks

Before accepting LLM results, the system checks for:

1. **Zero detections with good context**:
   - Candidates > 0
   - Legend present OR labels > 5
   - LLM returns 0 detections
   - → **Trigger retry**

2. **Low classification rate**:
   - Candidates > 10
   - Classification rate < 5%
   - Legend present OR labels > 10
   - → **Trigger retry**

### Retry Behavior

**On validation failure**:
1. Log warning: `🔄 Retry attempt 1/1: IMPROBABLE_ZERO`
2. Call LLM again with **same content hash** (deterministic)
3. If retry produces more detections → use retry result
4. If retry still fails → flag for Human-In-The-Loop (HITL)

**QA Flags**:
- `IMPROBABLE_ZERO`: Zero detections despite clear hints
- `LOW_CLASSIFICATION_RATE`: Too few detections for context quality

### Run-time Invariants Logging

Every classification logs:

```
📊 Run-time invariants:
  candidate_count=42
  label_count=15
  legend_present=True
  model=gpt-4o-mini
  temperature=0
  seed=42
  token_budget_used=1250
  content_hash=abc123def456
  detection_count=38
```

This provides full traceability for debugging and auditing.

### Why Retry Works

With deterministic mode (`ESTIMAI_SEED=42`), the retry uses:
- **Same input** (canonicalized)
- **Same seed** (42)
- **Same model parameters** (temp=0, top_p=1)

If the first call had a transient issue (e.g., API hiccup, truncation), the retry often succeeds.

If both attempts fail identically, it's likely a real issue (poor PDF quality, missing data) and should be flagged for HITL.

## 9. Troubleshooting

### Issue: Different results with same PDF

**Possible causes**:
1. `ESTIMAI_SEED` not set → Add to environment
2. PDF extraction order is random → Check if polyline IDs are stable
3. Float precision issues → Verify quantization is working

**Debug steps**:
1. Check logs for content hash
2. Compare hashes between runs
3. If hashes differ, canonicalization has a bug
4. If hashes match but results differ, OpenAI may have updated the model

### Issue: Timeouts with large PDFs

**Solution**: Batching is automatic (15 candidates/batch)

**If still timing out**:
1. Reduce batch size in `pipe_classifier.py`
2. Increase timeout in `_call_llm` (currently 120s)

## 8. Future Improvements

- [ ] Cache LLM responses by content hash (avoid re-processing identical inputs)
- [ ] Wire `legend_ontology` and `scale_info` into context
- [ ] Add prompt versioning (hash prompt + context together)
- [ ] Store content hashes in database for audit trail

