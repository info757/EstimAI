# Engineering Rules (EstimAI)
- FastAPI + Pydantic v2, SQLAlchemy 2.x, Postgres + pgvector, React+TS, Python 3.11.
- Agents return JSON validated by Pydantic models; no free-form prose returned to API.
- All LLM calls go through backend/app/core/llm.py with JSON schema enforcement.
- GET routes never mutate state; POST/PATCH for writes.
- Long jobs go to workers; API returns 202 where appropriate.
- Write artifacts to backend/artifacts/<project>/<agent>/<ts>.json.
- Takeoff items require `confidence` (0..1) and `evidence_uri`.
