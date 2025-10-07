# Unknown/Unclassified Pipe Handling

## Problem

A common "gotcha" in classification pipelines is **silent filtering** downstream:

```python
# BAD: Silently drops unknowns
if pipe.discipline in ["storm", "sanitary", "water"]:
    include_in_output(pipe)
# Unknown pipes just disappear - user sees "0 found"
```

**Symptoms**:
- LLM classifies 50 pipes
- UI shows 0 pipes
- No error message
- User thinks detection failed

**Root cause**: Filter drops `discipline=null` or `discipline=unknown` without logging or routing to HITL.

## Solution: Route Unknowns to HITL

EstimAI **never silently drops candidates**. Instead:

1. **Collect unknowns** separately
2. **Flag for Human-In-The-Loop (HITL)** review
3. **Show in UI** as "unknown" network
4. **Only hide after verifier approval**

### Architecture

```
LLM Classification
    ↓
Filter by discipline (storm/sanitary/water)
    ├─→ Classified → Add to network
    └─→ Unknown → Add to "unknown" network with HITL flag
            ↓
        Review UI shows all pipes (including unknowns)
            ↓
        Verifier reviews unknowns
            ├─→ Reclassify → Move to correct network
            └─→ Approve hide → Remove from output
```

## Implementation

### 1. Detectors Return Full Data

Each detector now returns:
- `pipes`: Classified pipes for this network
- `all_detections`: ALL detections from LLM (before filtering)
- `classified_ids`: Set of IDs that made it into this network

**Example** (`backend/app/services/detectors/storm.py`):
```python
return {
    "nodes": nodes,
    "pipes": storm_pipes,  # Only storm discipline
    "qa_flags": qa_flags,
    "all_detections": detections,  # ALL LLM results
    "classified_ids": {p["id"] for p in storm_pipes}  # What we kept
}
```

### 2. Unknown Collector

**File**: `backend/app/services/detectors/unknown.py`

```python
def collect_unknowns(
    all_detections: List[Any],
    classified_ids: set[str]
) -> Dict[str, Any]:
    """
    Collect pipes that weren't classified into any network.
    
    NOT silently dropped - flagged for HITL review.
    """
    unknown_pipes = []
    
    for detection in all_detections:
        if detection.polyline_id not in classified_ids:
            # This pipe was excluded - find out why
            discipline = detection.attrs.discipline
            confidence = detection.attrs.confidence or 0.0
            
            # Determine exclusion reason
            if discipline is None or discipline == "unknown":
                exclusion_reason = "NO_DISCIPLINE"
            elif discipline not in ["storm", "sanitary", "water"]:
                exclusion_reason = f"INVALID_DISCIPLINE_{discipline}"
            elif confidence < MIN_CONFIDENCE:
                exclusion_reason = f"LOW_CONFIDENCE_{confidence:.2f}"
            else:
                exclusion_reason = "UNKNOWN"
            
            # Create pipe with HITL flag
            unknown_pipe = {
                "id": detection.polyline_id,
                "discipline": discipline,
                "material": detection.attrs.material,
                "dia_in": detection.attrs.dia_in,
                "confidence": confidence,
                "reason": detection.reason,
                "exclusion_reason": exclusion_reason,
                "hitl_required": True,  # Explicit HITL flag
                "qa_flags": [{
                    "code": f"UNCLASSIFIED_{exclusion_reason}",
                    "message": f"Pipe excluded: {exclusion_reason}. Requires HITL review.",
                    "severity": "warning"
                }]
            }
            
            unknown_pipes.append(unknown_pipe)
    
    return {
        "nodes": [],
        "pipes": unknown_pipes,
        "qa_flags": [...]
    }
```

### 3. Integration in `run_extract`

**File**: `backend/app/services/detectors/__init__.py`

