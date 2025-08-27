# CONTEXT.md — EstimAI

## Goal
EstimAI is an AI-powered estimating assistant for contractors.  
It turns drawings + specs into a professional bid package ready to submit.

## Flow
Upload PDFs → Ingest → Agents (takeoff, scope, leveler, risk, estimate) → Bid PDF.

## Current State (v0.2)
- ✅ Ingest working (sheet_index.json, spec_index.json).
- ✅ Takeoff + Scope agents produce schema-valid JSON.
- ✅ Artifacts saved under backend/artifacts/{pid}.
- ✅ Docs/NEXT_STEPS + ENGINEERING_LOG started.
- ⏳ Tighten Leveler + Risk.
- ⏳ Add Estimate Agent + Bid PDF.
- 🚧 Frontend scaffold not started.

## Next Milestones
- Implement Estimate Agent MVP.
- Implement Bid PDF generator.
- Add async job pattern to avoid blocking.
- Scaffold frontend (Vite/React).

## Key Paths
- backend/app/api/routes.py
- backend/app/services/orchestrator.py
- backend/app/models/schemas.py
- prompts/<agent>/system.md
- backend/artifacts/{pid}/<agent>/

