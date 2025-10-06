"""
Structured error handlers for consistent API responses.
"""
import logging
import traceback
from typing import Union, Dict, Any
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ErrorResponse:
    """Structured error response builder."""
    
    @staticmethod
    def create(
        status_code: int,
        error_type: str,
        message: str,
        details: Dict[str, Any] = None,
        request_id: str = None
    ) -> JSONResponse:
        """Create structured error response."""
        content = {
            "error": {
                "type": error_type,
                "message": message,
                "status_code": status_code
            },
            "timestamp": __import__("time").time(),
            "path": None,  # Will be set by handler
            "request_id": request_id
        }
        
        if details:
            content["error"]["details"] = details
        
        return JSONResponse(
            status_code=status_code,
            content=content
        )
    
    @staticmethod
    def validation_error(
        message: str,
        field_errors: Dict[str, Any] = None,
        request_id: str = None
    ) -> JSONResponse:
        """Create validation error response."""
        return ErrorResponse.create(
            status_code=422,
            error_type="validation_error",
            message=message,
            details={"field_errors": field_errors} if field_errors else None,
            request_id=request_id
        )
    
    @staticmethod
    def not_found(
        resource: str,
        identifier: str = None,
        request_id: str = None
    ) -> JSONResponse:
        """Create not found error response."""
        message = f"{resource} not found"
        if identifier:
            message += f" with identifier: {identifier}"
        
        return ErrorResponse.create(
            status_code=404,
            error_type="not_found",
            message=message,
            request_id=request_id
        )
    
    @staticmethod
    def server_error(
        message: str = "Internal server error",
        request_id: str = None,
        include_traceback: bool = False
    ) -> JSONResponse:
        """Create server error response."""
        details = None
        if include_traceback:
            details = {"traceback": traceback.format_exc()}
        
        return ErrorResponse.create(
            status_code=500,
            error_type="server_error",
            message=message,
            details=details,
            request_id=request_id
        )
    
    @staticmethod
    def rate_limit_exceeded(
        retry_after: int = 60,
        request_id: str = None
    ) -> JSONResponse:
        """Create rate limit exceeded response."""
        return ErrorResponse.create(
            status_code=429,
            error_type="rate_limit_exceeded",
            message="Too many requests",
            details={"retry_after": retry_after},
            request_id=request_id
        )
    
    @staticmethod
    def request_too_large(
        max_size_mb: float,
        request_id: str = None
    ) -> JSONResponse:
        """Create request too large response."""
        return ErrorResponse.create(
            status_code=413,
            error_type="request_too_large",
            message=f"Request size exceeds {max_size_mb:.1f}MB limit",
            details={"max_size_mb": max_size_mb},
            request_id=request_id
        )
    
    @staticmethod
    def timeout(
        timeout_seconds: int,
        request_id: str = None
    ) -> JSONResponse:
        """Create timeout response."""
        return ErrorResponse.create(
            status_code=408,
            error_type="timeout",
            message=f"Request exceeded {timeout_seconds}s timeout",
            details={"timeout_seconds": timeout_seconds},
            request_id=request_id
        )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with structured responses."""
    request_id = getattr(request.state, 'request_id', None)
    
    # Extract error details from exception
    if hasattr(exc, 'detail') and isinstance(exc.detail, dict):
        error_type = exc.detail.get('error', 'http_error')
        message = exc.detail.get('message', str(exc.detail))
        details = exc.detail.get('details')
    else:
        error_type = 'http_error'
        message = str(exc.detail) if exc.detail else "HTTP error occurred"
        details = None
    
    response = ErrorResponse.create(
        status_code=exc.status_code,
        error_type=error_type,
        message=message,
        details=details,
        request_id=request_id
    )
    
    # Add path information
    response.body = response.body.decode('utf-8').replace(
        '"path": null',
        f'"path": "{request.url.path}"'
    ).encode('utf-8')
    
    return response


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation exceptions with structured responses."""
    request_id = getattr(request.state, 'request_id', None)
    
    # Extract field errors
    field_errors = {}
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        field_errors[field_path] = {
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        }
    
    response = ErrorResponse.validation_error(
        message="Request validation failed",
        field_errors=field_errors,
        request_id=request_id
    )
    
    # Add path information
    response.body = response.body.decode('utf-8').replace(
        '"path": null',
        f'"path": "{request.url.path}"'
    ).encode('utf-8')
    
    return response


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions with structured responses."""
    request_id = getattr(request.state, 'request_id', None)
    
    # Log the exception
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    response = ErrorResponse.server_error(
        message="An unexpected error occurred",
        request_id=request_id,
        include_traceback=True
    )
    
    # Add path information
    response.body = response.body.decode('utf-8').replace(
        '"path": null',
        f'"path": "{request.url.path}"'
    ).encode('utf-8')
    
    return response


def setup_error_handlers(app):
    """Setup error handlers for the FastAPI app."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Error handlers configured")
