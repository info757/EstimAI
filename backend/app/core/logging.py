"""
Structured JSON logging configuration for EstimAI.

This module provides structured JSON logging with consistent fields
for production monitoring and debugging.
"""
import json
import logging
import logging.config
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar

# Context variables for request-scoped data
request_context: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})

# Custom JSON formatter
class JSONFormatter(logging.Formatter):
    """Format log records as single-line JSON for production monitoring."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Base log data
        log_data = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
            "pid": os.getpid(),
        }
        
        # Add request context if available
        try:
            context = request_context.get()
            if context:
                log_data.update(context)
        except LookupError:
            pass
        
        # Add extra fields from record
        if hasattr(record, 'job_id'):
            log_data['job_id'] = record.job_id
        if hasattr(record, 'project_id'):
            log_data['project_id'] = record.project_id
        if hasattr(record, 'path'):
            log_data['path'] = record.path
        if hasattr(record, 'method'):
            log_data['method'] = record.method
        if hasattr(record, 'status'):
            log_data['status'] = record.status
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        if hasattr(record, 'from_state'):
            log_data['from_state'] = record.from_state
        if hasattr(record, 'to_state'):
            log_data['to_state'] = record.to_state
        if hasattr(record, 'result'):
            log_data['result'] = record.result
        if hasattr(record, 'error'):
            log_data['error'] = record.error
            
        # Add exception info if present
        if record.exc_info:
            log_data['error'] = self.formatException(record.exc_info)
            
        return json.dumps(log_data, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """
    Configure logging with structured JSON output.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create formatter
    formatter = JSONFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)


def json_logger(name: str) -> logging.Logger:
    """
    Get a logger configured for structured JSON output.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance configured for JSON output
    """
    return logging.getLogger(name)


def log_job_transition(
    logger: logging.Logger,
    job_id: str,
    project_id: str,
    from_state: str,
    to_state: str,
    duration_ms: Optional[float] = None,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    level: str = "INFO"
) -> None:
    """
    Log a job state transition with structured data.
    
    Args:
        logger: Logger instance
        job_id: Job identifier
        project_id: Project identifier
        from_state: Previous job state
        to_state: New job state
        duration_ms: Duration in milliseconds
        result: Result data dictionary
        error: Error message (truncated to 1k chars)
        level: Log level
    """
    # Truncate error message if too long
    if error and len(error) > 1000:
        error = error[:997] + "..."
    
    # Create log record with extra fields
    extra = {
        'job_id': job_id,
        'project_id': project_id,
        'from_state': from_state,
        'to_state': to_state,
        'log_type': 'job_transition'
    }
    
    if duration_ms is not None:
        extra['duration_ms'] = round(duration_ms, 2)
    if result:
        extra['result'] = result
    if error:
        extra['error'] = error
        level = "ERROR"
    
    # Log with appropriate level
    log_method = getattr(logger, level.lower())
    log_method("Job transition", extra=extra)


def set_request_context(**kwargs) -> None:
    """
    Set request context for logging.
    
    Args:
        **kwargs: Context variables to set
    """
    current = request_context.get()
    current.update(kwargs)
    request_context.set(current)


def clear_request_context() -> None:
    """Clear request context."""
    request_context.set({})
