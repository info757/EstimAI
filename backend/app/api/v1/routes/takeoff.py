from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.app.core.config import settings

router = APIRouter(prefix="/v1/takeoff", tags=["takeoff"])

@router.post("/pdf")
async def takeoff_pdf(file: UploadFile = File(...)):
    if not settings.APR_USE_APRYSE:
        raise HTTPException(status_code=422, detail="Apryse disabled (set APR_USE_APRYSE=1)")
    # TODO: call your Apryse pipeline and return EstimAIResult
    return {"sheet_units":"ft","networks":{},"roadway":{},"e_sc":{},"earthwork":{},"qa_flags":[]}
