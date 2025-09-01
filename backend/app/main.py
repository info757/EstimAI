# backend/app/main.py
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from .api.routes import r

load_dotenv()
app = FastAPI(title="EstimAI")

# --- CORS (Vite dev) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Correct paths:
#   APP_DIR      = .../backend/app
#   BACKEND_DIR  = .../backend
APP_DIR = Path(__file__).resolve().parent           # backend/app
BACKEND_DIR = APP_DIR.parent                        # backend

# --- Static mounts ---
# /artifacts -> the SAME base dir your code writes to
# Use absolute path to ensure correct resolution regardless of working directory
ARTIFACTS_DIR = Path(os.getenv("ARTIFACT_DIR", str(BACKEND_DIR / "artifacts"))).resolve()
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=str(ARTIFACTS_DIR)), name="artifacts")

# /projects -> backend/app/data/projects  (indexes / json etc.)
PROJECTS_DIR = (APP_DIR / "data" / "projects").resolve()
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/projects", StaticFiles(directory=str(PROJECTS_DIR)), name="projects")

# --- API routes under /api ---
app.include_router(r, prefix="/api")
