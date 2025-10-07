# 🔍 **Placeholder Detection Analysis - Complete Call Chain**

## 📊 **Summary: You're Getting Mock Data**

The 6 pipes you see are **hardcoded placeholders**, not real measurements from your PDF.

---

## 🎭 **The 6 Pipes Explained**

### **Where They Come From:**

**File**: `backend/app/services/detectors/storm.py` (lines 43-59)
**File**: `backend/app/services/detectors/sanitary.py` (lines 43-59)
**File**: `backend/app/services/detectors/water.py` (lines 43-59)

Each network generates **2 mock pipes** using this formula:

```python
def trace_edges(vectors: List[Dict], nodes: List[Dict]) -> List[Pipe]:
    pipes = []
    for i in range(len(nodes) - 1):
        pipe = Pipe(
            id=f"storm_pipe_{i}",
            from_id=nodes[i]["id"],
            to_id=nodes[i + 1]["id"],
            length_ft=50.0 + (i * 25.0),  # ← HARDCODED!
            dia_in=12.0 + (i * 2.0),      # ← HARDCODED!
            mat="pvc"                      # ← HARDCODED!
        )
        pipes.append(pipe)
    return pipes
```

### **Breakdown:**

| Network | Pipe # | Length (LF) | Diameter (in) | Material | Formula |
|---------|--------|-------------|---------------|----------|---------|
| Storm | 0 | 50 | 12" | PVC | 50 + (0×25), 12 + (0×2) |
| Storm | 1 | 75 | 14" | PVC | 50 + (1×25), 12 + (1×2) |
| Sanitary | 0 | 40 | 8" | PVC | Different base values |
| Sanitary | 1 | 60 | 9" | PVC | Different base values |
| Water | 0 | 60 | 6" | D.I. | Different base values |
| Water | 1 | 90 | 7" | D.I. | Different base values |

**Total: 6 pipes, 375 LF** - all fake!

---

## 🔗 **Complete Call Chain**

### **Path 1: Agent API (What You're Testing)**

```
curl POST /v1/agent/takeoff
  ↓
backend/app/api/v1/routes/agent.py :: agent_takeoff()
  ↓
backend/app/agent/takeoff_impl.py :: DefaultTakeoffAgent.run()
  ↓
backend/app/agent/adapters/extract_adapter.py :: extract_any()
  ↓ (tries multiple paths, finds http_extract_bridge)
backend/app/agent/adapters/http_extract_bridge.py :: extract_via_route()
  ↓
TestClient.post("/v1/takeoff/pdf")  ← HTTP BRIDGE
  ↓
backend/app/api/v1/routes/takeoff.py :: takeoff_pdf()
  ↓
Apryse extracts vectors + texts from PDF
  ↓
backend/app/services/detectors/storm.py :: detect_storm_network(vectors, texts)
backend/app/services/detectors/sanitary.py :: detect_sanitary_network(vectors, texts)
backend/app/services/detectors/water.py :: detect_water_network(vectors, texts)
  ↓
Each calls trace_edges() which returns MOCK PIPES ← HERE'S THE PROBLEM
  ↓
Returns EstimAIResult with fake data
```

### **Path 2: Demo Project Pipeline**

```
Frontend: Click "Run Pipeline"
  ↓
POST /api/projects/demo/pipeline_async
  ↓
backend/app/api/routes_projects.py :: pipeline_async()
  ↓
backend/app/workers/run_pipeline.py :: run_pipeline()
  ↓
backend/app/services/orchestrator.py :: run_full_pipeline()
  ↓
orchestrator.run_takeoff(pid)
  ↓
backend/app/agent/takeoff_impl.py :: DefaultTakeoffAgent.run()
  ↓
[Same path as above - ends with MOCK PIPES]
```

---

## ✅ **What IS Working (Real Code)**

### **1. Apryse PDFNet Extraction** ✅

**File**: `backend/app/api/v1/routes/takeoff.py` (lines 37-80)

