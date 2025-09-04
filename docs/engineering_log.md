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

### 2025-09-03 — PR 19: Multi-format Parsing + OCR Stubs

**Context:** Added multi-format parsing pipeline with normalized doc model, OCR optional.

**Change:** 
- Created `backend/app/services/parsers.py` with comprehensive document parsing capabilities
- Added support for DOCX, XLSX, CSV, Image (OCR), and PDF (stub) file formats
- Implemented normalized document model with consistent JSON structure across all formats
- Enhanced `backend/app/core/config.py` with OCR configuration (OCR_ENABLED, OCR_LANG)
- Updated `backend/requirements.txt` with parsing dependencies (python-docx, openpyxl, pillow, pytesseract)
- Modified `backend/app/services/ingest.py` to integrate parsers and write normalized parsed JSON
- Created comprehensive test suite `backend/tests/test_parsers.py` for all parsing functionality
- Updated README.md with document parsing documentation and OCR configuration

**Endpoints touched:** none (ingestion routes unchanged)

**Artifacts shape/paths:** 
- Normalized parsed JSON now written to `artifacts/{pid}/ingest/parsed/...` with consistent structure
- Document model: `{ type, meta: {filename, content_hash, size}, content: { text, tables[] } }`
- Raw files remain in `artifacts/{pid}/ingest/raw/...` as before

**Risks/Notes:** 
- OCR gated by OCR_ENABLED and requires Tesseract on host/container
- PDF parsing still stub implementation (text extraction coming soon)
- All parsers gracefully handle missing dependencies with informative fallback messages
- Maintains backward compatibility with existing ingest workflow and manifest system
- Comprehensive test coverage with proper mocking for optional dependencies

### 2025-09-03 — PR 15: Auth Scaffolding

**Context:** Implement backend authentication helpers for JWT-based user authentication.

