"""API routes for serving sample PDFs."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter(prefix="/api/samples", tags=["samples"])

# Get samples directory (2 levels up from backend/app)
SAMPLES_DIR = Path(__file__).resolve().parents[3] / "samples"


@router.get("/")
def list_samples():
    """List all available sample PDFs."""
    if not SAMPLES_DIR.exists():
        return {"samples": [], "error": "Samples directory not found"}
    
    samples = []
    for pdf_file in SAMPLES_DIR.glob("*.pdf"):
        samples.append({
            "filename": pdf_file.name,
            "size_mb": round(pdf_file.stat().st_size / (1024 * 1024), 2),
            "url": f"/api/samples/{pdf_file.name}"
        })
    
    return {"samples": samples}


@router.get("/{filename}")
def get_sample(filename: str):
    """Serve a sample PDF file."""
    # Security: only allow PDF files and prevent path traversal
    if not filename.endswith(".pdf") or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    file_path = SAMPLES_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Sample PDF '{filename}' not found")
    
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename
    )

