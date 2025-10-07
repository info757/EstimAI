# EstimAI Environment Variables

This document describes all environment variables used by the EstimAI backend.

## 🔧 Core Configuration

### Required Variables

#### `OPENAI_API_KEY`
- **Description**: OpenAI API key for LLM classification
- **Required**: Yes (for LLM-based detection)
- **Example**: `sk-proj-...`
- **Get**: https://platform.openai.com/api-keys

#### `APR_LICENSE_KEY`
- **Description**: Apryse PDFNet license key
- **Required**: Yes (if `APR_USE_APRYSE=1`)
- **Example**: `demo:1759355776611:...`
- **Get**: https://www.apryse.com

---

## 🎛️ Detection Pipeline Configuration

### `APR_USE_APRYSE`
- **Description**: Enable Apryse PDFNet for vector extraction and scale parsing
- **Values**: `0` (disabled) or `1` (enabled)
- **Default**: `0`
- **Recommendation**: Set to `1` for production
- **Impact**: Enables real vector/scale extraction from PDFs

### `ESTIMAI_USE_DEMO`
- **Description**: Use fake demo data instead of real extraction
- **Values**: `0` (production) or `1` (demo)
- **Default**: `0`
- **Recommendation**: Always `0` for production
- **Impact**: 
  - `0`: Real extraction or explicit errors
  - `1`: Returns 6 fake pipes per network for testing

### `ESTIMAI_TEXT_BACKEND`
- **Description**: Text extraction backend selection
- **Values**: `pymupdf` (fast, real coords) or `pdfnet` (robust, estimated)
- **Default**: `pymupdf`
- **Recommendation**: Use `pymupdf` for production
- **Impact**:
  - `pymupdf`: Real word bounding boxes, phrase merging, fast
  - `pdfnet`: Estimated positions, word-level, slower but more robust

### `ESTIMAI_PIPE_MIN_CONF`
- **Description**: Minimum confidence threshold for pipe classification
- **Values**: Float between `0.0` and `1.0`
- **Default**: `0.35`
- **Recommendations**:
  - `0.25-0.35`: Balanced (catch more, some false positives)
  - `0.35-0.50`: Conservative (fewer false positives)
  - `0.50-0.80`: Very conservative (may miss valid pipes)
- **Impact**: Filters out low-confidence detections

### `ESTIMAI_DEBUG`
- **Description**: Enable debug endpoints for development
- **Values**: `0` (disabled) or `1` (enabled)
- **Default**: `0`
- **Recommendation**: `1` for development, `0` for production
- **Impact**: Enables `/v1/debug/extract` and `/v1/debug/health` endpoints

---

## 📊 Startup Logging

When the server starts, it logs all critical configuration:

```
2025-10-07 09:07:18,720 - backend.app.app - INFO - 📝 TextBackend=pymupdf
✅ Apryse PDFNet initialized
✅ Depth configuration initialized
2025-10-07 09:07:18,052 - backend.app.services.detectors.storm - INFO - Storm detector: MIN_CONFIDENCE threshold = 0.35
```

---

## 🚀 Recommended Production Settings

```bash
# .env for production

# Core
OPENAI_API_KEY=sk-proj-your-key-here
APR_LICENSE_KEY=your-apryse-license-here

# Detection Pipeline
APR_USE_APRYSE=1
ESTIMAI_USE_DEMO=0
ESTIMAI_TEXT_BACKEND=pymupdf
ESTIMAI_PIPE_MIN_CONF=0.35
ESTIMAI_DEBUG=0

# Optional
LOG_LEVEL=INFO
ARTIFACT_DIR=backend/artifacts
```

---

## 🧪 Recommended Development Settings

```bash
# .env for development

# Core
OPENAI_API_KEY=sk-proj-your-key-here
APR_LICENSE_KEY=demo:your-demo-key-here

# Detection Pipeline
APR_USE_APRYSE=1
ESTIMAI_USE_DEMO=0
ESTIMAI_TEXT_BACKEND=pymupdf
ESTIMAI_PIPE_MIN_CONF=0.25
ESTIMAI_DEBUG=1

# Optional
LOG_LEVEL=DEBUG
ESTIMAI_SEED=42
```

---

## 🔍 Optional Variables

### `ESTIMAI_SEED`
- **Description**: Random seed for deterministic LLM results
- **Values**: Integer (e.g., `42`)
- **Default**: None (non-deterministic)
- **Use**: Testing, reproducibility, ground truth comparison

### `LOG_LEVEL`
- **Description**: Logging verbosity
- **Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- **Default**: `INFO`

### `ARTIFACT_DIR`
- **Description**: Directory for storing artifacts
- **Values**: Path (relative or absolute)
- **Default**: `backend/artifacts`

---

## 📝 Complete Startup Log Example

```
Activating virtual environment...
Starting EstimAI backend server...
Environment: APR_USE_APRYSE=1
Working directory: /Users/williamholt/estimai

INFO:     Started server process [39308]
INFO:     Waiting for application startup.

✅ Database migrations completed: 0 indices applied
2025-10-07 09:07:18,720 - backend.app.app - INFO - 📝 TextBackend=pymupdf

PDFNet is running in demo mode.
2025-10-07 09:07:19,470 - backend.app.services.ingest.pdfnet_runtime - INFO - ✅ PDFNet initialized
✅ Apryse PDFNet initialized
✅ Depth configuration initialized

INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000

2025-10-07 09:07:18,052 - backend.app.services.detectors.storm - INFO - Storm detector: MIN_CONFIDENCE threshold = 0.35
2025-10-07 09:07:18,055 - backend.app.services.detectors.sanitary - INFO - Sanitary detector: MIN_CONFIDENCE threshold = 0.35
2025-10-07 09:07:18,059 - backend.app.services.detectors.water - INFO - Water detector: MIN_CONFIDENCE threshold = 0.35
```

This shows:
- ✅ TextBackend=pymupdf
- ✅ Apryse PDFNet initialized (APR_USE_APRYSE=1)
- ✅ MIN_CONFIDENCE threshold = 0.35
- ℹ️ ESTIMAI_USE_DEMO status (not explicitly logged, but can be inferred from behavior)
- ℹ️ ESTIMAI_DEBUG status (endpoints enabled/disabled)

---

## 🎯 Quick Reference

| Variable | Production | Development |
|----------|------------|-------------|
| `APR_USE_APRYSE` | `1` | `1` |
| `ESTIMAI_USE_DEMO` | `0` | `0` |
| `ESTIMAI_TEXT_BACKEND` | `pymupdf` | `pymupdf` |
| `ESTIMAI_PIPE_MIN_CONF` | `0.35` | `0.25` |
| `ESTIMAI_DEBUG` | `0` | `1` |

