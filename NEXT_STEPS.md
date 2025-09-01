# NEXT_STEPS — Post-MVP Priorities

## 1) Human-in-the-Loop (HITL)

**Overrides layer at artifacts/{pid}/overrides/**

**Review endpoints:**
- `GET/PATCH /api/projects/{pid}/review/takeoff`
- `GET/PATCH /api/projects/{pid}/review/estimate`

**Frontend review tables:**
- Takeoff: qty/unit/cost-code
- Estimate: unit costs, overhead/profit/contingency

**Optional:** pipeline pause/resume with status `waiting_for_review`

## 2) Observability

**Per-stage timings and job spans in logs**

**Basic error analytics:**
- Top tracebacks
- Error frequency tracking

**Request IDs / Job IDs in all logs**

## 3) Reliability / DX

**Atomic writes for artifacts & jobs:**
- temp → rename pattern
- "latest.json" / "latest.pdf" pointer for each stage

**Makefile improvements:**
- build/watch tasks
- pre-commit hooks (ruff/black)

## 4) Security / Auth (later)

**Single-user dev now; plan JWT or session auth later**

**Private artifacts directory when deployed**

## 5) Persistence & Scale

**Consider migrating jobs store from disk to SQLite**

**S3 (or compatible) for artifacts in cloud environments**

## 6) Pricing & Packaging (future)

**Tiered limits by pages/items per month**

**Webhooks / email on job completion**

---

## Links

- **Roadmap**: [./roadmap.md](./roadmap.md)
- **Dev Quickstart**: [./README.md](./README.md)
