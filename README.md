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

**Optional:**
- `CORS_ORIGINS`: Comma-separated allowed origins
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `VITE_API_BASE`: Backend API URL (default: http://localhost:8000/api)
- `VITE_FILE_BASE`: File serving URL (default: http://localhost:8000)

### API Endpoints
- `POST /api/projects/{pid}/ingest` - Upload documents
- `POST /api/projects/{pid}/pipeline_async` - Start async pipeline
- `GET /api/jobs/{job_id}` - Check job status
- `POST /api/projects/{pid}/bid` - Generate bid PDF
- `GET /api/projects/{pid}/artifacts` - List artifacts

### Development Commands
```bash
make dev    # Start backend with hot reload
make web    # Start frontend development server
make test   # Run backend tests
make fmt    # Format code
make lint   # Lint code
make clean  # Clear caches
```

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
