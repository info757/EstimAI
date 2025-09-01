# backend/app/main.py
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.routes import r
from .core.config import get_settings
from .core.paths import artifacts_root
from .services.overrides import ensure_overrides_dir

# Load environment variables
load_dotenv()

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="EstimAI")

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static mounts ---
# /artifacts -> artifacts directory from settings
ARTIFACTS_DIR = artifacts_root()
app.mount("/artifacts", StaticFiles(directory=str(ARTIFACTS_DIR)), name="artifacts")

# /projects -> backend/app/data/projects (indexes / json etc.)
APP_DIR = Path(__file__).resolve().parent  # backend/app
PROJECTS_DIR = (APP_DIR / "data" / "projects").resolve()
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/projects", StaticFiles(directory=str(PROJECTS_DIR)), name="projects")

# --- API routes under /api ---
app.include_router(r, prefix="/api")


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.on_event("startup")
async def startup_event():
    """Log startup configuration."""
    logger.info(f"🚀 EstimAI backend starting up...")
    logger.info(f"📁 /artifacts mounted at: {ARTIFACTS_DIR.resolve()}")
    logger.info(f"🌐 CORS origins: {settings.CORS_ORIGINS}")
    logger.info(f"📝 Log level: {settings.LOG_LEVEL}")
    
    # Ensure overrides directory structure exists
    logger.info(f"📁 Ensuring overrides directory structure...")
    
    logger.info(f"✅ Backend ready at http://localhost:8000")
