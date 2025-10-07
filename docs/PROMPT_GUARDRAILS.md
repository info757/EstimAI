# Prompt Guardrails Against "Collapse to Unknown"

## Problem

LLMs can sometimes exhibit a "collapse to unknown" behavior where they return mostly null/unknown classifications, even when clear evidence (layer names, text labels, legend) is present.

**Common causes**:
1. **Global distribution assumption**: Model tries to match expected class distribution
2. **Over-cautious**: Model defaults to "unknown" when uncertain
3. **Token bloat**: Verbose reasons exceed token budget → truncation → loss of classifications
4. **Evidence amnesia**: Model doesn't explicitly cite evidence it used

## Solution

We've implemented **5 prompt guardrails** to prevent this collapse:

### 1. Independent Classification Directive

**Added to prompt**:
```
Classify each polyline INDEPENDENTLY. 
Do not adjust outputs to match an assumed global distribution.
```

**Why this works**:
- Prevents model from "balancing" storm/sanitary/water counts
- Each polyline is judged on its own evidence
- No artificial quota enforcement

### 2. Evidence-First Rule

**Added to prompt**:
```
If you cite at least one label or legend clue for a polyline, 
you MUST choose a type (storm/sanitary/water); 
only use null/unknown when there is truly no evidence.
```

**Why this works**:
- Forces model to commit when evidence exists
- "Unknown" reserved for genuinely ambiguous cases
- Explicit commitment → higher classification rate

### 3. Reason Length Cap

**Added to prompt**:
```
Keep "reason" concise (≤25 words). 
Cite specific evidence (layer name, nearby text).
```

**Implementation**:
```python
# In _parse_llm_response()
reason_words = reason.split()
if len(reason_words) > 25:
    reason = " ".join(reason_words[:25]) + "..."
```

**Why this works**:
- Prevents token bloat (verbose reasons)
- Reduces truncation risk
- Forces model to prioritize key evidence
- More tokens available for actual classifications

### 4. Evidence References (Schema Enforcement)

**Added to schema**:
```json
{
  "evidence_refs": {
    "type": "array",
    "items": {"type": "string"},
    "description": "List of cited labels/text (required if discipline != null)"
  }
}
```

**Validation**:
```python
if discipline and not evidence_refs:
    logger.warning(
        f"⚠️ Contract violation: {poly_id} has discipline={discipline} "
        f"but evidence_refs is empty"
    )
```

**Why this works**:
- Model must explicitly list evidence used
- Creates accountability trail
- Harder to classify without evidence
- Easier to debug misclassifications

### 5. Evidence-First Style (Maintained)

**Prompt structure**:
1. Layer hints (strong evidence)
2. Text annotations (definitive evidence)
3. Material patterns (contextual evidence)
4. Then classification rules

**Why this works**:
- Evidence comes before conclusions
- Model sees hints before making decisions
- Primes model to look for evidence

## Contract Changes

### Before (v1.0)

```json
{
  "polyline_id": "vec_0_42",
  "discipline": "storm",
  "material": "pvc",
  "dia_in": 12.0,
  "confidence": 0.9,
  "reason": "The polyline is located on a layer named STORM SEWER which strongly indicates this is a storm drain system. Additionally, there is nearby text that reads '12 inch PVC pipe' which provides definitive evidence of both the diameter and material."
}
```

**Issues**:
- Reason is 44 words (token bloat)
- No explicit evidence citations
- Verbose prose

### After (v1.1)

```json
{
  "polyline_id": "vec_0_42",
  "discipline": "storm",
  "material": "pvc",
  "dia_in": 12.0,
  "confidence": 0.9,
  "reason": "Layer STORM SEWER, text 12\" PVC",
  "evidence_refs": ["12\" PVC", "STORM SEWER"]
}
```

**Improvements**:
- Reason is 6 words (concise)
- Explicit evidence citations
- More tokens for classifications

## Validation

The system validates outputs in `_parse_llm_response()`:

```python
def _parse_llm_response(llm_result, original_patches):
    for item in llm_result:
        discipline = item.get("discipline")
        evidence_refs = item.get("evidence_refs", [])
        reason = item.get("reason", "")
        
        # Guardrail 1: Truncate reason
        if len(reason.split()) > 25:
            reason = " ".join(reason.split()[:25]) + "..."
        
        # Guardrail 2: Warn on missing evidence
        if discipline and not evidence_refs:
            logger.warning(f"Contract violation: discipline={discipline} but no evidence_refs")
```

## Expected Improvements

### Metrics

**Before guardrails**:
- Classification rate: 30-60% (highly variable)
- Unknown rate: 40-70%
- Reason avg length: 30-50 words
- Evidence citations: 0 (not captured)

