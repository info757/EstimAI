"""HTTP extract bridge for calling existing /v1/takeoff/pdf route internally.

This bridge allows the agent to reuse the already-working FastAPI route as a fallback
when the direct pipeline implementation is not available. This is a pragmatic MVP
solution that can be kept or removed once the pipeline is stabilized.
"""
from __future__ import annotations
from typing import Optional, Dict, Any
import pathlib
import logging
from fastapi.testclient import TestClient

logger = logging.getLogger(__name__)

_client: Optional[TestClient] = None


def _client_singleton() -> TestClient:
    """Get or create a singleton TestClient instance."""
    global _client
    if _client is None:
        # Separate in-memory app instance; fine for a bridge in dev/MVP
        from backend.app.app import create_app
        _client = TestClient(create_app())
        logger.info("Created TestClient singleton for HTTP extract bridge")
    return _client


def extract_via_route(file_ref: str, max_pages: Optional[int] = None) -> Dict[str, Any]:
    """
    Calls the existing /v1/takeoff/pdf route with the given file.
    
    This function acts as a bridge to reuse the already-working FastAPI route,
    allowing the agent to process files even when the direct pipeline implementation
    is not available.
    
    Args:
        file_ref: Path to the PDF file to process
        max_pages: Optional maximum number of pages to process
        
    Returns:
        Parsed JSON response from the route (should include networks/...)
        
    Raises:
        FileNotFoundError: If the file_ref doesn't exist
        HTTPError: If the route returns an error status
    """
    path = pathlib.Path(file_ref)
    if not path.exists():
        raise FileNotFoundError(f"file_ref not found: {file_ref}")

    logger.info(f"Calling /v1/takeoff/pdf via HTTP bridge for: {path.name}")
    
    with path.open("rb") as f:
        files = {"file": (path.name, f, "application/pdf")}
        params = {}
        if max_pages is not None:
            params["max_pages"] = str(max_pages)

        resp = _client_singleton().post("/v1/takeoff/pdf", files=files, params=params)
        resp.raise_for_status()
        
    result = resp.json()
    logger.info(f"HTTP bridge succeeded: {len(result.get('networks', {}))} networks")
    return result

