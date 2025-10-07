# backend/app/middleware/security.py
from __future__ import annotations

import logging
from typing import Callable, Optional

from fastapi import Header, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette import status
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware

log = logging.getLogger(__name__)

# --- Exception handler factory -------------------------------------------------
def get_error_handler() -> Callable[[Request, Exception], JSONResponse]:
    """
    Returns a FastAPI/Starlette-compatible exception handler that logs the
    original exception and returns a safe JSON payload.
    Usage:
        app.add_exception_handler(Exception, get_error_handler())
    """
    def _handler(request: Request, exc: Exception) -> JSONResponse:
        log.exception("Unhandled error | path=%s", request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal Server Error"},
        )
    return _handler

# --- Optional: simple API-key gate (no-op if not used) ------------------------
def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    """
    Lightweight dependency you can plug into routes if you want a shared API key.
    Set ESTIMAI_API_KEY in env and add: Depends(require_api_key) to routes.
    """
    import os
    expected = os.getenv("ESTIMAI_API_KEY")
    if expected:
        if not x_api_key or x_api_key != expected:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

# --- Optional: attach common security/CORS middleware -------------------------
def with_security_middleware(orig: list[Middleware] | None = None) -> list[Middleware]:
    """
    Returns a middleware list including permissive CORS for local/dev.
    Call in main.py: app = FastAPI(middleware=with_security_middleware())
    """
    allow_all = ["*"]
    cors = Middleware(
        CORSMiddleware,
        allow_origins=allow_all,
        allow_credentials=True,
        allow_methods=allow_all,
        allow_headers=allow_all,
        max_age=600,
    )
    return ([cors] + (orig or []))

__all__ = ["get_error_handler", "require_api_key", "with_security_middleware"]