# Token Budgeting and Context Length Management

## Problem

**Context length overflow** is a silent killer of LLM classification:

```
Candidates: 200 pipes
↓ Build context (candidates + labels + legend)
Context: 150,000 tokens (exceeds 128k limit)
↓ LLM truncates input silently
Legend/labels get cut off → "0 classified"
```

**Symptoms**:
- Works fine with small PDFs (<50 pipes)
- Fails with large PDFs (>100 pipes)
- LLM returns mostly "unknown" despite clear evidence
- No error message (truncation is silent)

## Solution: Token Budgeting + Spatial Tiling

EstimAI implements **automatic context management**:

1. **Estimate tokens before sending**
2. **Check if context fits** within budget (123k tokens)
3. **If too large**: Tile into spatial neighborhoods
4. **Process tiles independently** and merge results

### Token Limits (gpt-4o-mini)

```python
MAX_CONTEXT_TOKENS = 128_000    # Model limit
MAX_OUTPUT_TOKENS = 4_000       # Reserve for response
SAFE_PROMPT_TOKENS = 123_000    # Leave 1k safety margin
```

## Implementation

### 1. Token Estimation

**File**: `backend/app/services/ai/token_budget.py`

```python
def estimate_tokens(text: str) -> int:
    """
    Estimate token count using simple heuristic:
    1 token ≈ 4 characters (conservative for English)
    """
    return len(text) // 4

def estimate_context_tokens(prompt: str, context: Dict) -> int:
    """
    Estimate total tokens for LLM call.
    """
    prompt_tokens = estimate_tokens(prompt)
    context_tokens = estimate_tokens(json.dumps(context))
    return prompt_tokens + context_tokens
```

**Note**: Uses simple heuristic for speed. For production accuracy, use `tiktoken` library.

### 2. Context Length Check

```python
def check_context_length(
    prompt: str,
    context: Dict,
    max_tokens: int = 123_000
) -> Tuple[bool, int]:
    """
    Check if context fits within token budget.
    
    Returns: (fits: bool, token_count: int)
    """
    token_count = estimate_context_tokens(prompt, context)
    fits = token_count <= max_tokens
    
    if not fits:
        logger.warning(
            f"⚠️ Context overflow: {token_count} tokens > {max_tokens} limit"
        )
    
    return (fits, token_count)
```

### 3. Spatial Tiling

**Strategy**: Divide large PDFs into connected neighborhoods.

```python
def spatial_tile_candidates(
    candidates: List[Dict],
    tile_size_ft: float = 500.0,    # 500 ft × 500 ft tiles
    overlap_ft: float = 100.0       # 100 ft overlap
) -> List[List[Dict]]:
    """
    Tile candidates into spatial neighborhoods.
    
    Process:
    1. Compute global bounding box
    2. Divide into 500 ft × 500 ft tiles
    3. Add 100 ft overlap between tiles
    4. Assign candidates to tiles by bbox center
    5. Return list of candidate lists (one per tile)
    """
    # ... (implementation details in code)
```

**Why 500 ft with 100 ft overlap**:
- **500 ft**: Typical utility corridor length
- **100 ft**: Captures nearby pipes at tile boundaries
- **Overlap**: Ensures connected pipes aren't split

### 4. Automatic Tiling

**File**: `backend/app/services/ai/pipe_classifier.py`

```python
def _classify_batch(self, patches):
    # Build context
    context = self._build_context(patches)
    prompt = self._get_classification_prompt()
    
    # Check if tiling needed
    tiled_contexts = tile_large_context(prompt, context)
    
    if len(tiled_contexts) > 1:
        # Process each tile
        all_detections = []
        for tile_context in tiled_contexts:
            tile_detections = self._classify_tile(tile_context, prompt)
            all_detections.extend(tile_detections)
        return all_detections
    else:
        # Single context, process normally
        return self._classify_tile(context, prompt)
```

## Example: Large PDF

### Input

- 200 polylines
- 1000 text labels
- Full legend with 50 entries

### Token Calculation

```
Prompt: 1,500 tokens
Candidates: 200 × 150 tokens = 30,000 tokens
Labels: 1000 × 20 tokens = 20,000 tokens
Legend: 50 × 30 tokens = 1,500 tokens
-------------------------------------------
Total: 53,000 tokens → ✅ Fits!
```

### But What If...

- 500 polylines
- 3000 text labels
- Full legend

```
Prompt: 1,500 tokens
Candidates: 500 × 150 tokens = 75,000 tokens
Labels: 3000 × 20 tokens = 60,000 tokens
Legend: 50 × 30 tokens = 1,500 tokens
-------------------------------------------
Total: 138,000 tokens → ❌ Overflow!
```

### Tiling Solution

```
Spatial analysis:
- PDF bounds: 0-2000 ft × 0-1500 ft
- Tile size: 500 ft × 500 ft
- Tiles needed: 4×3 = 12 tiles

Tile 1: (0-500, 0-500)
  - 42 polylines
  - 150 labels (nearby only)
  - Tokens: 8,500 → ✅ Fits

Tile 2: (500-1000, 0-500)
  - 38 polylines
  - 120 labels
  - Tokens: 7,800 → ✅ Fits

... (10 more tiles)

Result: 12 tiles, all fit within budget
```

## Logging

### Normal Case (No Tiling)

```
Context fits in budget: 45,200 tokens < 123,000
📊 Token usage: input=45,200 (prompt=1,500, context=43,700), output=2,800, total=48,000
```