**After guardrails**:
- Classification rate: 70-90% (when evidence present)
- Unknown rate: 10-30% (truly ambiguous only)
- Reason avg length: 8-15 words
- Evidence citations: 1-3 per classification

### Behavioral Changes

1. **Fewer "unknown" classifications**: Model commits when evidence exists
2. **More consistent**: Independent classification → less variation
3. **Better token efficiency**: Shorter reasons → more classifications fit in budget
4. **Easier debugging**: Evidence refs show exactly what model saw

## Testing

### Test 1: Legend Present, Clear Labels

**Input**:
- 50 polylines
- Legend with "SD = Storm Drain", "SS = Sanitary Sewer"
- 40+ nearby labels like "8\" PVC SD", "12\" CONC SS"

**Expected** (v1.1):
- Classification rate: >80%
- All classifications have evidence_refs
- Reasons <25 words

**Previous** (v1.0):
- Classification rate: ~50%
- Many "unknown" despite clear labels
- Verbose reasons

### Test 2: No Legend, Mixed Labels

**Input**:
- 30 polylines
- No legend
- Some labels like "STORM SEWER", others unlabeled

**Expected** (v1.1):
- Labeled pipes: ~80% classified
- Unlabeled pipes: ~20% classified (inferred from layer)
- Evidence refs present for all classified
- Unknown only for pipes with no layer/text hints

### Test 3: Retry on Improbable Zero

**Input**:
- 40 polylines
- Legend present
- 20+ labels
- LLM returns 0 classifications (collapse)

**Expected** (v1.1):
1. Validation triggers: "IMPROBABLE_ZERO"
2. Automatic retry
3. Retry with same input (deterministic)
4. Likely produces >0 classifications (guardrails active)
5. If still 0 → QA_FLAG for HITL

## Monitoring

Watch for these log patterns:

### Good (Working as intended)

```
🔑 Content hash: abc123 (42 candidates)
✅ LLM response received
📊 Run-time invariants: detection_count=38
🔍 Validation check: Candidates: 42, Detections: 38
✅ Validation passed
```

### Warning (Contract violations)

```
⚠️ Contract violation: P123abc has discipline=storm but evidence_refs is empty
```
**Action**: Investigate why model didn't cite evidence

### Retry (Improbable result)

```
⚠️ IMPROBABLE_ZERO: 42 candidates, legend=yes, labels=15, but 0 detections
🔄 Retry attempt 1/1: IMPROBABLE_ZERO
🔄 Retry result: 35 detections
✅ Retry improved: 0 → 35
```
**Action**: Normal - retry fixed transient issue

### Failure (Persistent collapse)

```
⚠️ IMPROBABLE_ZERO: 42 candidates, legend=yes, labels=15, but 0 detections
🔄 Retry attempt 1/1: IMPROBABLE_ZERO
🔄 Retry result: 0 detections
⚠️ QA_FLAG: IMPROBABLE_ZERO (persists after retry)
```
**Action**: Flag for HITL - likely poor PDF quality or missing data

## Versioning

**Prompt version**: `v1.1` (bumped from v1.0)
**Schema version**: `v1.1` (bumped from v1.0)

**Why version bump**:
- Prompt changes invalidate old cache entries
- New schema adds `evidence_refs` field
- Ensures clean cache separation

**Cache behavior**:
- v1.0 cache: `gpt-4o-mini_v1.0_v1.0_{hash}.json`
- v1.1 cache: `gpt-4o-mini_v1.1_v1.1_{hash}.json`
- Different versions = different cache keys = no collision

## Rollback

If guardrails cause issues, rollback by:

1. **Revert prompt version**:
   ```python
   # In llm_cache.py
   PROMPT_VERSION = "v1.0"
   SCHEMA_VERSION = "v1.0"
   ```

2. **Revert prompt text**:
   ```python
   # In pipe_classifier.py, remove CRITICAL GUARDRAILS section
   ```

3. **Revert schema**:
   ```python
   # Remove evidence_refs from schema
   # Remove reason length constraint
   ```

4. **Clear new cache**:
   ```bash
   curl -X DELETE http://localhost:8000/v1/cache/clear
   ```

## Conclusion

These 5 guardrails work together to prevent "collapse to unknown":

1. **Independent classification** → No distribution balancing
2. **Evidence-first rule** → Commit when evidence exists
3. **Reason length cap** → Prevent token bloat
4. **Evidence references** → Explicit citations
5. **Validation & retry** → Catch and fix improbable results

The result: **Consistent, high-quality classifications with full traceability**.

