# EstimAI Backend

This is the backend API for the EstimAI construction estimation platform.

## Quick Start

### Prerequisites
- Python 3.11+
- Virtual environment activated
- Dependencies installed

### Running the Backend

**Option 1: From repo root (recommended)**
```bash
# From repo root
cd backend
source ../.venv/bin/activate 2>/dev/null || true
uvicorn app.main:app --reload --app-dir .
```

**Option 2: From repo root with PYTHONPATH**
```bash
# From repo root
PYTHONPATH=backend uvicorn app.main:app --reload --app-dir backend
```

**Option 3: From backend directory**
```bash
# From backend directory
cd backend
source ../.venv/bin/activate 2>/dev/null || true
uvicorn app.main:app --reload --app-dir .
```

### Running the Frontend

```bash
# From repo root
cd frontend
npm run dev
```

## Important Notes

### Import Error Prevention
- **Always run backend from repo root or backend/ directory**
- **Never run from frontend/ directory**
- **Use the exact commands above to avoid import errors**

### Directory Structure
```
estimai/
├── backend/          # Backend code
│   ├── app/         # FastAPI application
│   └── requirements.txt
├── frontend/         # Frontend code
│   ├── src/
│   └── package.json
└── .venv/           # Virtual environment
```

### Environment Setup
1. **Activate virtual environment**: `source .venv/bin/activate`
2. **Install dependencies**: `pip install -r backend/requirements.txt`
3. **Run backend**: Use commands above
4. **Run frontend**: `cd frontend && npm run dev`

## API Endpoints

### Health Check
- `GET /healthz` - Service health status

### Detection
- `POST /v1/detect` - Run detection on PDF page
- `GET /v1/detect/{file}/{page}` - Get detection results
- `GET /v1/detect/stats/{file}` - Get detection statistics

### Counts
- `GET /v1/counts` - List count items with filters
- `PATCH /v1/counts/{id}` - Update count item
- `GET /v1/counts/{id}` - Get specific count item
- `DELETE /v1/counts/{id}` - Delete count item

### Review
- `POST /v1/review/commit` - Commit review results
- `GET /v1/sessions` - List review sessions
- `GET /v1/sessions/{id}` - Get review session
- `GET /v1/sessions/{id}/metrics` - Get session metrics

### Static Files
- `GET /reports/{filename}` - Download generated reports

## Configuration

### Environment Variables
Create `.env` file in backend directory:
```env
DATABASE_URL=sqlite:///./estimai.db
FILES_DIR=app/files
REPORTS_DIR=/tmp/estimai_reports
TEMPLATES_DIR=backend/templates
DETECTOR_IMPL=opencv_template
```

### Database
- SQLite database created automatically
- Tables initialized on startup
- Data persisted in `estimai.db`

## Troubleshooting

### Import Errors
If you get import errors:
1. **Check directory**: Make sure you're in repo root or backend/
2. **Check PYTHONPATH**: Use the exact commands above
3. **Check virtual environment**: Ensure it's activated

### Port Conflicts
- Backend runs on `http://localhost:8000`
- Frontend runs on `http://localhost:5173`
- Change ports if needed: `--port 8001` for backend

### Database Issues
- Delete `estimai.db` to reset database
- Check file permissions for database directory
- Ensure SQLite is installed

## Development

### Adding New Endpoints
1. Create router in `app/api/v1/`
2. Add to `app/main.py`
3. Update this README

### Adding New Models
1. Define in `app/models.py`
2. Create migration (if needed)
3. Update schemas in `app/schemas.py`

### Testing
```bash
# Run tests
cd backend
python -m pytest tests/

# Run specific test
python -m pytest tests/test_detect.py
```

## Production Deployment

### Docker
```bash
# Build image
docker build -f Dockerfile.backend -t estimai-backend .

# Run container
docker run -p 8000:8000 estimai-backend
```

### Environment Variables
Set production environment variables:
- `DATABASE_URL` - Production database
- `SECRET_KEY` - Secure secret key
- `BACKEND_CORS_ORIGINS` - Allowed origins