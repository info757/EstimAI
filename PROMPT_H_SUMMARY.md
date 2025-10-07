# Prompt H — Demo Fallback Guarding

## Goal
Ensure demo fallback is hard-gated behind `ESTIMAI_USE_DEMO=1` and provide explicit warnings when 0 pipes are detected instead of silently injecting fake data.

## Implementation

### 1. Demo Fallback Guards (Already in Place)
The demo fallback was already properly guarded in all three detectors:

**Early Return (Primary Demo Mode)**:
```python
# Feature flag: Use demo data
if USE_DEMO:
    logger.info("ESTIMAI_USE_DEMO=1: Using demo data for storm network")
    nodes = _demo_detect_nodes(texts)
    pipes = _demo_trace_edges(nodes)
    return _attach_labels_and_qa(pipes, texts, "storm")
```

**Exception Fallback**:
```python
except ApryseUnavailable as e:
    if USE_DEMO:
        logger.warning(f"Apryse unavailable, using demo data (ESTIMAI_USE_DEMO=1): {e}")
        nodes = _demo_detect_nodes(texts)
        pipes = _demo_trace_edges(nodes)
        return _attach_labels_and_qa(pipes, texts, "storm")
    else:
        logger.error(f"❌ Apryse unavailable and ESTIMAI_USE_DEMO=0: {e}")
        return {"nodes": [], "pipes": [], "qa_flags": []}
```

### 2. Explicit Zero-Pipes Warnings (NEW)
Added clear warnings when classification results in 0 pipes:

```python
# Explicit warning if zero pipes after classification
if len(storm_detections) == 0:
    logger.warning(
        f"⚠️ 0 storm pipes after classification (from {len(patches)} candidates, {len(detections)} detections). "
        f"Reasons: {assignment_stats.get('unknown', 0)} unclassifiable. "
        f"Check: (1) confidence threshold (current: {MIN_CONFIDENCE}), "
        f"(2) discipline assignment (material/legend/layer hints), "
        f"(3) text/layer extraction quality."
    )
    if not USE_DEMO:
        logger.info("ℹ️ ESTIMAI_USE_DEMO=0, no fallback data will be injected.")
```

## Files Modified

1. `backend/app/services/detectors/storm.py` - Added zero-pipes warning
2. `backend/app/services/detectors/sanitary.py` - Added zero-pipes warning
3. `backend/app/services/detectors/water.py` - Added zero-pipes warning

## Behavior Modes

### Mode 1: ESTIMAI_USE_DEMO=0 (Production)
**Real Pipeline Success, 0 Pipes Detected**:
```
⚠️ 0 storm pipes after classification (from 2 candidates, 2 detections). 
Reasons: 2 unclassifiable. 
Check: (1) confidence threshold (current: 0.35), 
       (2) discipline assignment (material/legend/layer hints), 
       (3) text/layer extraction quality.

ℹ️ ESTIMAI_USE_DEMO=0, no fallback data will be injected.

Result: 0 pipes, explicit warning, no fake data
```

**Real Pipeline Success, N Pipes Detected**:
```
Storm network: 5 nodes, 3 pipes, 2 QA flags
📊 Storm assignment breakdown: llm=2, heuristic=1, rule_material=0, rule_legend=0, rule_layer=0, unknown=0

Result: 3 real pipes with full audit trail
```

**Real Pipeline Fails (Apryse Unavailable)**:
```
❌ Apryse unavailable and ESTIMAI_USE_DEMO=0: PDFNet initialization failed
Set APR_USE_APRYSE=1 or ESTIMAI_USE_DEMO=1 to proceed

Result: 0 pipes, clear error message
```

**Real Pipeline Fails (Exception)**:
```
❌ Real storm detection failed and ESTIMAI_USE_DEMO=0: division by zero
No vector candidates found - check PDF has vector geometry

Result: 0 pipes, error logged with stack trace
```

### Mode 2: ESTIMAI_USE_DEMO=1 (Development/Testing)
**Early Return (Bypass Real Pipeline)**:
```
ESTIMAI_USE_DEMO=1: Using demo data for storm network
ESTIMAI_USE_DEMO=1: Using demo data for sanitary network
ESTIMAI_USE_DEMO=1: Using demo data for water network

Result: 6 fake pipes per network (18 total)
```

**Exception Fallback**:
```
Apryse unavailable, using demo data (ESTIMAI_USE_DEMO=1): PDFNet not found
Real storm detection failed: division by zero
Falling back to demo data (ESTIMAI_USE_DEMO=1)

Result: 6 fake pipes per network as fallback
```

## Testing Results

### Test 1: ESTIMAI_USE_DEMO=0 (No Demo)
```bash
ESTIMAI_USE_DEMO=0 ./backend/run_dev.sh
```

