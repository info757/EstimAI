# NEXT_STEPS.md — EstimAI

This is your **living Kanban** inside the repo. Keep items bite-sized (aim for half-day or less). Each ticket has clear acceptance criteria and produces a commit.

---

## �� Active (Today)
- [x] Ticket: **Estimate Agent MVP**
  - [ ] Schema: `EstimateOutput` in `backend/app/models/schemas.py`
  - [ ] Service: `orchestrator.run_estimate(pid)`
  - [ ] API: `POST /projects/{pid}/agents/estimate`
  - [ ] Persist artifact under `backend/artifacts/{pid}/estimate/<timestamp>.json`
  - [ ] Tests: `backend/tests/test_estimate_endpoint.py` (happy + empty)
  - **Acceptance:** Returns valid schema; totals computed; artifacts created; tests pass.
## Ticket: Estimate Agent MVP
**Task:** Implement a new agent to generate costed estimates from takeoff + leveler outputs.  

**Why:** Contractors need not only extracted quantities, but actual costs and totals to prepare a bid.  

**Scope:**
- `backend/app/models/schemas.py`
  - Add `EstimateItem` + `EstimateOutput` Pydantic models.
- `backend/app/services/orchestrator.py`
  - Add `run_estimate(pid)` function.
  - Reads `takeoff` + `leveler` artifacts.
  - Looks up unit costs from `backend/app/data/costbook.json` (fallback if no uploaded costbook).
  - Computes line totals, subtotal, overhead, profit, total_bid.
- `backend/app/api/routes.py`
  - Add `POST /projects/{pid}/agents/estimate` endpoint.
  - Persists JSON artifact under `backend/artifacts/{pid}/estimate/<timestamp>.json`.
- `backend/tests/test_estimate_endpoint.py`
  - Happy path: at least 2 items with costs + totals computed correctly.
  - Empty path: no takeoff items → empty list, totals = 0.

**Acceptance:**
- Returns valid `EstimateOutput` JSON.
- Artifact is saved with timestamped filename in `/estimate/`.
- Tests pass (`pytest backend/tests/test_estimate_endpoint.py -q`).
- Logged to `ENGINEERING_LOG.md`.

