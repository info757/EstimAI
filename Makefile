PY=python3
.PHONY: api dev web test fmt lint clean db-up db-down

# Load environment variables and start backend
dev: ; cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start backend only (with env loading)
api: ; cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend development server
web: ; cd frontend && npm run dev

# Run backend tests
test:
	if [ -f .env ]; then set -o allexport; source .env; set +o allexport; fi; \
	pytest -q

# Format code
fmt: ; ruff check --fix backend || true ; black backend || true

# Lint code
lint:
	ruff check . || true
	black --check . || true

# Clean caches (not artifacts)
clean: ; find . -type d -name "__pycache__" -exec rm -rf {} + ; find . -type d -name ".pytest_cache" -exec rm -rf {} + ; find . -type f -name "*.pyc" -delete

# Database commands (optional - requires Docker)
db-up: ; docker compose up -d db
db-down: ; docker compose down

# Demo utilities
demo: 
	@echo "🚀 Starting EstimAI Demo..."
	@echo "📋 Quick Demo Instructions:"
	@echo "  1. Copy .env.example → .env (keep DEMO_PUBLIC=true)"
	@echo "  2. In one terminal: make dev"
	@echo "  3. In another terminal: make web"
	@echo "  4. Open http://localhost:5173/projects/demo"
	@echo ""
	@echo "🔄 Starting services in background..."
	@make dev & make web

demo-seed:
	cd backend && python -m app.scripts.seed_demo

demo-reset:
	cd backend && python -m app.scripts.reset_demo

demo-open:
	@echo "🌐 Open your browser to: http://localhost:5173/projects/demo"

# Docker commands for PR 12
docker-build-backend:
	docker build -f Dockerfile.backend \
		--build-arg COMMIT_SHA=$${COMMIT_SHA:-dev} \
		-t estimai-backend:latest .

docker-build-frontend:
	docker build -f Dockerfile.frontend \
		--build-arg COMMIT_SHA=$${COMMIT_SHA:-dev} \
		-t estimai-frontend:latest .

# Get current git commit SHA
docker-up:
	COMMIT_SHA=$$(git rev-parse --short HEAD 2>/dev/null || echo "dev") docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-restart:
	docker compose restart
