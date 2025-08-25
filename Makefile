PY=python3
.PHONY: api dev db-up db-down test fmt lint
dev: db-up api
api: ; cd backend && uvicorn app.main:app --reload --port 8000
db-up: ; docker compose up -d db
db-down: ; docker compose down
test: ; cd backend && pytest -q
fmt: ; ruff check --fix backend || true ; black backend || true
lint: ; ruff check backend
