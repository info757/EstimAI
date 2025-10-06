"""
Security middleware for request size limits, timeouts, and rate limiting.
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Configuration constants
MAX_REQUEST_SIZE = 50 * 1024 * 1024  # 50MB
REQUEST_TIMEOUT = 300  # 5 minutes
RATE_LIMIT_WINDOW = 60  # 1 minute
RATE_LIMIT_MAX_REQUESTS = 100  # 100 requests per minute per IP

# Rate limiting storage (in production, use Redis)
_rate_limit_storage = {}


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for request validation and rate limiting."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.max_request_size = MAX_REQUEST_SIZE
        self.request_timeout = REQUEST_TIMEOUT
        self.rate_limit_window = RATE_LIMIT_WINDOW
        self.rate_limit_max_requests = RATE_LIMIT_MAX_REQUESTS
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with security checks."""
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        
        try:
            # Rate limiting check
            if not self._check_rate_limit(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Limit: {self.rate_limit_max_requests} per {self.rate_limit_window}s",
                        "retry_after": self.rate_limit_window
                    }
                )
            
            # Request size check
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_request_size:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": "Request too large",
                        "message": f"Request size exceeds {self.max_request_size / (1024*1024):.1f}MB limit",
                        "max_size_mb": self.max_request_size / (1024*1024)
                    }
                )
            
            # Process request with timeout
            response = await self._process_with_timeout(request, call_next)
            
            # Add security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": "Request processing failed"
                }
            )
        finally:
            # Log request timing
            duration = time.time() - start_time
            if duration > 1.0:  # Log slow requests
                logger.warning(f"Slow request: {request.method} {request.url} took {duration:.2f}s")
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """Check if client is within rate limit."""
        current_time = time.time()
        window_start = current_time - self.rate_limit_window
        
        # Clean old entries
        if client_ip in _rate_limit_storage:
            _rate_limit_storage[client_ip] = [
                timestamp for timestamp in _rate_limit_storage[client_ip]
                if timestamp > window_start
            ]
        else:
            _rate_limit_storage[client_ip] = []
        
        # Check if under limit
        if len(_rate_limit_storage[client_ip]) >= self.rate_limit_max_requests:
            return False
        
        # Add current request
        _rate_limit_storage[client_ip].append(current_time)
        return True
    
    async def _process_with_timeout(self, request: Request, call_next: Callable) -> Response:
        """Process request with timeout protection."""
        import asyncio
        
        try:
            # Create timeout task
            timeout_task = asyncio.create_task(
                asyncio.sleep(self.request_timeout)
            )
            
            # Create request task
            request_task = asyncio.create_task(call_next(request))
            
            # Wait for either completion or timeout
            done, pending = await asyncio.wait(
                [timeout_task, request_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Check if timeout occurred
            if timeout_task in done:
                raise HTTPException(
                    status_code=408,
                    detail={
                        "error": "Request timeout",
                        "message": f"Request exceeded {self.request_timeout}s timeout"
                    }
                )
            
            # Return response
            return request_task.result()
            
        except asyncio.CancelledError:
            raise HTTPException(
                status_code=408,
                detail={
                    "error": "Request cancelled",
                    "message": "Request was cancelled due to timeout"
                }
            )


class StructuredErrorHandler:
    """Structured error response handler."""
    
    @staticmethod
    def create_error_response(
        status_code: int,
        error_type: str,
        message: str,
        details: dict = None
    ) -> JSONResponse:
        """Create structured error response."""
        content = {
            "error": error_type,
            "message": message,
            "status_code": status_code,
            "timestamp": time.time()
        }
        
        if details:
            content["details"] = details
        
        return JSONResponse(
            status_code=status_code,
            content=content
        )
    
    @staticmethod
    def validation_error(message: str, field_errors: dict = None) -> JSONResponse:
        """Create validation error response."""
        return StructuredErrorHandler.create_error_response(
            status_code=422,
            error_type="validation_error",
            message=message,
            details={"field_errors": field_errors} if field_errors else None
        )
    
    @staticmethod
    def not_found_error(resource: str, identifier: str = None) -> JSONResponse:
        """Create not found error response."""
        message = f"{resource} not found"
        if identifier:
            message += f" with identifier: {identifier}"
        
        return StructuredErrorHandler.create_error_response(
            status_code=404,
            error_type="not_found",
            message=message
        )
    
    @staticmethod
    def server_error(message: str = "Internal server error") -> JSONResponse:
        """Create server error response."""
        return StructuredErrorHandler.create_error_response(
            status_code=500,
            error_type="server_error",
            message=message
        )