# ENGINEERING_LOG.md — EstimAI

Use this log to capture decisions, changes, and path contracts. Append new entries at the top.

## Template
### YYYY-MM-DD
- **Context:**
- **Change:**
- **Endpoints touched:**
- **Artifacts shape/paths:**
- **Risks/Notes:**

---

## Entries

### 2025-09-01

**Context:** PR roadmap established; moving toward MVP with async pipeline and smoke tests.

**Change:** Added docs (README Dev Quickstart + Path Contracts), NEXT_STEPS.md; confirmed Makefile targets and .env.example.

**Endpoints touched:** N/A (docs only)

**Artifacts shape/paths:** Confirmed pdf_path contract => ${VITE_FILE_BASE}${pdf_path}

**Risks/Notes:** Ensure absolute ARTIFACT_DIR; verify CORS origin for Vite dev.

### 2025-09-02

**Context:** Added overrides layer (HITL scaffolding).

**Change:** backend/app/services/overrides.py with load/save/apply logic; pipeline now merges base ⊕ overrides if overrides exist.

**Endpoints touched:** N/A (no review API yet).

**Artifacts shape/paths:** new artifacts/{pid}/overrides/{stage}.json; reviewed_{stage}.json outputs.

**Risks/Notes:** versioning/merge conflicts; provenance fields important.

---

### 2025-09-01 16:00 — PR 8: HITL Overrides Layer

**Context:** Implemented lightweight overrides mechanism for human edits to pipeline outputs.

**Change:** Created backend/app/services/overrides.py with JSON patch format; integrated into orchestrator pipeline stages (takeoff, scope, estimate); updated bid service to use reviewed versions; added comprehensive tests.

**Endpoints touched:** N/A (backend service layer only)

**Artifacts shape/paths:** 
- artifacts/{pid}/overrides/overrides_{stage}.json (patch files)
- artifacts/{pid}/{stage}/reviewed.json (merged outputs)
- Provenance metadata: _override: {by, reason, at}

**Risks/Notes:** Overrides applied after each stage; bid PDF uses reviewed versions when available; 9/9 tests passing.

---

### 2025-09-01 14:00 — PR 6: Added smoke + lifecycle tests for /bid, /artifacts, /jobs endpoints; async polling with retries; 6/6 tests passing.

### 2025-08-27 16:20 — Completed Estimate Agent MVP; tests passing; artifacts persist.

### 2025-08-27 — Planned tickets: Estimate Agent MVP; Tighten Leveler & Risk; Bid PDF; Async Jobs.

### 2025-08-27 — Initialized NEXT_STEPS and ENGINEERING_LOG templates.

