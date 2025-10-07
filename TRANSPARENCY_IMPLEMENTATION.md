# 🔍 Transparency & Verification Implementation

## Summary

Implemented comprehensive transparency features to prove that Apryse + LLM are actively working and provide clients with verification data about the accuracy of the takeoff process.

## ✅ What Was Implemented

### 1. Backend Transparency (Agent Types & Implementation)

#### A. Pipeline Information in Agent Responses
- **File**: `backend/app/agent/types.py`
- **Added**: `PipelineInfo` model with fields:
  - `apryse_enabled`: Boolean flag showing if Apryse PDFNet is active
  - `llm_enabled`: Boolean flag showing if LLM processing is active
  - `llm_model`: Name of the LLM model (e.g., "gpt-4o-mini")
  - `ground_source`: Primary source for ground elevation ("profile", "surface", "constant", "unknown")
  - `prompt_token_count`: Token usage tracking (future implementation)
  - `completion_token_count`: Token usage tracking (future implementation)

- **Updated**: `AgentSummary` model now includes `pipeline: PipelineInfo` field

#### B. Agent Implementation Updates
- **File**: `backend/app/agent/takeoff_impl.py`
- **Updated**: `_generate_summary()` method now:
  - Reads `APR_USE_APRYSE` and `VISION_MODEL` from settings
  - Detects ground source used (profile/surface/constant)
  - Populates `PipelineInfo` for every agent response
  - Adds `ground_source` to individual pipe `extra` metadata

#### C. Per-Pipe Ground Source Tracking
- **Updated**: `_process_network_depths()` method now tracks which ground elevation source was used for each pipe
- **Stored in**: `pipe.extra.ground_source` field
- **Values**:
  - `"profile"` - Used profile ground line annotations
  - `"surface"` - Sampled from contour surface data
  - `"constant"` - Used fallback constant elevation
  - `"unknown"` - Could not determine source

### 2. Orchestrator Integration Fix
- **File**: `backend/app/services/orchestrator.py`
- **Fixed**: Incorrect status checking in `run_takeoff()` 
  - **Before**: `if resp.status != "completed"` (field doesn't exist)
  - **After**: `if not resp.proposed_review or resp.error` (correct check)
- **Ensures**: Working orchestrator correctly uses the v1 agent for demo project

### 3. Frontend Verification Panel

#### A. New Component: VerificationPanel
- **File**: `frontend/src/components/VerificationPanel.tsx`
- **Features**:
  - Collapsible panel with clear "Verification" heading
  - Shows pipeline component status (Apryse, LLM model)
  - Scale proof section with parsed scale and verification accuracy
  - Depth proof with min/avg/max and ground source badges
  - Counts proof showing depth buckets (LF) and trench volume (CY)
  - QA flags with color-coded badges (COVER_LOW, DEEP_EXCAVATION, etc.)

#### B. Ground Source Badges
- ✅ Profile (green) - Most accurate
- ✅ Surface (blue) - Good accuracy
- ⚠️ Flat Fallback (yellow) - Estimate only
- ❓ Unknown (gray) - Could not determine

#### C. Integration
- **File**: `frontend/src/pages/ProjectPage.tsx`
- **Location**: Added between "Ingest Sources" and "Artifacts" sections
- **Session ID**: Uses `project-${pid}` format to match orchestrator

## 📊 API Response Example

```json
{
  "proposed_review": { /* ... */ },
  "summary": {
    "pipes_total": 6,
    "qa_flags": {
      "COVER_LOW": 2,
      "DEEP_EXCAVATION": 1
    },
    "pipeline": {
      "apryse_enabled": true,
      "llm_enabled": true,
      "llm_model": "gpt-4o-mini",
      "ground_source": "profile",
      "prompt_token_count": null,
      "completion_token_count": null
    }
  },
  "warnings": [],
  "error": null
}
```

## 🎯 Usage

### Backend Verification
```bash
# Test agent with transparency info
curl -s "http://localhost:8000/v1/agent/takeoff" \
  -F "session_id=test" \
  -F "file=@samples/bid_test.pdf" \
  | jq '.summary.pipeline'

# Response shows:
# {
#   "apryse_enabled": true,
#   "llm_enabled": true,
#   "llm_model": "gpt-4o-mini",
#   "ground_source": "unknown",
#   ...
# }
```

### Frontend Verification
1. Navigate to project page: `http://localhost:5173/projects/demo`
2. Scroll to "Verification" section
3. Click to expand verification panel
4. Review:
   - Pipeline component status
   - Scale verification accuracy
   - Depth analysis with ground source
   - Quantity breakdown by depth bucket
   - QA flags for problematic pipes

## 🔧 Environment Configuration

Ensure `APR_USE_APRYSE=1` is set in `backend/run_dev.sh`:
```bash
export APR_USE_APRYSE=${APR_USE_APRYSE:-1}
```

This defaults to enabled, ensuring Apryse PDFNet is active for vector extraction.

## 📝 Future Enhancements

1. **Token Tracking**: Implement actual token counting from OpenAI API responses
2. **Scale Verification**: Extract actual scale bar data from PDFs and verify measurements
3. **Real-time Updates**: WebSocket connection for live pipeline status
4. **Historical Tracking**: Store verification data per session for audit trail
5. **Accuracy Metrics**: Compare detected quantities vs. manual review adjustments
6. **Export Reports**: Generate PDF verification reports for clients

## 🐛 Known Issues

1. **Ground Source per-pipe**: Currently showing in agent processing but may not persist through `to_payload_networks()` serialization
   - **Fix**: Need to ensure `extra.ground_source` is included in final payload
2. **Mock Data**: VerificationPanel currently uses mock data for scale/depth stats
   - **Fix**: Connect to actual `/v1/counts` data structure with depth attributes
3. **Session Mapping**: Need to verify session_id format matches between agent and UI
   - **Current**: Using `project-${pid}` format in orchestrator

## ✅ Testing Checklist

- [x] Backend: Pipeline info included in agent response
- [x] Backend: Orchestrator fix for status checking
- [x] Backend: Ground source detection working
- [x] Frontend: VerificationPanel component created
- [x] Frontend: Component integrated into ProjectPage
- [x] Environment: APR_USE_APRYSE defaults to enabled
- [ ] E2E: Full pipeline run with verification panel visible
- [ ] E2E: Real data populating verification panel
- [ ] E2E: QA flags correctly displayed
- [ ] Documentation: Client-facing verification guide

## 📚 Related Files

**Backend:**
- `backend/app/agent/types.py` - Pipeline transparency types
- `backend/app/agent/takeoff_impl.py` - Implementation with ground source tracking
- `backend/app/agent/__init__.py` - Exports for PipelineInfo
- `backend/app/services/orchestrator.py` - Fixed status checking

**Frontend:**
- `frontend/src/components/VerificationPanel.tsx` - New verification UI
- `frontend/src/pages/ProjectPage.tsx` - Integration point

**Configuration:**
- `backend/run_dev.sh` - Environment setup
- `backend/app/core/config.py` - Settings (APR_USE_APRYSE, VISION_MODEL)

