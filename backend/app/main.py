"""FastAPI main application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from .db import init_db
from .api.v1 import detect, counts
from .core.config import settings

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

# Include API routers
app.include_router(detect.router, tags=["detection"])
app.include_router(counts.router, tags=["counts"])

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