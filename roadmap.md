# EstimAI — PR Roadmap (with Acceptance Criteria)

This file tracks the sequence of PRs to build the EstimAI MVP and post-MVP (HITL) features. Copy relevant sections into GitHub Issues/PRs as needed.

---

## PR 1 — API Contract & Path Contracts
**Goal**: Freeze endpoint names and path behaviors.  
**Acceptance Criteria**
- [x ] Endpoints exposed in FastAPI with OpenAPI docs:  
  - `POST /api/projects/{pid}/ingest`  
  - `POST /api/projects/{pid}/pipeline_sync`  
  - `POST /api/projects/{pid}/pipeline_async`  
  - `GET /api/jobs/{id}`  
  - `GET /api/projects/{pid}/artifacts`  
  - `POST (or GET) /api/projects/{pid}/bid`  
- [ x] All responses return **browser-openable `pdf_path`** values.  
- [ x] CORS configured to allow Vite dev origin.  

---

## PR 2 — Sync Pipeline Orchestration
**Goal**: Run all agents sequentially in one request.  
**Acceptance Criteria**
- [X] Pipeline chains: takeoff → scope → leveler → risk → estimate → bid.  
- [x] Stage outputs persisted to `artifacts/{pid}/{stage}/…`.  
- [X] Returns `{ summary, pdf_path }` in response.  
- [x] Stage-by-stage logging visible in backend logs.  

---

## PR 3 — Minimal Async Jobs
**Goal**: Allow background job execution with polling.  
**Acceptance Criteria**
- [X] Jobs stored on disk `{ id, pid, status, result?, error? }`.  
- [X] `POST /pipeline_async` enqueues a job, returns `{ job_id }`.  
- [X] `GET /jobs/{id}` reflects correct status transitions.  
- [X] On success, includes `{ summary, pdf_path }`.  
- [X] On failure, captures and persists traceback message.  

---

## PR 4 — Frontend Async UX
**Goal**: Add UI to run pipeline asynchronously and track status.  
**Acceptance Criteria**
- [X] Project page shows **Generate Bid PDF** and **Run Full Pipeline**.  
- [X] Clicking **Run Full Pipeline** → calls `pipeline_async`, starts polling `GET /jobs/{id}`.  
- [X] On success → toast “Pipeline completed” + artifacts auto-refresh.  
- [X] On failure → toast with error message.  
- [X] Artifacts list always renders working download links.  

---

## PR 5 — Stability & DX Guardrails
**Goal**: Make local dev reliable and predictable.  
**Acceptance Criteria**
- [x] `.env.example` includes pinned `ARTIFACT_DIR` (absolute path recommended).  
- [x] One backend start command (`make dev`).  
- [x ] Startup logs print: `"/artifacts mounted at: <abs path>"`.  
- [x ] Frontend docs list correct `VITE_API_BASE` and `VITE_FILE_BASE`.  

---

## PR 6 — Tests (Smoke + Lifecycle)
**Goal**: Add minimal backend tests for confidence.  
**Acceptance Criteria**
- [x ] **Bid smoke test**:  
  - Call `/bid`, fetch returned `pdf_path`, assert `200` and `Content-Type: application/pdf`.  
- [x ] **Artifacts mount test**:  
  - Place sentinel file in artifacts, assert `GET /artifacts` lists it and direct GET works.  
- [x ] **Job lifecycle test**:  
  - Call `/pipeline_async`, poll until `succeeded`, confirm returned `pdf_path` serves 200 and appears in artifacts.  

---

## PR 7 — Docs
**Goal**: Ensure new devs can start in minutes.  
**Acceptance Criteria**
- [x] **Dev Quickstart** in README: clone → copy `.env.example` → start backend/frontend.  
- [x ] **NEXT_STEPS.md** updated with post-MVP priorities.  
- [x ] **ENGINEERING_LOG.md** includes today’s decisions and path contracts.  

---

## PR 8 — HITL Overrides Layer
**Goal**: Add scaffolding for human-in-the-loop review.  
**Acceptance Criteria**
- [x ] New directory `artifacts/{pid}/overrides/` created per project.  
- [x ] Overrides JSON format defined (row-level patches `{ id, fields…, by, reason }`).  
- [x ] Merged views = base ⊕ overrides, used when available.  
- [x ] `bid` endpoint generates from reviewed state if overrides exist.  

---

## PR 9 — Review Endpoints
**Goal**: Expose review data to the frontend.  
**Acceptance Criteria**
- [ ] `GET /api/projects/{pid}/review/takeoff` returns merged rows (with AI + overrides + confidence).  
- [ ] `PATCH /api/projects/{pid}/review/takeoff` upserts overrides.  
- [ ] `GET /api/projects/{pid}/review/estimate` returns merged cost table.  
- [ ] `PATCH /api/projects/{pid}/review/estimate` allows editing unit_cost, markups.  

---

## PR 10 — Frontend Review UI
**Goal**: Add minimal tables for human judgment.  
**Acceptance Criteria**
- [ ] **Takeoff review table**: editable qty/unit/desc/cost-code with confidence highlights.  
- [ ] **Estimate review table**: editable unit costs, overhead, profit, contingency.  
- [ ] Save overrides via PATCH endpoints.  
- [ ] Recalculate + “Continue Pipeline” button resumes job.  
- [ ] Bid PDF generated from reviewed state.  

---

## Definition of Done (MVP)
- From clean start: upload → run full pipeline (async) → artifacts update.  
- Generate Bid PDF works; all artifact links 200.  
- Two backend tests pass (bid smoke + job lifecycle).  
- Docs updated; startup prints mounted artifacts path.  
