# EstimAI

Multi-agent estimating application with async pipeline orchestration.

## Dev Quickstart

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env and set your absolute artifact directory path
# Example: ARTIFACT_DIR=/Users/yourname/estimai/backend/artifacts
```

### 2. Backend Setup

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
make dev
```

The backend will start at `http://localhost:8000` with:
- API docs at `http://localhost:8000/docs`
- Artifacts served at `http://localhost:8000/artifacts/`

### 3. Frontend Setup

```bash
# In a new terminal, start frontend
make web
```

The frontend will start at `http://localhost:5173` (or 5174 if 5173 is busy).

### 4. Environment Variables

**Backend:**
- `ARTIFACT_DIR`: Absolute path to artifacts directory (required)
- `CORS_ORIGINS`: Comma-separated list of allowed origins
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**Frontend:**
- `VITE_API_BASE`: Backend API base URL (default: `http://localhost:8000/api`)
- `VITE_FILE_BASE`: Backend file serving URL (default: `http://localhost:8000`)

### 5. Usage

1. **Upload Documents**: Use the upload page to add PDFs to a project
2. **Run Pipeline**: Click "Run Full Pipeline" to execute all agents asynchronously
3. **Generate Bid**: Click "Generate Bid PDF" to create a bid document
4. **Monitor Progress**: Watch job status and download artifacts

### 6. Development Commands

```bash
make dev    # Start backend with hot reload
make web    # Start frontend development server
make test   # Run backend tests
make fmt    # Format code
make lint   # Lint code
make clean  # Clear caches
```

## Architecture

- **Backend**: FastAPI with async job processing
- **Frontend**: React + TypeScript + Vite
- **Agents**: Takeoff → Scope → Leveler → Risk → Estimate → Bid
- **Storage**: File-based artifacts with JSON metadata

## API Endpoints

- `POST /api/projects/{pid}/ingest` - Upload project documents
- `POST /api/projects/{pid}/pipeline_async` - Start async pipeline
- `GET /api/jobs/{job_id}` - Check job status
- `POST /api/projects/{pid}/bid` - Generate bid PDF
- `GET /api/projects/{pid}/artifacts` - List project artifacts
