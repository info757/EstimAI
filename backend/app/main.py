# backend/app/main.py
import logging
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from .api.routes import r
from .core.config import get_settings
from .core.paths import artifacts_root
from .core.runtime import get_runtime_info
from .core.logging import configure_logging, json_logger, set_request_context, clear_request_context

from .services.overrides import ensure_overrides_dir

# Load environment variables
load_dotenv()

# Configure logging
settings = get_settings()
configure_logging(settings.LOG_LEVEL)
logger = json_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """ASGI middleware to log request timing and context."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Extract project_id from path if present
        project_id = None
        path = str(request.url.path)
        if path.startswith('/projects/'):
            parts = path.split('/')
            if len(parts) > 2:
                project_id = parts[2]
        
        # Extract job_id from query params if present
        job_id = request.query_params.get('job_id')
        
        # Set request context for logging
        context = {
            'path': path,
            'method': request.method,
            'project_id': project_id
        }
        if job_id:
            context['job_id'] = job_id
        set_request_context(**context)
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise
        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log request with structured data
            logger.info("request", extra={
                'path': path,
                'method': request.method,
                'status': status_code,
                'duration_ms': round(duration_ms, 2),
                'project_id': project_id,
                'job_id': job_id
            })
            
            # Clear request context
            clear_request_context()
        
        return response


app = FastAPI(title="EstimAI")

# --- Middleware ---
app.add_middleware(LoggingMiddleware)
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

# /static/samples -> backend/static/samples (sample files)
SAMPLES_DIR = (APP_DIR.parent / "static" / "samples").resolve()
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static/samples", StaticFiles(directory=str(SAMPLES_DIR)), name="samples")

# --- API routes under /api ---
app.include_router(r, prefix="/api")


@app.get("/health")
async def health_check():
    """
    Health check endpoint with uptime and version information.
    
    Returns:
        dict: Health status with uptime and version
    """
    # Include debug info when LOG_LEVEL is DEBUG
    include_debug = settings.LOG_LEVEL == "DEBUG"
    return get_runtime_info(include_debug=include_debug)


@app.on_event("startup")
async def startup_event():
    """Log startup configuration."""
    from .core.runtime import app_version
    
    logger.info(f"🚀 EstimAI backend starting up...")
    logger.info(f"📁 /artifacts mounted at: {ARTIFACTS_DIR.resolve()}")
    logger.info(f"📁 /static/samples mounted at: {SAMPLES_DIR.resolve()}")
    logger.info(f"🌐 CORS origins: {settings.CORS_ORIGINS}")
    logger.info(f"📝 Log level: {settings.LOG_LEVEL}")
    logger.info(f"🔖 Version: {app_version()}")
    
    # Ensure overrides directory structure exists
    logger.info(f"📁 Ensuring overrides directory structure...")
    
    logger.info(f"✅ Backend ready at http://localhost:8000")
