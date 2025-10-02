"""
FastAPI routes for serving PDF files and static assets.
"""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional

router = APIRouter(prefix="/files", tags=["files"])

# Serve static files from artifacts directory
ARTIFACTS_DIR = Path(os.getenv("ARTIFACT_DIR", "backend/artifacts"))

@router.get("/{filename}")
async def serve_file(filename: str, request: Request):
    """
    Serve PDF files from the artifacts directory.
    Supports streaming for large files.
    """
    file_path = ARTIFACTS_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Not a file")
    
    # Check if it's a PDF file
    if not filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Get file size for streaming decision
    file_size = file_path.stat().st_size
    
    # For large files (>10MB), use streaming
    if file_size > 10 * 1024 * 1024:  # 10MB
        def iter_file():
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk
        
        return StreamingResponse(
            iter_file(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename={filename}",
                "Content-Length": str(file_size)
            }
        )
    else:
        return FileResponse(
            path=str(file_path),
            media_type="application/pdf",
            filename=filename,
            headers={
                "Content-Disposition": f"inline; filename={filename}"
            }
        )

@router.get("/sample.pdf")
async def serve_sample_pdf():
    """
    Serve a sample PDF for testing WebViewer.
    Creates a simple sample PDF if it doesn't exist.
    """
    sample_path = ARTIFACTS_DIR / "sample.pdf"
    
    if not sample_path.exists():
        # Create a simple sample PDF using reportlab
        try:
            from reportlab.lib.pagesizes import LETTER
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            
            # Ensure artifacts directory exists
            sample_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create sample PDF
            doc = SimpleDocTemplate(str(sample_path), pagesize=LETTER)
            styles = getSampleStyleSheet()
            story = []
            
            # Add content
            story.append(Paragraph("Sample PDF for WebViewer Testing", styles['Title']))
            story.append(Spacer(1, 12))
            story.append(Paragraph("This is a sample PDF document created for testing the Apryse WebViewer integration.", styles['Normal']))
            story.append(Spacer(1, 12))
            story.append(Paragraph("Features to test:", styles['Heading2']))
            story.append(Paragraph("• PDF rendering", styles['Normal']))
            story.append(Paragraph("• SVG overlay functionality", styles['Normal']))
            story.append(Paragraph("• HiL (Highlight in Line) annotations", styles['Normal']))
            story.append(Paragraph("• Page navigation", styles['Normal']))
            story.append(Paragraph("• Annotation management", styles['Normal']))
            
            doc.build(story)
            
        except ImportError:
            raise HTTPException(
                status_code=500, 
                detail="ReportLab not available. Please install with: pip install reportlab"
            )
    
    return FileResponse(
        path=str(sample_path),
        media_type="application/pdf",
        filename="sample.pdf",
        headers={
            "Content-Disposition": "inline; filename=sample.pdf"
        }
    )

@router.get("/project/{pid}/{filename}")
async def serve_project_file(pid: str, filename: str):
    """
    Serve files from a specific project directory.
    """
    project_path = ARTIFACTS_DIR / pid / filename
    
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if not project_path.is_file():
        raise HTTPException(status_code=404, detail="Not a file")
    
    return FileResponse(
        path=str(project_path),
        media_type="application/pdf" if filename.lower().endswith('.pdf') else "application/octet-stream",
        filename=filename
    )

# Mount static files for WebViewer assets
@router.get("/webviewer/{file_path:path}")
async def serve_webviewer_assets(file_path: str):
    """
    Serve WebViewer static assets.
    """
    webviewer_path = Path("frontend/public/lib/webviewer") / file_path
    
    if not webviewer_path.exists():
        raise HTTPException(status_code=404, detail="WebViewer asset not found")
    
    return FileResponse(path=str(webviewer_path))
