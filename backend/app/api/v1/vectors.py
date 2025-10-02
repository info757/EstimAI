from fastapi import APIRouter, HTTPException, Query
from app.services.ingest import get_ingestor
from app.domain.dto import PageVectors
import os

router = APIRouter(prefix="/v1")

FILES_DIR = os.getenv("FILES_DIR", "backend/files")

@router.get("/vectors", response_model=PageVectors)
def get_vectors(name: str = Query(...), page: int = Query(0)):
    path = os.path.join(FILES_DIR, name)
    if not os.path.isfile(path):
        raise HTTPException(404, "file not found")
    ing = get_ingestor()
    return ing.read_page(path, page)
