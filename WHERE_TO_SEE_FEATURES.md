# 🗺️ Where to See All the New Features

This guide shows you exactly where each feature is and how to see it working.

---

## 1️⃣ Pipeline Transparency (Backend API)

### **What**: Agent response includes pipeline info showing Apryse + LLM are working

### **Where**: `/v1/agent/takeoff` API endpoint

### **How to See It**:

```bash
# Quick test with curl
curl -s "http://localhost:8000/v1/agent/takeoff" \
  -F "session_id=test" \
  -F "file=@samples/bid_test.pdf" \
| jq '.summary.pipeline'
```

### **What You'll See**:
```json
{
  "apryse_enabled": true,
  "llm_enabled": true,
  "llm_model": "gpt-4o-mini",
  "ground_source": "unknown",
  "prompt_token_count": null,
  "completion_token_count": null
}
```

### **Files to Review**:
- `backend/app/agent/types.py` - Lines 85-113 (PipelineInfo model)
- `backend/app/agent/takeoff_impl.py` - Lines 416-439 (Pipeline info generation)
- `backend/app/core/config.py` - Lines 48-54 (Settings with ESTIMAI_SEED)

---

## 2️⃣ Verification Panel (Frontend UI)

### **What**: Collapsible card showing pipeline status, depth analysis, and QA flags

### **Where**: Project page at `http://localhost:5173/projects/demo`

### **How to See It**:

**Step 1: Start Frontend**
```bash
cd frontend
npm run dev
```

**Step 2: Open Browser**
```
http://localhost:5173/projects/demo
```

**Step 3: Find the Panel**
- Scroll down below "Ingest Sources"
- Look for **"🔍 Verification"** card
- Click to expand it

### **What You'll See**:
- ✅ **Pipeline Components**: Shows Apryse (Active) and LLM (gpt-4o-mini)
- 📏 **Scale Verification**: Parsed scale with accuracy %
- 📊 **Depth Analysis**: Min/Avg/Max depth with ground source badge
- 📦 **Quantity Breakdown**: LF per depth bucket + total trench CY
- ⚠️ **QA Flags**: Badges for COVER_LOW, DEEP_EXCAVATION, etc.

### **Files to Review**:
- `frontend/src/components/VerificationPanel.tsx` - The full component
- `frontend/src/pages/ProjectPage.tsx` - Lines 11, 209 (Integration)

---

## 3️⃣ Deterministic Testing (Ground Truth)

### **What**: One-button test to verify results match expected values

### **Where**: Command line script `scripts/compare_ground_truth.sh`

### **How to See It**:

**Option A: Run the Script**
```bash
./scripts/compare_ground_truth.sh
```

**Option B: Run pytest Directly**
```bash
export ESTIMAI_SEED=42
export APR_USE_APRYSE=1
source backend/.venv/bin/activate
PYTHONPATH=. pytest backend/tests/test_ground_truth.py -v -s -m ground_truth
```

### **What You'll See**:
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
... [more checks]
================================================================================
Results: 16/16 checks passed
================================================================================

✅ All ground truth checks passed!
```

### **Files to Review**:
- `backend/tests/golden_reference.json` - Expected metrics
- `backend/tests/test_ground_truth.py` - Test implementation
- `scripts/compare_ground_truth.sh` - One-button runner
- `backend/app/core/llm.py` - Lines 47-65 (Seed injection)

---

## 🎬 Quick Start Demo

### **5-Minute Full Demo**:

```bash
# Terminal 1: Backend (already running)
# Check: curl http://localhost:8000/_healthz

# Terminal 2: Test Pipeline Transparency
curl -s "http://localhost:8000/v1/agent/takeoff" \
  -F "session_id=demo" \
  -F "file=@samples/bid_test.pdf" \
| jq '.summary.pipeline'

# Terminal 3: Run Ground Truth Test
./scripts/compare_ground_truth.sh

# Terminal 4: Start Frontend
cd frontend && npm run dev
# Then open http://localhost:5173/projects/demo
# Click "Verification" panel
```

---

## 📁 File Locations Summary

### **Backend API**
| Feature | File | Key Lines |
|---------|------|-----------|
| Pipeline Types | `backend/app/agent/types.py` | 85-133 |
| Pipeline Info | `backend/app/agent/takeoff_impl.py` | 416-468 |
| LLM Seed | `backend/app/core/llm.py` | 47-65 |
| Config | `backend/app/core/config.py` | 48-54 |

### **Frontend UI**
| Feature | File | Key Lines |
|---------|------|-----------|
| Verification Panel | `frontend/src/components/VerificationPanel.tsx` | Full file |
| Integration | `frontend/src/pages/ProjectPage.tsx` | 11, 209 |

### **Testing**
| Feature | File | Purpose |
|---------|------|---------|
| Golden Reference | `backend/tests/golden_reference.json` | Expected metrics |
| Ground Truth Test | `backend/tests/test_ground_truth.py` | Comparison tests |
| Runner Script | `scripts/compare_ground_truth.sh` | One-button validation |

### **Documentation**
| File | Content |
|------|---------|
| `TRANSPARENCY_IMPLEMENTATION.md` | Pipeline transparency guide |
| `DETERMINISTIC_TESTING.md` | Ground truth validation guide |
| `WHERE_TO_SEE_FEATURES.md` | This file! |

---

## 🐛 Troubleshooting

### "Backend not responding"
```bash
# Check if running
curl http://localhost:8000/_healthz

# If not, start it
cd backend && ./run_dev.sh
```

### "Frontend not loading"
```bash
# Check if running
curl http://localhost:5173

# If not, start it
cd frontend && npm run dev
```

### "Ground truth test fails"
```bash
# Ensure seed is set
export ESTIMAI_SEED=42

# Ensure golden PDF exists
ls -lh samples/280-utility-construction-plans.pdf

# Re-run test
./scripts/compare_ground_truth.sh
```

---

## 🎯 Next Steps

1. **Test Backend API**: Run the curl command above
2. **View Frontend Panel**: Start frontend and open demo project
3. **Run Ground Truth**: Execute `./scripts/compare_ground_truth.sh`
4. **Review Code**: Check the files listed in "File Locations"
5. **Read Docs**: See `DETERMINISTIC_TESTING.md` for full details

**All features are implemented and ready to use!** 🎉

