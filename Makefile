PY=python3
.PHONY: api dev web test fmt lint clean db-up db-down

# Load environment variables and start backend
dev: ; cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start backend only (with env loading)
api: ; cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend development server
web: ; cd frontend && npm run dev

# Run backend tests
test: ; cd backend && pytest -q

# Format code
fmt: ; ruff check --fix backend || true ; black backend || true

# Lint code
lint: ; ruff check backend

# Clean caches (not artifacts)
clean: ; find . -type d -name "__pycache__" -exec rm -rf {} + ; find . -type d -name ".pytest_cache" -exec rm -rf {} + ; find . -type f -name "*.pyc" -delete

# Database commands (optional - requires Docker)
db-up: ; docker compose up -d db
db-down: ; docker compose down
