# EstimAI

[![CI](https://github.com/<YOUR_ORG_OR_USER>/<YOUR_REPO>/actions/workflows/ci.yml/badge.svg)](https://github.com/<YOUR_ORG_OR_USER>/<YOUR_REPO>/actions/workflows/ci.yml)

Multi-agent estimating application with async pipeline orchestration.

## Dev Quickstart

### Prereqs
- Python 3.11+
- Node 18+ and npm
- Make (optional but recommended)

### Setup
```bash
git clone <YOUR_REPO_URL>
cd estimai
cp .env.example .env
# Edit .env and set an ABSOLUTE ARTIFACT_DIR path
# For authentication (PR 15+), set JWT_SECRET to a secure value

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### Run
```bash
make dev    # Backend at http://localhost:8000
make web    # Frontend at http://localhost:5173
```

### Test
```bash
make test   # Run backend tests
```

## Run with Docker

```bash
# build and start (backend:8000, frontend:8080)
docker compose up -d --build

# follow logs
docker compose logs -f

# stop
docker compose down
```

## Health & Logs

### Health Check
Monitor application health and version information:

```bash
# Basic health check
curl -s http://localhost:8000/health | jq

# Expected response:
{
  "status": "ok",
  "uptime_seconds": 123.456,
  "version": "f47c4f4"
}
```

### Structured Logging
The application uses structured JSON logging for production monitoring:

**Log Format:**
```json
{
  "ts": "2025-09-03T14:16:11.618983Z",
  "level": "INFO",
  "msg": "🚀 EstimAI backend starting up...",
  "logger": "app.main",
  "pid": 69804,
  "path": "/health",
  "method": "GET",
  "status": 200,
  "duration_ms": 2.43,
  "project_id": "P1",
  "job_id": "J1"
}
```

**Key Log Fields:**
- `ts`: ISO UTC timestamp
- `level`: Log level (INFO, ERROR, etc.)
- `msg`: Human-readable message
- `logger`: Logger name
- `pid`: Process ID
- `path`: HTTP request path
- `method`: HTTP method
- `status`: HTTP status code
- `duration_ms`: Request duration in milliseconds
- `project_id`: Project identifier (when available)
- `job_id`: Job identifier (when available)
- `log_type`: Type of log entry (e.g., "job_transition", "pipeline_completion")

**Job Pipeline Logging:**
```json
{
  "ts": "2025-09-03T14:16:30.789Z",
  "level": "INFO",
  "msg": "Full pipeline completed successfully",
  "logger": "app.services.orchestrator",
  "pid": 69804,
  "project_id": "P1",
  "path": "/pipeline",
  "method": "POST",
  "status": 200,
  "duration_ms": 10450.23,
  "log_type": "pipeline_completion",
  "result": {
    "steps_completed": 5,
    "errors_count": 0
  }
}
```

**Version Tracking:**
The application automatically tracks the git commit SHA:
- Set `COMMIT_SHA` environment variable for custom versioning
- Docker builds automatically include current git commit SHA
- Falls back to "dev" if no version information available

**Log Aggregation:**
- Single-line JSON format for production log systems
- Compatible with ELK stack, Splunk, Datadog, etc.
- Request context preserved across async operations
```

## Path Contracts

### Artifact Directory Structure
```
backend/artifacts/
├── {project_id}/
│   ├── docs/           # Uploaded PDFs
│   ├── takeoff/        # Takeoff analysis results
│   ├── scope/          # Scope analysis results  
│   ├── leveler/        # Leveling results
│   ├── risk/           # Risk analysis results
│   ├── estimate/       # Cost estimates
│   ├── bid/            # Generated bid PDFs
│   ├── sheet_index.json    # Document metadata
│   └── spec_index.json     # Specification chunks
```

### Environment Variables
**Required:**
- `ARTIFACT_DIR`: Absolute path to artifacts directory

**Authentication (PR 15+):**
- `JWT_SECRET`: Secret key for JWT token signing (required in production)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT token expiration time (default: 60)
- `JWT_ALG`: JWT signing algorithm (default: HS256)

**Optional:**
- `CORS_ORIGINS`: Comma-separated allowed origins
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `VITE_API_BASE`: Backend API URL (default: http://localhost:8000/api)
- `VITE_FILE_BASE`: File serving URL (default: http://localhost:8000)

### API Endpoints
**Authentication Required (PR 15+):**
- `POST /api/auth/login` - Authenticate and get JWT token
- `POST /api/projects/{pid}/ingest` - Upload documents
- `POST /api/projects/{pid}/pipeline_async` - Start async pipeline
- `GET /api/jobs/{job_id}` - Check job status
- `POST /api/projects/{pid}/bid` - Generate bid PDF
- `GET /api/projects/{pid}/artifacts` - List artifacts

**Public Endpoints:**
- `GET /health` - Health check and version info
- `GET /docs` - OpenAPI documentation

### Development Commands
```bash
make dev    # Start backend with hot reload
make web    # Start frontend development server
make test   # Run backend tests
make fmt    # Format code
make lint   # Lint code
make clean  # Clear caches
```

## Auth (demo scaffold)

**Authentication Flow:**
- **Login**: `POST /api/auth/login` with:
  ```json
  {
    "username": "demo@example.com",
    "password": "demo123"
  }
  ```
- **Response**: `{ "token": "<jwt>", "token_type": "bearer", "user": {...} }`
- **Storage**: Frontend stores token in localStorage and automatically attaches `Authorization: Bearer <token>` to all API calls
- **Protection**: All `/api/projects/*` endpoints require a valid token
- **Frontend**: Login page at `/login`, protected routes redirect to login if unauthenticated

**Demo Credentials:**
- Username: `demo@example.com`
- Password: `demo123`

**⚠️ NOTE:** This is demo-only scaffolding; replace with real user store and authentication system in production.

## Troubleshooting

**curl hangs in terminal**
- Verify backend is running: `make dev` → Uvicorn on :8000
- Hit `/docs` or `/health` first to confirm server is live
- If route isn't implemented yet (e.g., `/api/jobs` before PR 3), curl will wait and appear to "hang"

**Artifacts 404**
- Ensure `ARTIFACT_DIR` is an ABSOLUTE path and exists
- Confirm startup log: `/artifacts mounted at: <abs path>`
- Make sure frontend uses `VITE_FILE_BASE` for links

**CORS errors**
- Check `CORS_ORIGINS` in `.env` includes `http://localhost:5173`

**Job Migration (PR 14+)**
- If upgrading from a version before PR 14, run the migration script:
  ```bash
  python scripts/migrate_jobs_disk_to_sqlite.py
  ```
- This migrates legacy JSON job files to the new SQLite database
- Safe to run multiple times - uses INSERT OR IGNORE to avoid duplicates

**Authentication Issues (PR 15+)**
- Ensure `JWT_SECRET` is set in environment variables
- Check that token is being sent in Authorization header
- Verify token hasn't expired (default: 60 minutes)
- Use demo credentials for testing: `demo@example.com` / `demo123`
- If getting 401/403 errors, try logging in again to get a fresh token
