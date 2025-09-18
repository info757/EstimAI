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
# For OCR (PR 19+), optionally set OCR_ENABLED=true and OCR_LANG=eng
# Note: .env.example may not include OCR settings - add them manually if needed

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### Run the App
```bash
# Start backend (in one terminal)
make dev    # Backend at http://localhost:8000

# Start frontend (in another terminal)  
make web    # Frontend at http://localhost:5173
```

**Complete Workflow:**
1. **Login**: Open http://localhost:5173 and sign in with admin credentials:
   - Username: `admin@example.com`
   - Password: `admin123`

2. **Create Project**: Navigate to Upload page and create a new project by uploading documents

3. **Review Data**: Navigate to `/projects/{project_id}/review` to:
   - Review and edit takeoff quantities
   - Adjust unit costs and markups
   - See real-time total calculations

4. **Continue Pipeline**: Click "Continue Pipeline" to:
   - Run the full estimation pipeline
   - Monitor job progress in real-time
   - See completion status and any errors

5. **Download Bid PDF**: Click "Generate Bid PDF" to:
   - Download the final bid document
   - File will be saved as `bid-{project_id}.pdf`

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

**OCR Configuration (PR 19+):**
- `OCR_ENABLED`: Enable OCR for image processing (default: false)
- `OCR_LANG`: OCR language code (default: eng)

**Note:** Add these variables to your `.env` file if you want to enable OCR functionality. These should also be added to `.env.example` for team reference.

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

## Authentication

**Authentication Flow:**
- **Login**: `POST /api/auth/login` with:
  ```json
  {
    "username": "admin@example.com",
    "password": "admin123"
  }
  ```
- **Response**: `{ "token": "<jwt>", "token_type": "bearer", "user": {...} }`
- **Storage**: Frontend stores token in localStorage and automatically attaches `Authorization: Bearer <token>` to all API calls
- **Protection**: All `/api/projects/*` endpoints require a valid token
- **Frontend**: Login page at `/login`, protected routes redirect to login if unauthenticated

**Default Admin Credentials:**
- Username: `admin@example.com`
- Password: `admin123`

**⚠️ NOTE:** This is development scaffolding; replace with real user store and authentication system in production.

## Multi-format Parsing (PR 19)

**Supported Formats:**
- **DOCX**: Text extraction from paragraphs and tables
- **XLSX**: Sheet data extraction with table structure
- **CSV**: Comma-separated value parsing
- **Images**: Basic OCR text extraction (PNG/JPG/TIFF) when `OCR_ENABLED=true`
- **PDF**: Stub parser (text extraction coming soon)

**OCR Configuration:**
```bash
# Enable OCR for image processing
OCR_ENABLED=true
OCR_LANG=eng  # Language code (default: eng)
```

**Note:** For OCR to work, you must have Tesseract installed on the host/container system.

**Environment Variables to Add to .env:**
```bash
# OCR Configuration (PR 19+)
OCR_ENABLED=false
OCR_LANG=eng

# Upload Guardrails (Mini-PR B)
ALLOWED_EXTS=.pdf,.docx,.xlsx,.csv,.png,.jpg,.jpeg,.tif,.tiff
MAX_UPLOAD_SIZE_MB=25

```

**Note:** These variables should also be added to `.env.example` for team reference. Note that `.env.example` is blocked by global ignore, so add these manually.

**Normalized Document Model:**
All parsed documents return a consistent structure:
```json
{
  "type": "docx|xlsx|csv|image|pdf|unknown",
  "meta": {
    "filename": "document.docx",
    "content_hash": "sha256:...",
    "size": 12345
  },
  "content": {
    "text": "Extracted text content...",
    "tables": [
      {
        "name": "Sheet1",
        "rows": [["Header1", "Header2"], ["Data1", "Data2"]]
      }
    ]
  }
}
```

**Implementation Details:**
- Normalized doc JSON is written to `artifacts/{pid}/ingest/parsed/…` with the structure above
- For OCR you must have Tesseract installed on the host/container
- Set `OCR_ENABLED=true` and `OCR_LANG=eng` to enable image text extraction

**Dependencies:**
- `python-docx>=1.1.0` - DOCX parsing
- `openpyxl>=3.1.5` - XLSX parsing  
- `pillow>=10.4.0` - Image processing
- `pytesseract>=0.3.13` - OCR (optional)



## Upload Limits (Mini-PR B)

**File Type Restrictions:**
- **Allowed Extensions**: PDF, DOCX, XLSX, CSV, PNG, JPG, JPEG, TIFF
- **Case Insensitive**: File extensions are validated regardless of case
- **Rejection**: Unsupported file types return HTTP 415 with clear error message

**File Size Limits:**
- **Maximum Size**: 25 MB per file (configurable via `MAX_UPLOAD_SIZE_MB`)
- **Streaming Validation**: File size is checked during upload to prevent large file abuse
- **Cleanup**: Partial files are automatically removed if size limit is exceeded
- **Error Response**: HTTP 413 with descriptive message when file is too large

**Configuration:**
```bash
# File type restrictions
ALLOWED_EXTS=.pdf,.docx,.xlsx,.csv,.png,.jpg,.jpeg,.tif,.tiff

# File size limit (in MB)
MAX_UPLOAD_SIZE_MB=25
```

**Error Messages:**
- **415 Unsupported Media Type**: "Unsupported file type. Allowed: PDF, DOCX, XLSX, CSV, PNG/JPG/TIFF."
- **413 Payload Too Large**: "File too large (limit 25 MB)."


## Standard Authenticated Workflow

**Quick Start:**
1. Copy `.env.example` → `.env` and set `JWT_SECRET` to a secure value
2. In one terminal: `make dev` (backend)
3. In another terminal: `make web` (frontend)
4. Open http://localhost:5173 and sign in with admin credentials
5. Create a project → Upload files → Review data → Continue Pipeline → Download Bid PDF

**Detailed Workflow:**
- **Upload**: Create project and upload construction documents (PDF, DOCX, XLSX, etc.)
- **Review**: Navigate to `/projects/{project_id}/review` to edit takeoff quantities, unit costs, and markups
- **Pipeline**: Run the full estimation pipeline with real-time progress monitoring
- **Bid**: Generate and download the final bid PDF document

**Environment Variables:**
```bash
# Required: JWT authentication secret
JWT_SECRET=your-secure-jwt-secret-here

# Required: Backend artifact directory (absolute path)
ARTIFACT_DIR=/ABSOLUTE/PATH/TO/estimai/backend/artifacts

# Frontend API configuration
VITE_API_BASE=http://localhost:8000/api
VITE_FILE_BASE=http://localhost:8000

# Upload guardrails
ALLOWED_EXTS=.pdf,.docx,.xlsx,.csv,.png,.jpg,.jpeg,.tif,.tiff
MAX_UPLOAD_SIZE_MB=25
```

**Default Admin Credentials:**
- Username: `admin@example.com`
- Password: `admin123`

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
- Use admin credentials for testing: `admin@example.com` / `admin123`
- If getting 401/403 errors, try logging in again to get a fresh token

**OCR Issues (PR 19+)**
- Ensure Tesseract is installed on your system: `tesseract --version`
- Check that `OCR_ENABLED=true` is set in your `.env` file
- Verify `OCR_LANG` is set to a supported language code (default: eng)
- For Docker deployments, ensure Tesseract is installed in the container
- If OCR fails, images will still be processed but with stub text "(OCR disabled)"
