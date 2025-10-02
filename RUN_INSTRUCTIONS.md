# EstimAI Run Instructions

This guide provides exact commands to run the EstimAI application without import errors.

## 🚀 Quick Start

### Backend (Always from repo root or backend/, NEVER from frontend/)

**Option 1: Using the run script (recommended)**
```bash
# From repo root
./run_backend.sh
```

**Option 2: Manual commands**
```bash
# From repo root
cd backend
source ../.venv/bin/activate 2>/dev/null || true
uvicorn app.main:app --reload --app-dir .
```

**Option 3: From repo root with PYTHONPATH**
```bash
# From repo root
PYTHONPATH=backend uvicorn app.main:app --reload --app-dir backend
```

### Frontend

**Option 1: Using the run script (recommended)**
```bash
# From repo root
./run_frontend.sh
```

**Option 2: Manual commands**
```bash
# From repo root
cd frontend
npm run dev
```

## ⚠️ Important Notes

### Import Error Prevention
- **Always run backend from repo root or backend/ directory**
- **Never run from frontend/ directory**
- **Use the exact commands above to avoid import errors**

### Directory Structure
```
estimai/                    # ← Run commands from here
├── backend/               # ← Or from here
│   ├── app/              # FastAPI application
│   └── requirements.txt
├── frontend/             # ← Or from here
│   ├── src/
│   └── package.json
├── .venv/               # Virtual environment
├── run_backend.sh       # Backend run script
├── run_frontend.sh      # Frontend run script
└── RUN_INSTRUCTIONS.md  # This file
```

## 🔧 Environment Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Virtual environment activated

### Backend Setup
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run backend
./run_backend.sh
```

### Frontend Setup
```bash
# Install dependencies
cd frontend
npm install

# Run frontend
cd ..
./run_frontend.sh
```

## 🌐 Access Points

### Backend
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/healthz
- **Reports**: http://localhost:8000/reports/

### Frontend
- **App**: http://localhost:5173
- **Hot Reload**: Automatic on file changes

## 🐛 Troubleshooting

### Import Errors
If you get import errors like `ModuleNotFoundError: No module named 'app'`:

1. **Check directory**: Make sure you're in repo root or backend/
2. **Check PYTHONPATH**: Use the exact commands above
3. **Check virtual environment**: Ensure it's activated

### Port Conflicts
- Backend runs on port 8000
- Frontend runs on port 5173
- Change ports if needed: `--port 8001` for backend

### Database Issues
- Database is created automatically
- Delete `estimai.db` to reset
- Check file permissions

## 📝 Development Workflow

### 1. Start Backend
```bash
# Terminal 1
./run_backend.sh
```

### 2. Start Frontend
```bash
# Terminal 2
./run_frontend.sh
```

### 3. Access Application
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000

## 🔄 Common Commands

### Backend Commands
```bash
# Run backend
./run_backend.sh

# Run with specific port
cd backend && uvicorn app.main:app --reload --app-dir . --port 8001

# Run tests
cd backend && python -m pytest tests/

# Install dependencies
pip install -r backend/requirements.txt
```

### Frontend Commands
```bash
# Run frontend
./run_frontend.sh

# Install dependencies
cd frontend && npm install

# Build for production
cd frontend && npm run build
```

## 🚨 Error Solutions

### "ModuleNotFoundError: No module named 'app'"
- **Solution**: Run from repo root or backend/ directory
- **Command**: `cd backend && uvicorn app.main:app --reload --app-dir .`

### "uvicorn: command not found"
- **Solution**: Activate virtual environment
- **Command**: `source .venv/bin/activate`

### "npm: command not found"
- **Solution**: Install Node.js
- **Download**: https://nodejs.org/

### "Port 8000 already in use"
- **Solution**: Kill process or use different port
- **Command**: `lsof -ti:8000 | xargs kill -9`

## 📚 Additional Resources

- **Backend README**: `backend/README.md`
- **API Documentation**: http://localhost:8000/docs
- **Frontend Documentation**: `frontend/README.md`

## 🎯 Success Checklist

- [ ] Backend running on http://localhost:8000
- [ ] Frontend running on http://localhost:5173
- [ ] Health check: http://localhost:8000/healthz
- [ ] API docs: http://localhost:8000/docs
- [ ] No import errors in console
- [ ] Both services accessible
