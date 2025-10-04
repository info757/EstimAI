"""
Security middleware for request size limits, rate limiting, and structured errors.

Provides production-ready safeguards for API stability and demo protection.
"""
import time
import logging
from typing import Dict, Any, Optional
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for request validation and rate limiting."""
    
    def __init__(self, app, max_request_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_request_size = max_request_size
        self.rate_limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["1000/hour", "100/minute"]
        )
    
    async def dispatch(self, request: Request, call_next):
        """Process request with security checks."""
        try:
            # Check request size
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_request_size:
                return self._create_error_response(
                    "REQUEST_TOO_LARGE",
                    f"Request size exceeds limit of {self.max_request_size} bytes",
                    413
                )
            
            # Check rate limits
            try:
                await self.rate_limiter.check_rate_limit(request)
            except RateLimitExceeded:
                return self._create_error_response(
                    "RATE_LIMIT_EXCEEDED",
                    "Too many requests. Please try again later.",
                    429
                )
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            
            return response
            
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            return self._create_error_response(
                "INTERNAL_ERROR",
                "An internal error occurred",
                500
            )
    
    def _create_error_response(self, error_code: str, message: str, status_code: int) -> JSONResponse:
        """Create structured error response."""
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": error_code,
                    "message": message,
                    "timestamp": time.time(),
                    "request_id": None  # Could be added for tracing
                }
            }
        )


class RequestSizeLimiter:
    """Request size limiting utility."""
    
    def __init__(self, max_size: int = 10 * 1024 * 1024):  # 10MB
        self.max_size = max_size
    
    async def __call__(self, request: Request, call_next):
        """Check request size before processing."""
        content_length = request.headers.get("content-length")
        
        if content_length:
            size = int(content_length)
            if size > self.max_size:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "REQUEST_TOO_LARGE",
                            "message": f"Request size {size} bytes exceeds limit of {self.max_size} bytes",
                            "max_size": self.max_size,
                            "actual_size": size
                        }
                    }
                )
        
        return await call_next(request)


class RateLimiter:
    """Rate limiting utility with different limits for different endpoints."""
    
    def __init__(self):
        self.limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["1000/hour", "100/minute"]
        )
        
        # Specific limits for different endpoint types
        self.endpoint_limits = {
            "/v1/detect": ["10/minute", "100/hour"],
            "/v1/takeoff/pdf": ["5/minute", "50/hour"],
            "/v1/export/summary": ["20/minute", "200/hour"],
            "/v1/review/commit": ["30/minute", "300/hour"],
            "/v1/counts": ["100/minute", "1000/hour"],
            "/v1/agent/takeoff": ["3/minute", "30/hour"]
        }
    
    def get_limits_for_path(self, path: str) -> list:
        """Get rate limits for specific path."""
        for endpoint, limits in self.endpoint_limits.items():
            if path.startswith(endpoint):
                return limits
        return self.limiter.default_limits
    
    async def check_rate_limit(self, request: Request):
        """Check rate limit for request."""
        path = request.url.path
        limits = self.get_limits_for_path(path)
        
        # Apply specific limits
        self.limiter.limits = limits
        await self.limiter.check_rate_limit(request)


class StructuredErrorHandler:
    """Structured error handling for consistent API responses."""
    
    @staticmethod
    def create_error_response(
        error_code: str,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """Create structured error response."""
        error_data = {
            "error": {
                "code": error_code,
                "message": message,
                "timestamp": time.time(),
                "status_code": status_code
            }
        }
        
        if details:
            error_data["error"]["details"] = details
        
        return JSONResponse(
            status_code=status_code,
            content=error_data
        )
    
    @staticmethod
    def handle_validation_error(exc: Exception) -> JSONResponse:
        """Handle Pydantic validation errors."""
        return StructuredErrorHandler.create_error_response(
            "VALIDATION_ERROR",
            "Request validation failed",
            422,
            {"validation_errors": str(exc)}
        )
    
    @staticmethod
    def handle_database_error(exc: Exception) -> JSONResponse:
        """Handle database errors."""
        logger.error(f"Database error: {exc}")
        return StructuredErrorHandler.create_error_response(
            "DATABASE_ERROR",
            "Database operation failed",
            500,
            {"error_type": type(exc).__name__}
        )
    
    @staticmethod
    def handle_file_error(exc: Exception) -> JSONResponse:
        """Handle file operation errors."""
        return StructuredErrorHandler.create_error_response(
            "FILE_ERROR",
            "File operation failed",
            400,
            {"error_type": type(exc).__name__}
        )
    
    @staticmethod
    def handle_llm_error(exc: Exception) -> JSONResponse:
        """Handle LLM service errors."""
        return StructuredErrorHandler.create_error_response(
            "LLM_ERROR",
            "AI service temporarily unavailable",
            503,
            {"error_type": type(exc).__name__}
        )


class DemoModeMiddleware:
    """Demo mode middleware for development and testing."""
    
    def __init__(self, demo_mode: bool = False):
        self.demo_mode = demo_mode
        self.demo_limits = {
            "max_file_size": 5 * 1024 * 1024,  # 5MB
            "max_requests_per_minute": 10,
            "max_requests_per_hour": 100
        }
    
    async def __call__(self, request: Request, call_next):
        """Apply demo mode restrictions."""
        if not self.demo_mode:
            return await call_next(request)
        
        # Add demo mode headers
        response = await call_next(request)
        response.headers["X-Demo-Mode"] = "true"
        response.headers["X-Demo-Limits"] = str(self.demo_limits)
        
        return response


# Global instances
_security_middleware = None
_rate_limiter = None
_error_handler = None


def get_security_middleware() -> SecurityMiddleware:
    """Get global security middleware instance."""
    global _security_middleware
    if _security_middleware is None:
        _security_middleware = SecurityMiddleware(
            app=None,  # Will be set by FastAPI
            max_request_size=getattr(settings, 'MAX_REQUEST_SIZE', 10 * 1024 * 1024)
        )
    return _security_middleware


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def get_error_handler() -> StructuredErrorHandler:
    """Get global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = StructuredErrorHandler()
    return _error_handler