### Tiling Case

```
⚠️ Context overflow: 138,000 tokens > 123,000 limit (15,000 tokens over)
Splitting into spatial tiles...

Spatial tiling: 500 candidates → 4×3 tiles (500ft with 100ft overlap)
Created 12 non-empty tiles

Context tiled into 12 chunks
Processing tile 1/12...
Tile 1/12: 42 candidates, 8,500 tokens
...
Processing tile 12/12...
Tile 12/12: 35 candidates, 7,200 tokens

Merged 487 detections from 12 tiles
```

## Benefits

### 1. No Silent Truncation

**Before**:
```
Context: 150k tokens
→ LLM silently truncates to 128k
→ Legend/labels cut off
→ "0 classified" (no error message)
```

**After**:
```
Context: 150k tokens
→ Detected overflow
→ Automatically tiled into 12 chunks
→ All tiles processed successfully
→ 487 pipes classified
```

### 2. Scalable to Large PDFs

- Small PDFs (<50 pipes): Single context, fast
- Medium PDFs (50-200 pipes): Single context, may approach limit
- Large PDFs (>200 pipes): Automatic tiling, slower but reliable

### 3. Spatial Coherence

Tiling by geography ensures:
- Connected pipes stay together
- Nearby labels included in context
- Overlap captures boundary pipes

### 4. Transparent

Full logging:
- Token estimates before sending
- Tile count and sizes
- Per-tile statistics
- Merge results

## Configuration

### Tile Size

```python
# Default: 500 ft × 500 ft
tile_size_ft = 500.0

# Smaller tiles (more tiles, less context per tile)
tile_size_ft = 300.0  # Good for dense urban plans

# Larger tiles (fewer tiles, more context per tile)
tile_size_ft = 1000.0  # Good for sparse rural plans
```

### Overlap

```python
# Default: 100 ft overlap
overlap_ft = 100.0

# More overlap (better boundary handling, more redundant context)
overlap_ft = 200.0

# Less overlap (less redundant context, risk missing boundary pipes)
overlap_ft = 50.0
```

### Token Budget

```python
# Default: 123k (safe for gpt-4o-mini 128k context)
SAFE_PROMPT_TOKENS = 123_000

# More aggressive (closer to limit, less safety margin)
SAFE_PROMPT_TOKENS = 126_000

# More conservative (larger safety margin, more likely to tile)
SAFE_PROMPT_TOKENS = 120_000
```

## Testing

### Test 1: Small PDF (No Tiling)

```python
def test_small_pdf_no_tiling():
    patches = create_patches(count=30)
    
    context = build_context(patches)
    prompt = get_prompt()
    
    tiled = tile_large_context(prompt, context)
    
    assert len(tiled) == 1  # No tiling needed
    assert estimate_tokens(prompt, context) < 123_000
```

### Test 2: Large PDF (Tiling)

```python
def test_large_pdf_tiling():
    patches = create_patches(count=300)
    
    context = build_context(patches)
    prompt = get_prompt()
    
    tiled = tile_large_context(prompt, context)
    
    assert len(tiled) > 1  # Tiling occurred
    
    # Each tile should fit
    for tile_context in tiled:
        assert estimate_tokens(prompt, tile_context) < 123_000
```

### Test 3: Tile Overlap

```python
def test_tile_overlap():
    # Create pipe at tile boundary (250 ft)
    patches = [
        {"bbox": [245, 0, 255, 100], "id": "boundary_pipe"}
    ]
    
    tiles = spatial_tile_candidates(patches, tile_size_ft=500, overlap_ft=100)
    
    # Pipe should appear in both adjacent tiles
    tile1_ids = {p["id"] for p in tiles[0]}
    tile2_ids = {p["id"] for p in tiles[1]}
    
    assert "boundary_pipe" in tile1_ids
    assert "boundary_pipe" in tile2_ids  # Captured by overlap
```

## Troubleshooting

### Issue: "0 classified" on large PDFs

**Diagnosis**: Check logs for context overflow

```bash
grep "Context overflow" /tmp/backend_*.log
```

**If found**: Tiling should happen automatically. Check:
1. Tiles created successfully?
2. Each tile processed?
3. Results merged?

### Issue: Tiles still overflowing

```
⚠️ Tile 3 still too large: 130,000 tokens!
```

**Causes**:
- Too many labels per candidate
- Tile size too large
- Extremely dense area

**Fix**:
1. Reduce tile size: `tile_size_ft = 300.0`
2. Limit labels per candidate: `max_labels = 10`
3. Simplify legend

### Issue: Duplicate pipes in output

**Cause**: Overlap zones processed twice

**Expected Behavior**: Deduplication happens in merge step

**Verify**:
```python
all_ids = [d.polyline_id for d in detections]
assert len(all_ids) == len(set(all_ids))  # No duplicates
```

## Future Enhancements

1. **Accurate token counting**: Use `tiktoken` library instead of heuristic
2. **Adaptive tiling**: Adjust tile size based on density
3. **Smart label filtering**: Include only truly nearby labels (spatial index)
4. **Hierarchical tiling**: Split large tiles recursively
5. **Token caching**: Cache common legend/prompt tokens

## Conclusion

Token budgeting ensures EstimAI **scales to large PDFs**:

- ✅ No silent truncation
- ✅ Automatic tiling when needed
- ✅ Spatial coherence preserved
- ✅ Full transparency via logging

**Key insight**: Context overflow is predictable and preventable. Detect it early, tile spatially, process independently, merge results.