**PDF**: `Neighborhood_Plan_Set_Annotated.pdf`

**Logs**:
```
📊 Storm assignment breakdown: llm=0, heuristic=0, rule_material=0, rule_legend=0, rule_layer=0, unknown=2
⚠️ 0 storm pipes after classification (from 2 candidates, 2 detections). 
   Reasons: 2 unclassifiable. 
   Check: (1) confidence threshold (current: 0.35), 
          (2) discipline assignment (material/legend/layer hints), 
          (3) text/layer extraction quality.
ℹ️ ESTIMAI_USE_DEMO=0, no fallback data will be injected.

📊 Sanitary assignment breakdown: llm=0, heuristic=0, rule_material=0, rule_legend=0, rule_layer=0, unknown=2
⚠️ 0 sanitary pipes after classification (from 2 candidates, 2 detections). 
   Reasons: 2 unclassifiable. 
   Check: (1) confidence threshold (current: 0.35), 
          (2) discipline assignment (material/legend/layer hints), 
          (3) text/layer extraction quality.
ℹ️ ESTIMAI_USE_DEMO=0, no fallback data will be injected.

📊 Water assignment breakdown: llm=0, heuristic=0, rule_material=0, rule_legend=0, rule_layer=0, unknown=2
⚠️ 0 water pipes after classification (from 2 candidates, 2 detections). 
   Reasons: 2 unclassifiable. 
   Check: (1) confidence threshold (current: 0.35), 
          (2) discipline assignment (material/legend/layer hints), 
          (3) text/layer extraction quality.
ℹ️ ESTIMAI_USE_DEMO=0, no fallback data will be injected.
```

**Result**: ✅ No silent fake data injection. Clear diagnostic warnings.

**API Response**:
```json
{
  "status": "completed",
  "pipes": 0,
  "networks": []
}
```

### Test 2: ESTIMAI_USE_DEMO=1 (With Demo)
```bash
ESTIMAI_USE_DEMO=1 ./backend/run_dev.sh
```

**Logs**:
```
ESTIMAI_USE_DEMO=1: Using demo data for storm network
ESTIMAI_USE_DEMO=1: Using demo data for sanitary network
ESTIMAI_USE_DEMO=1: Using demo data for water network
```

**Result**: ✅ Demo data used (bypasses real pipeline entirely)

## Warning Message Breakdown

The warning provides three specific areas to check:

1. **Confidence Threshold** (`current: 0.35`)
   - May be too high, filtering out valid but uncertain classifications
   - Adjust via `ESTIMAI_PIPE_MIN_CONF` env var

2. **Discipline Assignment** (material/legend/layer hints)
   - LLM returned `discipline=None`
   - Heuristics couldn't infer from material/text/layer
   - Rules couldn't match patterns
   - Likely cause: missing input data (material, nearby_text, layer all None/empty)

3. **Text/Layer Extraction Quality**
   - Root cause: text extraction incomplete (only 261 chars, title block)
   - Layer names always `None` (OCG extraction not working)
   - Text positions are fake placeholders
   - Fix upstream in PDFNet integration

## Benefits

### Before Prompt H:
- ❌ Demo fallback could silently inject fake data
- ❌ No clear indication when classification fails
- ❌ User might not realize they're seeing fake results

### After Prompt H:
- ✅ Demo only activates with `ESTIMAI_USE_DEMO=1`
- ✅ Explicit warning when 0 pipes detected
- ✅ Diagnostic info: candidates count, unclassifiable count, threshold
- ✅ Clear message: "no fallback data will be injected"
- ✅ Helps developers understand why classification failed

## Related Enhancements

Works in conjunction with:
- **Prompt A**: LLM classification logging (shows what LLM returned)
- **Prompt B**: Configurable threshold (mentioned in warning)
- **Prompt F**: Assignment breakdown (shows unclassifiable count)
- **Prompt E**: Debug endpoint (provides full diagnostic data)

## Acceptance Criteria

✅ **With demo off, you either see real results or a clear zero-pipes warning—no silent fake data**

- [x] ESTIMAI_USE_DEMO=0 + 0 pipes → Explicit warning logged
- [x] Warning includes diagnostic info (candidates, unclassifiable, threshold)
- [x] Warning mentions no fallback will be injected
- [x] No demo pipes silently added
- [x] ESTIMAI_USE_DEMO=1 → Demo data properly used and logged
- [x] All three detectors (storm, sanitary, water) have consistent behavior

## Conclusion

Prompt H successfully ensures transparency:
- No silent fake data injection
- Clear warnings when classification yields 0 results
- Diagnostic information to help fix the issue
- Demo mode explicitly controlled and logged

The system now provides clear feedback at every stage, making it easy to diagnose why pipes aren't being detected (in this case: text/layer extraction issues).

