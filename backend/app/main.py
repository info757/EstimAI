"""FastAPI main application."""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from .db import init_db
from .api.v1 import detect, counts
from .api import vector_takeoff
from .core.config import settings

# Configure logging - INFO level in production, DEBUG available via env
log_level = logging.DEBUG if settings.DEBUG else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for EstimAI construction estimation platform",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for reports
app.mount("/reports", StaticFiles(directory=str(settings.get_reports_dir())), name="reports")

# Mount static files for PDFs
app.mount("/files", StaticFiles(directory=str(settings.get_files_dir()), html=False), name="files")

# Include API routers
app.include_router(detect.router, tags=["detection"])
app.include_router(counts.router, tags=["counts"])
app.include_router(vector_takeoff.router, tags=["takeoff"])

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()
    print("Database initialized")

@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "EstimAI Backend",
            "version": "1.0.0"
        }
    )

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "EstimAI Backend API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}