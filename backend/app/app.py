"""Application factory for EstimAI backend."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import logging

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    # Create the app
    app = FastAPI(
        title="EstimAI Backend API",
        description="Backend API for EstimAI construction estimation platform",
        version="1.0.0"
    )

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add security middleware
    try:
        from backend.app.middleware.security import get_error_handler, with_security_middleware
        app.add_exception_handler(Exception, get_error_handler())
        print("✅ Security middleware and error handlers configured")
    except Exception as e:
        print(f"⚠️ Security middleware failed to load: {e}")

    # Mount static files
    try:
        from backend.app.core.config import settings
        from pathlib import Path
        app.mount("/reports", StaticFiles(directory=str(settings.get_reports_dir())), name="reports")
        app.mount("/files", StaticFiles(directory=str(settings.get_files_dir()), html=False), name="files")
        
        # Mount samples directory for viewing test PDFs
        samples_dir = Path(__file__).resolve().parents[2] / "samples"
        if samples_dir.exists():
            app.mount("/samples", StaticFiles(directory=str(samples_dir), html=False), name="samples")
        
        print("✅ Static files mounted")
    except Exception as e:
        print(f"⚠️ Static files mounting failed: {e}")

    # Include routers (import AFTER app is created to avoid circular imports)
    try:
        from fastapi import APIRouter
        from backend.app.api.v1 import detect, counts
        from backend.app.api import vector_takeoff
        from backend.app.api.v1.routes.takeoff import router as takeoff_router
        from backend.app.api.v1.routes.takeoff_review import router as takeoff_review_router
        from backend.app.api.v1.routes.debug_validate import router as debug_validate_router
        from backend.app.api.v1.routes.agent import router as agent_router
        from backend.app.api.v1.routes.export import router as export_router
        from backend.app.api.v1.routes.demo import router as demo_router
        from backend.app.api.v1.routes.debug import router as debug_router
        # Legacy routers (for /api/projects, /api/jobs, etc.)
        from backend.app.api.routes_projects import router as projects_router
        from backend.app.api.routes_jobs import router as jobs_router
        from backend.app.api.routes_review import router as review_router
        from backend.app.api.routes_auth import router as auth_router
        from backend.app.api.routes_files import router as files_router
        from backend.app.api.routes_samples import router as samples_router

        # Include routers directly - they already have /v1 prefix
        app.include_router(detect.router, tags=["detection"])
        app.include_router(counts.router, tags=["counts"])
        app.include_router(takeoff_router, tags=["takeoff"])
        app.include_router(takeoff_review_router, tags=["takeoff"])
        app.include_router(debug_validate_router, tags=["debug"])
        app.include_router(agent_router, tags=["agent"])
        app.include_router(export_router, tags=["export"])
        app.include_router(demo_router, tags=["demo"])
        app.include_router(debug_router, tags=["debug"])

        # Also mount under /api prefix for frontend compatibility
        api = APIRouter(prefix="/api")
        api.include_router(detect.router, tags=["detection"])
        api.include_router(counts.router, tags=["counts"])
        api.include_router(takeoff_router, tags=["takeoff"])
        api.include_router(takeoff_review_router, tags=["takeoff"])
        api.include_router(debug_validate_router, tags=["debug"])
        api.include_router(agent_router, tags=["agent"])
        api.include_router(export_router, tags=["export"])
        api.include_router(demo_router, tags=["demo"])
        # Legacy routes under /api
        api.include_router(projects_router, tags=["projects"])
        api.include_router(jobs_router, tags=["jobs"])
        api.include_router(review_router, tags=["review"])
        api.include_router(auth_router, tags=["auth"])
        api.include_router(files_router, tags=["files"])
        app.include_router(api)
        
        # Samples router (served at /api/samples)
        app.include_router(samples_router, tags=["samples"])

        # Also include vector_takeoff router directly (not under /v1)
        app.include_router(vector_takeoff.router, tags=["takeoff"])
        
        print("✅ All routers included at /v1 and /api/v1")
    except Exception as e:
        print(f"⚠️ Router inclusion failed: {e}")

    # Startup event
    @app.on_event("startup")
    def _startup() -> None:
        """Initialize database and optional services on startup."""
        try:
            from backend.app.db import init_db
            init_db()
            print("✅ Database initialized")
        except Exception as e:
            print(f"⚠️ Database initialization failed: {e}")

        # Run database migrations
        try:
            from backend.app.db.migrations import apply_migrations
            applied = apply_migrations()
            print(f"✅ Database migrations completed: {len(applied)} indices applied")
        except Exception as e:
            print(f"⚠️ Database migrations failed: {e}")

        # Log text extraction backend configuration
        try:
            from backend.app.core.config import settings
            import logging
            logger = logging.getLogger(__name__)
            text_backend = settings.get_text_backend()
            logger.info(f"📝 TextBackend={text_backend}")
            print(f"📝 TextBackend={text_backend}")  # Also print for visibility
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠️ Failed to log text backend: {e}")
            print(f"⚠️ Failed to log text backend: {e}")
        
        # Initialize Apryse PDFNet if enabled
        try:
            from backend.app.core.config import settings
            if settings.APR_USE_APRYSE:
                from backend.app.services.ingest.pdfnet_runtime import init as pdfnet_init
                pdfnet_init()
                print("✅ Apryse PDFNet initialized")
                
                from backend.app.services.detectors import init_depth_config
                init_depth_config()
                print("✅ Depth configuration initialized")
            else:
                print("ℹ️ Apryse disabled (APR_USE_APRYSE not set)")
        except Exception as e:
            print(f"⚠️ Apryse initialization failed: {e}")

        # Initialize demo mode if enabled
        try:
            from backend.app.core.demo_config import get_demo_manager
            demo_manager = get_demo_manager()
            if demo_manager.is_demo_mode():
                print("🎯 Demo mode enabled")
        except Exception as e:
            print(f"⚠️ Demo mode initialization failed: {e}")

    # Health check endpoints
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "estimai-backend",
            "version": "1.0.0",
            "timestamp": __import__("time").time()
        }

    @app.get("/_healthz")
    def _health():
        """Simple health check for load balancers."""
        return {"ok": True}

    @app.get("/_routes")
    def _routes():
        """List all registered routes for debugging."""
        return [getattr(r, "path", None) for r in app.routes]

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {"message": "EstimAI Backend API", "version": "1.0.0"}

    return app
