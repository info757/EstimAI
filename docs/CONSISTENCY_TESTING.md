# LLM Consistency Testing

## Overview

The consistency test harness ensures that our LLM pipeline produces **deterministic, byte-identical outputs** when given the same input.

**Test**: Run the exact same canonicalized input 10× and assert identical output bytes.

**If this fails** with `temperature=0` and `seed=42`, something is non-deterministic:
- Upstream ordering issue (arrays not sorted)
- Unstable IDs (random UUIDs instead of content hashes)
- Float quantization issue (NaN, Infinity, or precision drift)
- Context length variation (truncation, encoding issues)

## Test Suite

### 1. Core Consistency Test

**File**: `backend/tests/test_llm_consistency.py::test_llm_output_consistency_10x`

**What it does**:
```python
# Create input
patches = [...]

# Run 10 times
outputs = [classifier.classify(patches) for _ in range(10)]

# Assert all outputs are byte-identical
assert all(
    json.dumps(o, sort_keys=True) == json.dumps(outputs[0], sort_keys=True) 
    for o in outputs
)
```

**Expected**: All 10 runs produce identical JSON (byte-for-byte).

**On failure**:
1. Check if `ESTIMAI_SEED=42` is set
2. Check if content hashes are stable (logged)
3. Check if cache is being used (after first call)
4. Inspect diffs between outputs

### 2. Canonicalization Idempotency

**File**: `backend/tests/test_llm_consistency.py::test_canonicalization_idempotent`

**What it does**:
```python
bundle = {...}

canonical_1 = canonicalize_bundle(bundle)
canonical_2 = canonicalize_bundle(canonical_1)

assert content_hash(canonical_1) == content_hash(canonical_2)
```

**Expected**: `canonicalize(canonicalize(x)) == canonicalize(x)`

**On failure**: Canonicalization function has side effects or non-deterministic behavior.

### 3. Content Hash Stability

**File**: `backend/tests/test_llm_consistency.py::test_content_hash_stable`

**What it does**:
```python
payload = {...}

hashes = [content_hash(payload) for _ in range(10)]

assert len(set(hashes)) == 1
```

**Expected**: Same payload → same hash (every time).

**On failure**: Hash function is non-deterministic (check JSON serialization).

### 4. Cache Hit Behavior

**File**: `backend/tests/test_llm_consistency.py::test_cache_hit_behavior`

**What it does**:
```python
result_1 = classifier.classify(patches)  # May hit cache or call LLM
result_2 = classifier.classify(patches)  # Should hit cache

assert json_equivalent(result_1, result_2)
```

**Expected**: Cache hits return identical results (no re-computation).

**On failure**: Cache is corrupted or not being used.

### 5. Batching Consistency

**File**: `backend/tests/test_llm_consistency.py::test_consistency_across_batches`

**What it does**:
```python
# All at once
result_full = classifier.classify(patches_20)

# In batches
result_batch = classifier.classify(patches[:10]) + classifier.classify(patches[10:])

assert sorted(result_full) == sorted(result_batch)
```

**Expected**: Batching doesn't affect results (order may differ).

**On failure**: Batching logic has side effects or state leakage.

## Running Tests

### Locally

```bash
# All consistency tests
ESTIMAI_SEED=42 pytest -v -m consistency

# Single test
ESTIMAI_SEED=42 pytest -v backend/tests/test_llm_consistency.py::test_llm_output_consistency_10x

# With output
ESTIMAI_SEED=42 pytest -v -s -m consistency
```

### In CI (GitHub Actions)

The consistency test runs automatically on every PR:

```yaml
consistency:
  runs-on: ubuntu-latest
  env:
    ESTIMAI_SEED: "42"
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  steps:
    - name: Consistency test (10x runs)
      run: pytest -q backend/tests/test_llm_consistency.py -m consistency
```

**Note**: Requires `OPENAI_API_KEY` secret in GitHub repo settings.

## Interpreting Results

### ✅ Success Output

```
backend/tests/test_llm_consistency.py::test_llm_output_consistency_10x 
Run 1/10: 3 detections, hash=abc123def456
Run 2/10: 3 detections, hash=abc123def456
...
Run 10/10: 3 detections, hash=abc123def456
✅ Content hash stable: abc123def456
✅ All 10 outputs are byte-identical (1234 bytes)
✅ Consistency test PASSED
PASSED                                         [100%]

5 passed in 12.3s
```

### ❌ Failure: Non-Deterministic Output

```
backend/tests/test_llm_consistency.py::test_llm_output_consistency_10x 
Run 1/10: 3 detections, hash=abc123def456
Run 2/10: 3 detections, hash=abc123def456
Run 3/10: 2 detections, hash=abc123def456  # ← Different count!
...
FAILED - AssertionError: Output 3 differs from output 1!
  Diff length: 234 bytes
```

**Diagnosis**:
1. Content hash is stable → canonicalization OK
2. Output differs → LLM is non-deterministic

