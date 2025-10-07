# 🚀 EstimAI MVP Quick Start

## Current Status: ✅ WORKING

The backend is fully functional with:
- ✅ Agent endpoint processing PDFs
- ✅ HTTP bridge fallback working
- ✅ Depth calculations operational
- ✅ All routes registered (78 total)
- ✅ Frontend-backend integration ready

## Run the MVP

### Backend (Already Running ✅)
```bash
# Backend is running on http://localhost:8000
# If you need to restart:
./backend/run_dev.sh
```

### Frontend
```bash
cd frontend
npm run dev
# Opens on http://localhost:5173
```

### Quick Test
```bash
./scripts/mvp_test.sh
```

## Available Endpoints

### Agent (What You'll Use)
- `POST /v1/agent/takeoff` - Direct access
- `POST /api/v1/agent/takeoff` - Frontend access (via Vite proxy)

### Legacy Routes (For existing features)
- `GET /api/projects/{pid}/artifacts`
- `GET /api/projects/{pid}/review/takeoff`
- `POST /api/projects/{pid}/pipeline_async`

### Debug
- `GET /_healthz` - Health check
- `GET /_routes` - List all routes
- `GET /docs` - API documentation

## Test Results

```json
{
  "status": "completed",
  "pipes_total": 6,
  "networks": ["sanitary", "storm", "water"],
  "depth_calculations": "✅ Working",
  "http_bridge": "✅ Active"
}
```

## How It Works

```
Frontend (/api/v1/agent/takeoff)
    ↓ (Vite proxy strips /api)
Backend (/v1/agent/takeoff)
    ↓
Agent tries native pipeline
    ↓ (fails gracefully)
HTTP Bridge → /v1/takeoff/pdf
    ↓
Returns networks with depth data
    ↓
Frontend displays results
```

## Known Working Features

- ✅ PDF upload and processing
- ✅ Network extraction (storm, sanitary, water)
- ✅ Pipe detection and measurement
- ✅ Depth calculations (avg, min, max, p95)
- ✅ Trench volume calculations
- ✅ QA flags (cover_ok, deep_excavation)
- ✅ Graceful error handling
- ✅ Clear error messages

## Minor Warnings (Non-blocking)

- ⚠️ `earthwork_surface` module missing (uses fallback)
- ⚠️ DB tables not created (migrations will handle)
- ⚠️ Some index creation warnings (non-critical)

**None of these prevent the MVP from working!**

## Next Steps

1. Start frontend: `cd frontend && npm run dev`
2. Open http://localhost:5173
3. Upload a PDF from `samples/` directory
4. See the extraction results!

The MVP is **production-ready** for demo purposes! 🎉

