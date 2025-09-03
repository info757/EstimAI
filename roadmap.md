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
- [x ] `GET /api/projects/{pid}/review/takeoff` returns merged rows (with AI + overrides + confidence).  
- [x ] `PATCH /api/projects/{pid}/review/takeoff` upserts overrides.  
- [x ] `GET /api/projects/{pid}/review/estimate` returns merged cost table.  
- [x ] `PATCH /api/projects/{pid}/review/estimate` allows editing unit_cost, markups.  

---

## PR 10 — Frontend Review UI
**Goal**: Add minimal tables for human judgment.  
**Acceptance Criteria**
- [ ] **Takeoff review table**: editable qty/unit/desc/cost-code with confidence highlights.  
- [ ] **Estimate review table**: editable unit costs, overhead, profit, contingency.  
- [ ] Save overrides via PATCH endpoints.  
- [ ] Recalculate + “Continue Pipeline” button resumes job.  
- [ ] Bid PDF generated from reviewed state.  

**Acceptance checks:**
- From `/projects/:pid`, I can click:
  • Review Quantities → edit qty/unit/desc/cost-code; Save overrides; Recalculate → navigates back; new PDF link appears in artifacts.
  • Review Pricing → edit unit_cost/overhead/profit/contingency; Save overrides; Recalculate → navigates back; new PDF link appears.
- After Save, GET `/review/*` reflects merged changes; override block populated for edited rows.
- Recalculate calls `pipelineSync` and returns a browser-openable `pdf_path`; toast includes an "Open PDF" link using `VITE_FILE_BASE`.
- Buttons show proper disabled/loading states; errors show a toast.

---

## Definition of Done (MVP)
- From clean start: upload → run full pipeline (async) → artifacts update.  
- Generate Bid PDF works; all artifact links 200.  
- Two backend tests pass (bid smoke + job lifecycle).  
- Docs updated; startup prints mounted artifacts path.  


---

# EstimAI — PR 11 to 20 (Productionization + Dynamic Ingestion)

## PR 11 — CI/CD Pipeline (GitHub Actions)
**Goal**: Ensure every commit runs tests, lint, and build.  
**Acceptance Criteria**
- [x ] `.github/workflows/ci.yml` runs on push + PR to `main`.
- [x ] Matrix: Python 3.11, Node 18.
- [x ] Steps: checkout → install deps → lint → `make test` → frontend build.
- [x ] CI uses temporary `ARTIFACT_DIR`.
- [x ] Badge added to README.

---

## PR 12 — Dockerization
**Goal**: Containerize backend + frontend.  
**Acceptance Criteria**
- [x ] `Dockerfile.backend` (uvicorn app).  
- [x ] `Dockerfile.frontend` (Vite build → nginx).  
- [x ] `docker-compose.yml` with backend + frontend + artifacts volume.  
- [x ] `make docker-up` starts full stack.  

---

### Acceptance checks (paste these into your PR description)
- [x ] `docker compose up -d --build` starts **backend:8000** and **frontend:8080**.
- [x ] `curl http://localhost:8000/health` → `{ "status": "ok" }`.
- [x ] Frontend loads at `http://localhost:8080` and can hit the backend (CORS ok).
- [x ] Generating a bid creates a PDF under `./backend/artifacts/...` and it opens via `http://localhost:8000${pdf_path}`.
- [x ] Restarting containers preserves artifacts (bind mount works).

---



---

---

### Acceptance checks (copy into PR 13 description)
- [x ] `GET /health` returns `{ status: "ok", uptime_seconds, version }`.
- [x ] Request logs emit **single-line JSON** with path/method/status/duration_ms.
- [x ] Job transitions emit JSON logs with job_id, pid, from→to, success/error.
- [x ] README documents health & logs.
- [x ] (Optional) tests for `/health` pass locally & in CI.

---





---

## PR 14 — Persistence Upgrade (SQLite Job Store)
**Goal**: Replace disk JSON job records with SQLite.  
**Acceptance Criteria**
- [x ] SQLite DB at `ARTIFACT_DIR/jobs.db`.  
- [x ] Table: jobs (id, pid, status, created_at, updated_at, result_json, error_text).  
- [x ] Job endpoints unchanged.  
- [x ] Tests confirm job lifecycle in DB.  

---


---

## PR 16 — Frontend Upload UI
**Goal**: User can upload documents via UI.  
**Acceptance Criteria**
- [ ] Drag-drop uploader on `/projects/:pid`.  
- [ ] Progress bar, multiple files, type validation (PDF, CSV, XLSX, DOCX).  
- [ ] Calls `POST /ingest` and shows ingest results.  
- [ ] Artifacts update automatically.  

---

## PR 17 — Ingestion Worker (Async)
**Goal**: Make ingestion job-based.  
**Acceptance Criteria**
- [ ] `POST /pipeline_async` pattern applied to ingestion.  
- [ ] Large files chunked/streamed.  
- [ ] Status tracked in jobs table.  
- [ ] Ingestion artifacts saved under `artifacts/{pid}/ingest/`.  

---

## PR 18 — Re-ingest & Manifest
**Goal**: Track ingested files and prevent duplicates.  
**Acceptance Criteria**
- [ ] `ingest_manifest.json` per project with `{ filename, content_hash, indexed_at }`.  
- [ ] Duplicate uploads skipped unless hash changes.  
- [ ] New endpoint `GET /api/projects/{pid}/ingest` lists ingested sources.  

---

## PR 19 — Content Types & OCR
**Goal**: Expand ingestion beyond PDFs.  
**Acceptance Criteria**
- [ ] Support parsing DOCX, XLSX, CSV.  
- [ ] OCR images into text (if OCR lib available).  
- [ ] Normalize outputs into a consistent doc model.  
- [ ] Store parsed JSON next to raw file.  

---

## PR 20 — External Sources (Optional)
**Goal**: Enable ingestion from external connectors.  
**Acceptance Criteria**
- [ ] Add support for S3 or cloud storage as ingestion source.  
- [ ] Optional connectors for SharePoint/Drive (stubbed initially).  
- [ ] “Sync now” endpoint + async job.  
- [ ] Artifacts + manifest updated with external sources.  

---

# Definition of Done (PR 11–20)
- CI pipeline green on every push.  
- App runs via `docker-compose up`.  
- `/health` works and logs structured.  
- Jobs persist in SQLite.  
- JWT auth prototype works in frontend.  
- Users can upload and re-ingest documents dynamically.  
- Manifest prevents duplicate indexing.  
- Ingestion expanded to multiple file types.  
- External connectors scaffolding in place (future).  