**Notes:**
- Costbook format (example: `backend/app/data/costbook.json`):
  ```json
  {
    "Concrete Slab 3000psi": 8.50,
    "Structural Steel (ton)": 1200.00
  }

- [x] Ticket: **Tighten Leveler & Risk Prompts**
  - [ ] Enforce strict JSON contracts (no prose) in `prompts/leveler/system.md` and `prompts/risk/system.md`
  - [ ] Endpoint smoke tests validate JSON shape
  - **Acceptance:** `/agents/level` and `/agents/risk` return schema-valid payloads on sample PDFs (empty lists allowed).
  ## Ticket: Tighten Leveler & Risk Prompts
**Task:** Ensure Leveler and Risk agents always return strict, schema-valid JSON (arrays when empty, no prose).

**Why:** Keeps downstream (Estimate + Bid) stable. Prevents LLM “drift” into natural language that would break parsing.

**Scope:**
- `prompts/leveler/system.md`
  - Require top-level JSON array `[]`.
  - `normalized` must always be an array (use `[]` if empty).
- `prompts/risk/system.md`
  - Require top-level object with `"risks": []` when empty.
  - Enforce `0 ≤ probability ≤ 1`, impacts non-negative.
- `backend/tests/test_leveler_endpoint.py`
  - Smoke tests: endpoint returns JSON array, empty → `[]`.
- `backend/tests/test_risk_endpoint.py`
  - Smoke tests: endpoint returns JSON object with `"risks": []` when no risks.

**Acceptance:**
- `POST /api/projects/{pid}/agents/level` returns strictly `[]` or `[ ... ]`, no prose.
- `POST /api/projects/{pid}/agents/risk` returns strictly `{ "risks": [] }` or `{ "risks": [ ... ] }`, no prose.
- Tests pass (`pytest backend/tests/test_leveler_endpoint.py backend/tests/test_risk_endpoint.py -q`).
- ENGINEERING_LOG entry added.

**Notes:**
- Keep prompts concise + imperative (LLMs follow explicit constraints best).
- Example: `"Output: Return ONLY valid JSON that matches List[LevelingResult]. If no results, return []"`.
- Future: validation middleware could enforce schema, but prompt tightening is fastest path for MVP.

## 🟡 Next Up
- [X] Ticket: **Bid PDF Generator (v1)**
  - [ ] Service + endpoint: `POST /projects/{pid}/bid`
  - [ ] ReportLab template: cover, scope, estimate summary, risks, totals
  - [ ] Reads latest artifacts from `scope/`, `estimate/`, `risk/`
  - **Acceptance:** Returns a well-formed PDF; manual spot check includes all sections.
  ## Ticket: Bid PDF Generator (MVP)
**Task:** Generate a professional bid PDF combining Scope, Estimate, and Risks for a project.

**Why:** Contractors need a submission-ready package, not just JSON artifacts.

**Scope:**
- `backend/app/services/bid.py`  
  - `build_bid_pdf(pid: str) -> str`  // returns absolute path to created PDF
  - Load latest artifacts:
    - `artifacts/{pid}/scope/*.json` (ScopeOutput)
    - `artifacts/{pid}/estimate/*.json` (EstimateOutput)
    - `artifacts/{pid}/risk/*.json` (RiskOutput)
  - Render PDF with: Cover (project + date), Scope (bulleted), Estimate summary table (qty, unit, unit_cost, total), Risks (top 5), Totals.
  - Save under `artifacts/{pid}/bid/<timestamp>.pdf`.
- `backend/app/api/routes.py`
  - `POST /projects/{pid}/bid` → calls `build_bid_pdf` and returns `{ "project_id": pid, "pdf_path": "<...>" }`.
- `backend/app/templates/bid_template.py` (optional)
  - Keep ReportLab layout helpers separated (styles, table builder).
- `backend/tests/test_bid_pdf.py`
  - Creates tmp project with minimal artifacts.
  - Calls endpoint and asserts: 200, file exists, file size > 0.

**Acceptance:**
- Hitting `POST /api/projects/{pid}/bid` creates a PDF at `artifacts/{pid}/bid/<ts>.pdf`.
- PDF includes project header, scope section, estimate table (at least 2 rows if present), risks section, and total bid figure.
- Test `pytest backend/tests/test_bid_pdf.py -q` passes.

**Notes:**
- Use ReportLab (SimpleDocTemplate, Paragraph, Spacer, Table).
- If any artifact missing, render section header with “No data” and still produce a valid PDF.
- Currency formatting: `$1,234.56` (basic Python formatting is fine).


- [ ] Ticket: **Async Jobs + Polling**
  - [ ] `/ingest_async`, `/agents/*_async` using `BackgroundTasks`
  - [ ] `/jobs/{id}` status endpoint
  - **Acceptance:** Long operations return `job_id`, complete successfully, UI can poll.

## 🧰 Quality of Life
- [ ] Logging: time per agent, pid, and artifact path
- [ ] Health: `/healthz` returns ok, `/readyz` validates `ARTIFACT_DIR`
- [ ] CI: run `pytest -q` and lint on push

---

## ✅ Definition of Done (for any ticket)
- Tests pass for the new behavior.
- Code is committed with a clear, conventional message.
- A one-line entry is added to `ENGINEERING_LOG.md`.
- Docs updated if you changed prompts/schemas/endpoints.

---

## 🧾 Ticket Template (copy/paste)


---

## 🗂️ Backlog (parking lot)
- [ ] Frontend scaffold (Vite): upload, run agents, tables for outputs, bid export
- [ ] Costbook management: upload/override RSMeans with contractor pricing
- [ ] Versioning & compare: diff two estimates/bids
- [ ] Subcontractor quote ingestion & normalization