```python
# Step 1: Open PDF with Apryse
from backend.app.services.ingest.pdfnet_runtime import open_doc, iter_pages
doc = open_doc(tmp_file_path)

# Step 2: Extract scale information
from backend.app.services.ingest.scale_parser import extract_scale
scale_data = extract_scale(doc, page)

# Step 3: Extract vectors and text
from backend.app.services.ingest.pdfnet_runtime import extract_vectors, extract_text
all_vectors = extract_vectors(page)
all_texts = extract_text(page)
```

**Status**: ✅ This code RUNS and extracts real vector geometry + text from PDF

### **2. Vision LLM Detector** ✅

**File**: `backend/app/services/detectors/vision_llm.py` (lines 62-140)

```python
class VisionLLMDetector:
    async def detect(self, page_rgb: np.ndarray) -> List[dict]:
        prompt, schema = prompt_takeoff(TYPES)
        tiles = make_tiles(page_rgb, self.tile_px, self.overlap_px)
        # Sends images to gpt-4o-mini for detection
        results = await self._detect_all_tiles(tiles)
```

**Status**: ✅ This code EXISTS but is NOT BEING CALLED by the network detectors

---

## ❌ **What's NOT Working (Placeholders)**

### **Network Detection Functions** ❌

**Files:**
- `backend/app/services/detectors/storm.py` (lines 28-59)
- `backend/app/services/detectors/sanitary.py` (lines 28-59)
- `backend/app/services/detectors/water.py` (lines 28-59)

**Problem:**
```python
def detect_nodes(vectors: List[Dict], texts: List[Dict]) -> List[Dict]:
    """Detect storm network nodes (inlets, manholes, etc.)."""
    # Placeholder implementation ← FAKE DATA
    nodes = []
    for i, text in enumerate(texts[:3]):  # ← Uses first 3 texts randomly
        nodes.append({
            "id": f"inlet_{i}",
            "kind": "inlet",
            # Just uses text position, doesn't actually detect inlets
        })
    return nodes

def trace_edges(vectors: List[Dict], nodes: List[Dict]) -> List[Pipe]:
    """Trace storm network edges (pipes) between nodes."""
    pipes = []
    for i in range(len(nodes) - 1):
        pipe = Pipe(
            id=f"storm_pipe_{i}",
            from_id=nodes[i]["id"],
            to_id=nodes[i + 1]["id"],
            length_ft=50.0 + (i * 25.0),  # ← FAKE LENGTH!
            dia_in=12.0 + (i * 2.0),      # ← FAKE DIAMETER!
            mat="pvc"                      # ← FAKE MATERIAL!
        )
        pipes.append(pipe)
    return pipes
```

**These functions receive REAL vector data but ignore it and return fake pipes!**

---

## 🎯 **What Needs to Happen**

### **Replace Placeholders with Real Detection:**

The `detect_storm_network`, `detect_sanitary_network`, `detect_water_network` functions need to:

1. **Use the vectors data** (from Apryse) to find actual pipe lines
2. **Use the texts data** (from Apryse) to find annotations (sizes, materials)
3. **Calculate real lengths** from vector geometry
4. **Match symbols** to identify node types (manholes vs inlets)
5. **Build network topology** from actual connections

### **Option A: Use VisionLLMDetector**

Wire the Vision LLM detector into these functions to analyze the visual content and identify pipes.

### **Option B: Use Vector Geometry**

Process the `vectors` list directly:
- Filter for polylines/lines by layer/color
- Calculate geometric lengths
- Match annotations to pipes
- Build network graph

### **Option C: Hybrid**

Use Apryse vectors for geometry + Vision LLM for classification/validation.

---

## 🔬 **What's Actually in the PDF?**

Let me show you what Apryse IS extracting:

<function_calls>
<invoke name="run_terminal_cmd">
<parameter name="command">curl -s "http://localhost:8000/v1/takeoff/pdf" \
  -F "file=@samples/bid_test.pdf" \
2>&1 | jq -e '.networks.storm.pipes[0]' > /dev/null && echo "✅ Real /v1/takeoff/pdf endpoint works" || echo "❌ Endpoint may have errors"
