# 🔍 Real Detection Pipeline - Current Status

## 📊 **Summary**

The infrastructure for real Apryse+LLM detection is **90% complete**, but missing critical Apryse extraction functions.

---

## ✅ **What's Implemented and Working**

### **1. Vector Extractor Framework** ✅
- **File**: `backend/app/services/extract/apryse_vectors.py`
- **Status**: Compiles, initializes, loads PDFs
- **Missing**: `extract_vectors()` and `extract_text()` functions in `pdfnet_runtime.py`

### **2. Pipe Classifier (LLM)** ✅  
- **File**: `backend/app/services/ai/pipe_classifier.py`
- **Status**: Fully working, all tests pass (9/9)
- **Can**: Classify polylines by discipline, extract material/diameter from text
- **Uses**: gpt-4o-mini with deterministic seed support

### **3. Network Detection Functions** ✅
- **Files**: `storm.py`, `sanitary.py`, `water.py`
- **Status**: Wired to call VectorExtractor + PipeClassifier
- **Fallback**: Uses demo data when extraction fails
- **Feature Flag**: `ESTIMAI_USE_DEMO=1` to force demo mode

### **4. Depth & QA Analysis** ✅
- **Status**: Working (calculates trench volumes, depth buckets, QA flags)
- **Input**: Takes pipe geometry and outputs depth stats

---

## ❌ **What's Missing**

### **Critical Gap: Apryse Extraction Functions**

**File**: `backend/app/services/ingest/pdfnet_runtime.py`

**Currently has:**
- ✅ `init(license_key)` - Initialize Apryse
- ✅ `open_doc(path)` - Open PDF document
- ✅ `iter_pages(doc)` - Iterate pages

**Missing:**
- ❌ `extract_vectors(page)` - Extract vector geometry
- ❌ `extract_text(page)` - Extract text annotations

**Impact:** VectorExtractor can open PDFs but can't extract geometry or text, so it returns empty lists, which means zero pipes detected.

---

## 🔗 **Current Call Chain**

```
User uploads PDF
  ↓
/v1/agent/takeoff OR /v1/takeoff/pdf
  ↓
detect_storm_network(vectors, texts, pdf_path)
  ↓
VectorExtractor(pdf_path)
  ├─ load_scale() ✅ Works (returns assumed scale)
  ├─ extract_layer_lines() ❌ Returns [] (extract_vectors missing)
  └─ extract_text_annotations() ❌ Returns [] (extract_text missing)
  ↓
PipeClassifier.classify([]) ✅ Works (but gets empty input)
  ↓
Result: 0 pipes detected
  ↓
Fallback: Returns DEMO DATA (6 mock pipes)
```

---

## 🎯 **What Needs to Happen**

### **Option 1: Implement Apryse Extraction Functions** (Best)

Add to `backend/app/services/ingest/pdfnet_runtime.py`:

```python
def extract_vectors(page: Any) -> List[Dict[str, Any]]:
    """
    Extract vector geometry from PDF page using Apryse PDFNet.
    
    Returns list of vector elements with:
    - type: "line" | "polyline" | "path"
    - points: [(x, y), ...]
    - stroke: {color, width}
    - layer: str (OCG name if available)
    """
    # Use PDFNet ElementReader to walk page content
    # Filter for Path elements
    # Extract coordinates and stroke properties
    pass


def extract_text(page: Any) -> List[Dict[str, Any]]:
    """
    Extract text elements from PDF page using Apryse PDFNet.
    
    Returns list of text elements with:
    - text: str
    - bbox: (minx, miny, maxx, maxy)
    - x, y: center coordinates
    """
    # Use PDFNet TextExtractor
    # Get bounding boxes and content
    pass
```

### **Option 2: Use Existing `/v1/takeoff/pdf` Data** (Hack)

The `/v1/takeoff/pdf` route already extracts vectors and texts at lines 70-85. We could:
1. Export those extraction functions
2. Call them from VectorExtractor
3. Reuse the same data

### **Option 3: Vision-Only Mode** (Alternative)

Skip vector extraction entirely and use Vision LLM on rasterized pages:
1. Convert PDF page to image
2. Send to gpt-4-vision
3. Ask it to identify pipes and measure lengths
4. No vector geometry needed

---

## 🧪 **Current Test Results**

### **With Real Pipeline (APR_USE_APRYSE=1, ESTIMAI_USE_DEMO=0)**:
```bash
curl -F "file=@samples/bid_test.pdf" http://localhost:8000/v1/agent/takeoff
# Result: 0 pipes (extraction returns empty lists)
```

### **With Demo Mode (ESTIMAI_USE_DEMO=1)**:
```bash
ESTIMAI_USE_DEMO=1 curl -F "file=@samples/bid_test.pdf" http://localhost:8000/v1/agent/takeoff
# Result: 6 pipes (hardcoded mock data)
```

### **What Works:**
- ✅ PDF opens with Apryse
- ✅ Scale loaded (assumed 1"=20')
- ✅ PipeClassifier ready to classify
- ✅ Depth/QA analysis functional
- ❌ Vector extraction returns []
- ❌ Text extraction returns []
- Result: Falls back to demo data

---

## 📝 **Files Created/Modified**

### **New Files:**
- `backend/app/services/extract/apryse_vectors.py` - Vector extractor framework
- `backend/app/services/extract/__init__.py` - Package exports
- `backend/app/services/ai/pipe_classifier.py` - LLM classifier
- `backend/app/services/ai/__init__.py` - Package exports
- `backend/tests/test_vector_extractor.py` - Extractor tests
- `backend/tests/test_pipe_classifier.py` - Classifier tests (9/9 passing)

### **Modified Files:**
- `backend/app/services/detectors/storm.py` - Wired to real pipeline + fallback
- `backend/app/services/detectors/sanitary.py` - Wired to real pipeline + fallback
- `backend/app/services/detectors/water.py` - Wired to real pipeline + fallback
- `backend/app/api/v1/routes/takeoff.py` - Pass pdf_path to detectors

---

## 🚀 **Next Steps**

### **Immediate (to get real detection working):**

1. **Implement `extract_vectors()` in `pdfnet_runtime.py`**
   - Walk PDFNet page elements
   - Extract Path/Line geometry
   - Return with layer/stroke info

2. **Implement `extract_text()` in `pdfnet_runtime.py`**
   - Use PDFNet TextExtractor
   - Get text with bounding boxes
   - Return structured format

3. **Test with real PDF**
   - Should detect actual pipes from vector geometry
   - Should extract real sizes/materials from annotations
   - Should calculate real lengths using scale

### **Alternative (quicker demo):**

Use `ESTIMAI_USE_DEMO=1` to show the full pipeline working with mock data, then explain that real extraction is "coming soon" pending Apryse function implementation.

---

## 📚 **Documentation**

- `PLACEHOLDER_ANALYSIS.md` - Explains where mock data comes from
- `TRANSPARENCY_IMPLEMENTATION.md` - Pipeline transparency features
- `DETERMINISTIC_TESTING.md` - Ground truth validation
- This file - Real detection status

**The architecture is sound, just needs the Apryse extraction functions implemented!** 🏗️