```python
# Detect networks
storm_result = detect_storm_network(...)
sanitary_result = detect_sanitary_network(...)
water_result = detect_water_network(...)

# Collect unknowns
all_detections_combined = []
classified_ids_combined = set()

for result in [storm_result, sanitary_result, water_result]:
    all_detections_combined.extend(result.get("all_detections", []))
    classified_ids_combined.update(result.get("classified_ids", set()))

unknown_result = collect_unknowns(all_detections_combined, classified_ids_combined)

# Build response
networks = {
    'storm': storm_result,
    'sanitary': sanitary_result,
    'water': water_result,
    'unknown': unknown_result  # Always include if non-empty
}
```

## Output Format

### Response Structure

```json
{
  "networks": {
    "storm": {
      "pipes": [...]
    },
    "sanitary": {
      "pipes": [...]
    },
    "water": {
      "pipes": [...]
    },
    "unknown": {
      "pipes": [
        {
          "id": "poly_abc123",
          "discipline": null,
          "material": "pvc",
          "dia_in": 8.0,
          "confidence": 0.25,
          "reason": "Layer UTILITY, no specific text",
          "exclusion_reason": "LOW_CONFIDENCE_0.25",
          "hitl_required": true,
          "qa_flags": [
            {
              "code": "UNCLASSIFIED_LOW_CONFIDENCE_0.25",
              "message": "Pipe excluded: LOW_CONFIDENCE_0.25. Requires HITL review.",
              "severity": "warning"
            }
          ]
        }
      ],
      "qa_flags": [
        {
          "code": "UNKNOWNS_PRESENT",
          "message": "15 unclassified pipes require HITL review",
          "severity": "warning"
        }
      ]
    }
  }
}
```

### Exclusion Reasons

| Code | Description |
|------|-------------|
| `NO_DISCIPLINE` | LLM returned `discipline=null` |
| `INVALID_DISCIPLINE_{type}` | LLM returned invalid type (e.g., "utility") |
| `LOW_CONFIDENCE_{conf}` | Confidence below threshold (e.g., 0.25 < 0.35) |
| `UNKNOWN` | Other exclusion reason |

## UI Integration

### Review Page

**Show unknowns prominently**:

```tsx
<NetworkSection network="unknown" color="gray">
  <WarningBanner>
    ⚠️ {unknownCount} unclassified pipes require review
  </WarningBanner>
  
  {unknownPipes.map(pipe => (
    <PipeRow 
      key={pipe.id}
      pipe={pipe}
      actions={[
        <Button onClick={() => reclassify(pipe)}>Reclassify</Button>,
        <Button onClick={() => approveHide(pipe)}>Approve Hide</Button>
      ]}
    />
  ))}
</NetworkSection>
```

### HITL Actions

**1. Reclassify**:
```tsx
function reclassify(pipe) {
  // Show modal with discipline picker
  const newDiscipline = await showDisciplinePicker(pipe);
  
  // Move pipe to correct network
  await movePipe(pipe.id, "unknown", newDiscipline);
  
  // Log for audit
  logAction("RECLASSIFY", pipe.id, { from: "unknown", to: newDiscipline });
}
```

**2. Approve Hide**:
```tsx
function approveHide(pipe) {
  // Confirm with user
  if (await confirm(`Hide ${pipe.id}?`)) {
    // Mark as reviewed and hidden
    await updatePipe(pipe.id, { hidden: true, reviewed: true });
    
    // Log for audit
    logAction("APPROVE_HIDE", pipe.id, { reason: pipe.exclusion_reason });
  }
}
```

## Logging

### Detection Phase

```
🔍 LLM Classification Results (BEFORE filtering):
  Total patches sent: 50
  Detections returned: 48

AFTER filtering (discipline='storm', confidence>=0.35):
  Storm: 12 pipes
  
AFTER filtering (discipline='sanitary', confidence>=0.35):
  Sanitary: 18 pipes
  
AFTER filtering (discipline='water', confidence>=0.35):
  Water: 8 pipes
  
🤔 Unknown: poly_abc123 - LOW_CONFIDENCE_0.25 (discipline=null, conf=0.25)
🤔 Unknown: poly_def456 - NO_DISCIPLINE (discipline=null, conf=0.45)
...

⚠️ 10 pipes flagged as UNKNOWN - routed to HITL, NOT silently dropped

Classification summary:
  38 classified
  10 unknown (routed to HITL)
```