**Change:** 
- Added `backend/app/core/auth.py` with JWT token creation, decoding, and user authentication utilities
- Enhanced `backend/app/core/config.py` with JWT settings (JWT_SECRET, JWT_ALG, ACCESS_TOKEN_EXPIRE_MINUTES)
- Created `backend/requirements.txt` with PyJWT and other authentication dependencies
- Implemented comprehensive authentication functions: create_access_token, decode_token, get_current_user, authenticate_user
- Added OAuth2 Bearer token scheme with HTTPBearer dependency
- Included demo users for development/testing with configurable scopes
- Created comprehensive test suite `backend/tests/test_auth.py` for all authentication functions
- Added `backend/app/api/routes_auth.py` with POST /api/auth/login endpoint
- Protected all project endpoints with authentication: ingest, pipeline_async, pipeline_sync, agents/*, bid, artifacts, review/*
- Protected job endpoints with authentication: GET /api/jobs/{id}, GET /api/jobs
- Health endpoint remains public for monitoring
- Created comprehensive test suite `backend/tests/test_auth_routes.py` for authentication routes

**Endpoints touched:** 
- POST /api/auth/login (new)
- All /api/projects/{pid}/* endpoints (now require authentication)
- All /api/jobs/* endpoints (now require authentication)
- GET /health (remains public)

**Artifacts shape/paths:** N/A

**Risks/Notes:** 
- JWT_SECRET defaults to "dev-secret" in development (must be set in production)
- Uses PyJWT for lightweight JWT handling
- Demo users included for development/testing purposes
- All timestamps use UTC timezone for consistency
- Comprehensive error handling with proper HTTP status codes
- FastAPI returns 403 Forbidden for missing authentication (correct behavior)
- OpenAPI documentation automatically shows security requirements for protected endpoints

### 2025-09-02 — PR 14: SQLite Job Store

**Context:** Move job records from disk JSON to SQLite for robustness.

**Change:** 
- Added `backend/app/services/db.py` with SQLite database layer for job persistence
- Jobs now persisted in `ARTIFACT_DIR/jobs.db` instead of individual JSON files
- Updated `backend/app/services/jobs.py` to use database operations instead of file I/O
- Modified `backend/app/api/routes_jobs.py` and `backend/app/api/routes_projects.py` to read from database
- Added `backend/app/core/paths.py` with `jobs_db_path()` helper function
- Created comprehensive test suite `backend/tests/test_jobs_sqlite.py` for database-backed job lifecycle
- Added optional migration script `scripts/migrate_jobs_disk_to_sqlite.py` for legacy JSON job files
- Updated README.md with migration instructions

**Endpoints touched:** 
- GET /api/jobs/{id} (no contract change)
- POST /api/projects/{pid}/pipeline_async (no contract change)

**Artifacts shape/paths:** 
- Job records now stored in SQLite database at `ARTIFACT_DIR/jobs.db`
- Database schema: `jobs` table with columns `id`, `pid`, `status`, `created_at`, `updated_at`, `result_json`, `error_text`
- Legacy JSON job files can be migrated using the migration script

**Risks/Notes:** 
- Database uses WAL mode for improved concurrency and durability
- All timestamps stored as ISO8601 UTC strings
- Optional migration script for legacy JSON job files (safe to run multiple times)
- Maintains 100% backward compatibility with existing API contracts
- Smart field separation: file paths go to `artifacts`, complex data goes to `meta`

### 2025-09-03 — PR 13: Health Endpoint + Structured JSON Logging

**Context:** Health endpoint and structured JSON logs for observability.

**Change:** 
- Added GET /health with uptime/version; JSON logs for requests and job transitions; optional COMMIT_SHA support
- Created `backend/app/core/logging.py` with JSONFormatter, request context tracking, and job transition logging
- Enhanced `backend/app/main.py` with LoggingMiddleware for request timing and structured logging
- Updated `backend/app/services/jobs.py` and `backend/app/services/orchestrator.py` with structured logging
- Added COMMIT_SHA environment variable support in `backend/app/core/runtime.py`
- Updated `docker-compose.yml` and Dockerfiles to pass COMMIT_SHA from environment
- Enhanced Makefile with COMMIT_SHA-aware Docker build commands

**Endpoints touched:** GET /health

**Artifacts shape/paths:** Logs now include structured context for debugging and monitoring

**Risks/Notes:** 
- Keep logs single-line JSON; include duration_ms for latency tracking
- Single-line JSON logs for production log aggregation systems
- Request context tracking works across async operations
- COMMIT_SHA falls back to "dev" if not set
- Docker builds automatically include current git commit SHA

### 2025-09-02 — PR 12: Dockerization

**Context:** Containerized backend and frontend; added compose for local/prod-like runs.

**Change:** Dockerfile.backend, Dockerfile.frontend, ops/nginx/frontend.conf, docker-compose.yml, .dockerignore files; Makefile docker targets; README Docker section.

**Endpoints touched:** N/A

**Artifacts:** bind-mounted at ./backend/artifacts <-> /app/backend/artifacts

**Risks/Notes:** Frontend served at :8080; backend CORS includes http://localhost:8080

### 2025-09-02 — PR 11: CI/CD

**Context:** Added GitHub Actions CI to enforce tests/lint and build frontend.

**Change:** .github/workflows/ci.yml runs on push/PR to main; Makefile lint/test targets confirmed; README CI badge added.

**Endpoints touched:** N/A

**Artifacts:** CI writes to ARTIFACT_DIR=${{ github.workspace }}/artifacts-ci (uploaded as artifact).

**Risks/Notes:** Ensure tests don't depend on network/ports; keep ARTIFACT_DIR absolute in local .env; badge URL needs repo path after first push.

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

### 2025-09-02 17:00 — PR 9: Review Endpoints

**Context:** Exposed review endpoints for HITL.

**Change:** Added GET/PATCH /review/takeoff and /review/estimate; models in models/review.py; integrated overrides service.

**Endpoints touched:**
- GET/PATCH /api/projects/{pid}/review/takeoff
- GET/PATCH /api/projects/{pid}/review/estimate

**Artifacts shape/paths:** overrides remain in artifacts/{pid}/overrides/*.json; merged views returned by API, not persisted unless pipeline re-runs.

**Risks/Notes:** Row id stability is required across runs; ensure id assignment is deterministic in upstream stages.

### 2025-09-02 18:00 — PR 9 Enhancement: OpenAPI Examples

**Context:** Enriched review endpoints with comprehensive OpenAPI examples and documentation.

**Change:** Added json_schema_extra examples to all Pydantic models; enhanced endpoint docstrings with override behavior documentation; documented "last write wins" and provenance tracking.

**Endpoints touched:** Same as PR 9 (enhancement only)

**Artifacts shape/paths:** Enhanced examples showing:
- ReviewResponse with 2 rows (one with override, one without)
- PatchRequest with realistic patch example
- Confidence scores and provenance fields

**Risks/Notes:** 10/10 tests still passing; OpenAPI schema validates correctly.

### 2025-09-02 19:00 — PR 9 Add-on: Review Roundtrip Tests

**Context:** Added minimal pytest for review endpoint roundtrip functionality.

**Change:** Created tests/test_review_roundtrip.py with full GET -> PATCH -> GET flow testing; mocked pipeline services for controlled testing; verified override application and merged results.

**Endpoints touched:** Same as PR 9 (test coverage only)

**Artifacts shape/paths:** Test fixtures with realistic data:
- takeoff: qty changes (100 -> 150)
- estimate: unit_cost changes (45.0 -> 55.0, 120.0 -> 130.0) + profit_pct

**Risks/Notes:** 12/12 review tests passing; roundtrip tests verify full override workflow.

### 2025-09-02 20:00 — PR 10: Frontend Review UI API Client

**Context:** Added frontend API client methods for review endpoints and pipeline sync.

**Change:** Extended frontend/src/types/api.ts with ReviewRow, ReviewResponse, Patch, PatchResponse types; added getTakeoffReview, patchTakeoffReview, getEstimateReview, patchEstimateReview methods; exported pipelineSync and fileUrl functions.

**Endpoints touched:** Frontend API client integration (no new backend endpoints)

**Artifacts shape/paths:** TypeScript types matching backend ReviewResponse structure; fileUrl helper for constructing browser-openable URLs.

**Risks/Notes:** TypeScript compilation verified; all types properly exported; ready for React component integration.

### 2025-09-02 21:00 — PR 10: Frontend Review UI Pages & Routes

**Context:** Implemented React pages and routing for review UI with editable tables and override management.

**Change:** Created ReviewTakeoffPage and ReviewEstimatePage with editable tables, dirty state tracking, and API integration; added routes /projects/:pid/review/takeoff and /projects/:pid/review/estimate; added navigation links to ProjectPage.

**Endpoints touched:** Frontend routing and UI components (no new backend endpoints)

**Artifacts shape/paths:** Editable table UI showing AI values, user values, confidence, and diffs; dirty state tracking for changed fields; patch computation for API calls.

**Risks/Notes:** TypeScript compilation verified; ready for user testing; navigation links added to ProjectPage for easy access.

### 2025-09-02 22:00 — PR 10 Enhancement: Reusable ReviewTable Component

**Context:** Refactored review pages to use a shared, reusable table component for better maintainability and consistency.

**Change:** Created frontend/src/components/ReviewTable.tsx with configurable editable keys, confidence display, and diff calculation; updated both ReviewTakeoffPage and ReviewEstimatePage to use the component; removed duplicate table logic.

**Endpoints touched:** Frontend UI components only (no backend changes)

**Artifacts shape/paths:** ReviewTable component with props for rows, editableKeys, onChange handler, optional getDiff function, and confidenceKey; consistent UI across takeoff and estimate review pages.

**Risks/Notes:** Component is "dumb" - parent pages manage state; editable keys are configurable per page type; confidence display with color coding (green/yellow/red based on threshold).

### 2025-09-02 23:00 — PR 10 Refactor: ReviewTakeoffPage State Management

**Context:** Simplified ReviewTakeoffPage state management to work seamlessly with ReviewTable component.

**Change:** Refactored state from complex EditableRow interface to simple edited Record; implemented onChange handler, buildPatches, saveOverrides, and handleRecalc functions; updated ReviewTable to accept editedValues prop for real-time editing feedback.

**Endpoints touched:** Frontend UI components only (no backend changes)

**Artifacts shape/paths:** Simplified state: {id: {key: value}} for tracking edits; ReviewTable now shows edited values in inputs and highlights changed cells; clean separation between data fetching and editing state.

**Risks/Notes:** TypeScript compilation verified; state management simplified from ~100 lines to ~50 lines; ReviewTable component enhanced to handle both merged and edited values.

### 2025-09-02 24:00 — PR 10 Complete: ReviewEstimatePage Refactoring

**Context:** Completed ReviewEstimatePage refactoring to match ReviewTakeoffPage structure and use ReviewTable component.

**Change:** Refactored ReviewEstimatePage with same state management pattern; implemented estimate-specific editableKeys ["unit_cost", "overhead", "profit", "contingency"]; added custom diff calculation and totals summary section; integrated with ReviewTable component.

**Endpoints touched:** Frontend UI components only (no backend changes)

**Artifacts shape/paths:** Estimate-specific editable fields; totals calculation for qty × unit_cost with AI vs edited comparison; custom diff function for numeric fields; totals summary section showing financial impact of changes.

**Risks/Notes:** TypeScript compilation verified; both review pages now use consistent architecture; totals calculation provides business value insight for estimate changes.

### 2025-09-02 25:00 — PR 10 Navigation: ProjectPage Review Section

**Context:** Added dedicated Review section to ProjectPage for easy access to review screens.

**Change:** Reorganized ProjectPage layout to separate main actions from review actions; created dedicated "Review" section with "Review Quantities" (takeoff) and "Review Pricing" (estimate) buttons; maintained existing "Generate Bid PDF" and "Run Full Pipeline" buttons.

**Endpoints touched:** Frontend UI layout only (no backend changes)

**Artifacts shape/paths:** Clear separation between pipeline actions and review actions; intuitive navigation flow from project overview to specific review screens; consistent button styling and hover effects.

**Risks/Notes:** TypeScript compilation verified; improved user experience with logical grouping of related actions; review buttons now have descriptive labels ("Quantities" vs "Pricing").

### 2025-09-02 26:00 — PR 10 Toast System: Minimal Notification System

**Context:** Implemented minimal toast notification system to replace alerts in review pages.

**Change:** Created Toast component with support for links and types; implemented ToastContext with useToast hook; wrapped app with ToastProvider; updated both review pages to use toast() instead of alert().

**Endpoints touched:** Frontend UI components only (no backend changes)

**Artifacts shape/paths:** Toast component with options: { link?, label?, type? }; ToastContext with auto-dismiss after 5 seconds; useToast() hook for easy integration; success/error/info types with color coding.

**Risks/Notes:** TypeScript compilation verified; toast system provides better UX than alerts; auto-dismiss prevents notification clutter; link support enables direct PDF access from success messages.

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

