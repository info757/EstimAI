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


class DemoModeMiddleware(BaseHTTPMiddleware):
    """ASGI middleware for demo mode rate limiting and access control."""
    
    def __init__(self, app, settings):
        super().__init__(app)
        self.settings = settings
        self.demo_project_id = settings.DEMO_PROJECT_ID
        self.demo_public = settings.DEMO_PUBLIC
        self.rate_limit = settings.DEMO_RATE_LIMIT_PER_MIN
        self.ip_counters = {}  # {ip: [(timestamp, count), ...]}
    
    def _is_demo_route(self, path: str) -> bool:
        """Check if the request is for a demo project route."""
        return (self.demo_public and 
                (path.startswith(f'/api/projects/{self.demo_project_id}/') or
                 path.startswith(f'/artifacts/{self.demo_project_id}/')))
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address, handling proxies."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        # Fall back to direct connection
        return request.client.host if request.client else 'unknown'
    
    def _check_rate_limit(self, ip: str) -> bool:
        """Check if IP is within rate limit for demo routes."""
        now = time.time()
        window_start = now - 60  # 1 minute sliding window
        
        # Clean old entries
        if ip in self.ip_counters:
            self.ip_counters[ip] = [
                (ts, count) for ts, count in self.ip_counters[ip] 
                if ts > window_start
            ]
        
        # Count requests in current window
        current_count = sum(count for _, count in self.ip_counters.get(ip, []))
        
        # Add current request
        if ip not in self.ip_counters:
            self.ip_counters[ip] = []
        self.ip_counters[ip].append((now, 1))
        
        return current_count < self.rate_limit
    
    async def dispatch(self, request: Request, call_next):
        path = str(request.url.path)
        
        # Only apply demo mode logic to demo routes
        if self._is_demo_route(path):
            client_ip = self._get_client_ip(request)
            
            # Check rate limit
            if not self._check_rate_limit(client_ip):
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=429,
                    detail=f"Demo rate limit exceeded ({self.rate_limit} requests per minute). Please wait a minute."
                )
            
            # Log demo access
            logger.info("Demo mode access", extra={
                'path': path,
                'client_ip': client_ip,
                'demo_project': self.demo_project_id
            })
        
        # Continue with normal request processing
        return await call_next(request)


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

# Add demo mode middleware if enabled
if settings.DEMO_PUBLIC:
    app.add_middleware(DemoModeMiddleware, settings=settings)

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
    from .core.paths import ensure_demo_project_structure
    
    logger.info(f"🚀 EstimAI backend starting up...")
    logger.info(f"📁 /artifacts mounted at: {ARTIFACTS_DIR.resolve()}")
    logger.info(f"📁 /static/samples mounted at: {SAMPLES_DIR.resolve()}")
    logger.info(f"🌐 CORS origins: {settings.CORS_ORIGINS}")
    logger.info(f"📝 Log level: {settings.LOG_LEVEL}")
    logger.info(f"🔖 Version: {app_version()}")
    
    # Log demo mode status and bootstrap demo project structure
    if settings.DEMO_PUBLIC:
        logger.info(f"🎭 Demo mode ENABLED - Project '{settings.DEMO_PROJECT_ID}' is public (rate limit: {settings.DEMO_RATE_LIMIT_PER_MIN}/min)")
        logger.info(f"📁 Bootstrapping demo project structure at: {ARTIFACTS_DIR.resolve() / settings.DEMO_PROJECT_ID}")
        ensure_demo_project_structure(settings.DEMO_PROJECT_ID)
        logger.info(f"✅ Demo project structure ready")
        
        # Seed demo samples
        logger.info(f"🌱 Seeding demo sample files...")
        from .scripts.seed_demo import run as seed_demo
        seed_demo()
        logger.info(f"✅ Demo seed ensured")
    else:
        logger.info(f"🔒 Demo mode DISABLED - All projects require authentication")
    
    # Ensure overrides directory structure exists
    logger.info(f"📁 Ensuring overrides directory structure...")
    
    logger.info(f"✅ Backend ready at http://localhost:8000")