### Extract Complete

```
Extract complete: 48 total pipes across 4 networks (38 classified, 10 unknown)

⚠️ 'unknown' network added with 10 pipes - requires HITL review before approval
```

## Testing

### Test 1: Unknowns are NOT dropped

**Input**:
- 50 candidates
- LLM classifies 40 with high confidence
- LLM classifies 10 with low confidence or null discipline

**Expected**:
- 40 in storm/sanitary/water networks
- 10 in "unknown" network with HITL flags
- UI shows 50 total pipes (none dropped)

**Assert**:
```python
def test_unknowns_not_dropped():
    result = run_extract(pdf_path)
    
    classified = sum(len(net['pipes']) for k, net in result['networks'].items() if k != 'unknown')
    unknown = len(result['networks'].get('unknown', {}).get('pipes', []))
    total = classified + unknown
    
    # All candidates accounted for
    assert total == 50
    assert unknown == 10
    assert all(p['hitl_required'] for p in result['networks']['unknown']['pipes'])
```

### Test 2: No unknowns (happy path)

**Input**:
- 30 candidates
- LLM classifies all 30 with high confidence

**Expected**:
- 30 in storm/sanitary/water networks
- No "unknown" network (or empty)

**Assert**:
```python
def test_no_unknowns_happy_path():
    result = run_extract(pdf_path)
    
    assert 'unknown' not in result['networks'] or len(result['networks']['unknown']['pipes']) == 0
    
    classified = sum(len(net['pipes']) for net in result['networks'].values())
    assert classified == 30
```

### Test 3: All unknowns (worst case)

**Input**:
- 20 candidates
- LLM returns all null or low confidence

**Expected**:
- 0 in storm/sanitary/water networks
- 20 in "unknown" network with HITL flags
- Clear warning in logs

**Assert**:
```python
def test_all_unknowns_worst_case():
    result = run_extract(pdf_path)
    
    classified = sum(len(net['pipes']) for k, net in result['networks'].items() if k != 'unknown')
    unknown = len(result['networks'].get('unknown', {}).get('pipes', []))
    
    assert classified == 0
    assert unknown == 20
    
    # Should have validation retry triggered
    assert "IMPROBABLE_ZERO" in logs  # From validation.py
```

## Benefits

1. **Transparency**: User sees ALL pipes, including unknowns
2. **No silent failures**: Never drops candidates without explanation
3. **HITL routing**: Unknowns flagged for human review
4. **Audit trail**: Exclusion reason logged for each unknown
5. **Reclassification**: User can fix LLM mistakes
6. **Approved hiding**: User explicitly approves removal

## Comparison

### Before (Silent Filtering)

```
Candidates: 50
↓ LLM
Detections: 48
↓ Filter (drop unknowns)
Output: 38 pipes
❌ 10 pipes silently disappeared
```

### After (HITL Routing)

```
Candidates: 50
↓ LLM
Detections: 48
↓ Route by discipline
├─ storm: 12
├─ sanitary: 18
├─ water: 8
└─ unknown: 10 (flagged for HITL)
✅ Output: 48 pipes (38 classified + 10 unknown)
```

## Future Enhancements

1. **Auto-reclassification rules**: Common patterns → auto-assign
2. **Confidence boosting**: Re-run LLM on unknowns with more context
3. **Batch HITL actions**: Approve/hide multiple unknowns at once
4. **Unknown analytics**: Track common exclusion reasons
5. **Feedback loop**: HITL corrections → improve LLM prompt