**Possible causes**:
- Seed not being used (`ESTIMAI_SEED` not set)
- OpenAI model update (check `system_fingerprint`)
- Cache corruption (clear and retry)

### ❌ Failure: Unstable Content Hash

```
backend/tests/test_llm_consistency.py::test_llm_output_consistency_10x 
Run 1/10: 3 detections, hash=abc123def456
Run 2/10: 3 detections, hash=xyz789abc123  # ← Different hash!
...
FAILED - AssertionError: Content hashes differ across runs!
  Hashes: {'abc123def456', 'xyz789abc123', 'def456abc789'}
```

**Diagnosis**: Canonicalization is non-deterministic.

**Possible causes**:
- Array sorting not working (check nearby_text, labels)
- Float quantization not working (check NaN, Infinity handling)
- Unstable IDs (check polyline_id generation)

## Debugging Non-Determinism

### Step 1: Check Seed

```bash
ESTIMAI_SEED=42 pytest -v -s backend/tests/test_llm_consistency.py::test_llm_output_consistency_10x

# Look for in logs:
# 🎲 Deterministic mode: model=gpt-4o-mini, seed=42, temp=0, top_p=1, max_tokens=4000
```

If seed is NOT logged → check environment variable setup.

### Step 2: Check Content Hash

```python
# In test output, look for:
# Run 1/10: 3 detections, hash=abc123def456
# Run 2/10: 3 detections, hash=abc123def456
```

If hashes differ → canonicalization issue.

If hashes match but outputs differ → LLM issue (despite seed).

### Step 3: Check Cache

```bash
# View cache stats
curl http://localhost:8000/v1/cache/stats

# Clear cache and retry
curl -X DELETE http://localhost:8000/v1/cache/clear
ESTIMAI_SEED=42 pytest -v backend/tests/test_llm_consistency.py::test_llm_output_consistency_10x
```

If clearing cache fixes it → cache corruption (investigate).

### Step 4: Compare Outputs

```python
# Add to test:
import difflib

diff = difflib.unified_diff(
    json.dumps(outputs[0], indent=2).splitlines(),
    json.dumps(outputs[2], indent=2).splitlines(),
    lineterm=''
)
print('\n'.join(diff))
```

Look for:
- Different confidence values → Check quantization
- Different IDs → Check stable_poly_id
- Different order → Check sorting
- Different materials/disciplines → Real non-determinism

## Maintenance

### When to Update Tests

1. **Prompt changes**: If you change the prompt, tests may fail (expected). Review and accept new baseline.

2. **Schema changes**: If you add/remove fields, update assertions.

3. **Version bump**: If you bump prompt/schema version, cache invalidates → first run may be slow.

### Updating Baseline

If you intentionally change the model behavior:

1. Clear cache: `curl -X DELETE http://localhost:8000/v1/cache/clear`
2. Run test once to generate new baseline
3. Run test again to verify consistency with new baseline

### Performance

**Expected runtime**:
- First run: ~10-30 seconds (10 LLM calls or 1 call + 9 cache hits)
- Subsequent runs: ~1-2 seconds (all cache hits)

**If slower**:
- Check if cache is working
- Check network latency to OpenAI
- Consider using smaller test inputs

## CI Integration

The consistency test is part of the CI pipeline:

```
CI Pipeline:
├── boot (must pass)
├── smoke (should pass)
├── consistency (must pass)  ← New!
├── lint (should pass)
└── type check (should pass)
```

**On PR**: Consistency test runs automatically.

**On failure**: PR is blocked until fixed.

## Best Practices

1. **Always set ESTIMAI_SEED=42** for consistency tests
2. **Run locally before pushing** to catch issues early
3. **Clear cache if suspicious** - cache corruption is rare but possible
4. **Check logs for content hashes** - they should be stable
5. **Don't skip consistency tests** - they catch subtle bugs

## Troubleshooting

### Issue: Tests pass locally, fail in CI

**Possible causes**:
- Different Python version (check CI uses 3.11)
- Different dependencies (check requirements.txt)
- Missing OPENAI_API_KEY in CI secrets

**Fix**: Match local environment to CI environment.

### Issue: Tests are flaky (sometimes pass, sometimes fail)

**Possible causes**:
- Network issues (OpenAI API timeout)
- Concurrency issues (parallel test runs)
- Cache race conditions

**Fix**: Run with `-x` flag to stop on first failure, inspect logs.

### Issue: Tests are slow

**Possible causes**:
- Cache not working (re-computing every time)
- Large test inputs (too many patches)
- API rate limiting

**Fix**: Verify cache is working, reduce test input size.

## Conclusion

The consistency test harness provides **high-confidence verification** that our LLM pipeline is truly deterministic. If these tests pass, you can trust that:

1. Same input → same hash → same cache key
2. Same cache key → same output (from cache or LLM)
3. Canonicalization is stable and idempotent
4. Batching doesn't affect results

**Golden rule**: If consistency tests fail, **do not merge**. Non-determinism is a critical bug.

