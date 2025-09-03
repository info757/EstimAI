"""
SQLite database service for job storage.

This module provides a SQLite-based job store to replace JSON file persistence.
"""
import sqlite3
import json
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime, timezone

from ..core.paths import jobs_db_path
from ..core.logging import json_logger

logger = json_logger(__name__)


def _utcnow() -> str:
    """Get current UTC time as ISO8601 string."""
    return datetime.now(timezone.utc).isoformat()


def get_conn() -> sqlite3.Connection:
    """
    Get a database connection with proper configuration.
    
    Returns:
        sqlite3.Connection: Configured database connection
    """
    db_path = jobs_db_path()
    
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(str(db_path))
    
    # Configure connection for better performance and reliability
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    
    # Set row factory to return dictionaries
    conn.row_factory = sqlite3.Row
    
    # Create table if it doesn't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            pid TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            result_json TEXT,
            error_text TEXT
        )
    """)
    
    # Create index for project_id lookups
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_project_id 
        ON jobs(pid)
    """)
    
    # Create index for status lookups
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_status 
        ON jobs(status)
    """)
    
    conn.commit()
    return conn


def create_job(job_id: str, pid: str, status: str, created_at: str) -> None:
    """
    Create a new job record in the database.
    
    Args:
        job_id: Unique job identifier
        pid: Project identifier
        status: Job status
        created_at: Creation timestamp (ISO8601)
    """
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO jobs (id, pid, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (job_id, pid, status, created_at, created_at))
        conn.commit()
    
    logger.info("Job created", extra={
        'job_id': job_id,
        'project_id': pid,
        'status': status,
        'db_operation': 'create'
    })


def update_job(
    job_id: str, 
    status: str, 
    updated_at: str, 
    result_json: Optional[str] = None, 
    error_text: Optional[str] = None
) -> None:
    """
    Update an existing job record in the database.
    
    Args:
        job_id: Job identifier to update
        status: New job status
        updated_at: Update timestamp (ISO8601)
        result_json: Optional JSON result data
        error_text: Optional error message
    """
    with get_conn() as conn:
        conn.execute("""
            UPDATE jobs 
            SET status = ?, updated_at = ?, result_json = ?, error_text = ?
            WHERE id = ?
        """, (status, updated_at, result_json, error_text, job_id))
        conn.commit()
    
    logger.info("Job updated", extra={
        'job_id': job_id,
        'status': status,
        'db_operation': 'update',
        'has_result': result_json is not None,
        'has_error': error_text is not None
    })


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a job record from the database.
    
    Args:
        job_id: Job identifier to retrieve
        
    Returns:
        dict: Job record as dictionary, or None if not found
    """
    with get_conn() as conn:
        cursor = conn.execute("""
            SELECT id, pid, status, created_at, updated_at, result_json, error_text
            FROM jobs WHERE id = ?
        """, (job_id,))
        
        row = cursor.fetchone()
        if row is None:
            return None
        
        # Convert sqlite3.Row to dict
        job_dict = dict(row)
        
        # Parse JSON fields if present
        if job_dict['result_json']:
            try:
                job_dict['result'] = json.loads(job_dict['result_json'])
            except json.JSONDecodeError:
                logger.warning("Failed to parse result_json for job", extra={
                    'job_id': job_id,
                    'result_json': job_dict['result_json']
                })
                job_dict['result'] = None
        else:
            job_dict['result'] = None
        
        # Remove the raw JSON field
        del job_dict['result_json']
        
        return job_dict


def list_jobs(project_id: Optional[str] = None) -> list[Dict[str, Any]]:
    """
    List all jobs, optionally filtered by project_id.
    
    Args:
        project_id: Optional project ID filter
        
    Returns:
        list: List of job dictionaries
    """
    with get_conn() as conn:
        if project_id:
            cursor = conn.execute("""
                SELECT id, pid, status, created_at, updated_at, result_json, error_text
                FROM jobs WHERE pid = ? ORDER BY created_at DESC
            """, (project_id,))
        else:
            cursor = conn.execute("""
                SELECT id, pid, status, created_at, updated_at, result_json, error_text
                FROM jobs ORDER BY created_at DESC
            """)
        
        jobs = []
        for row in cursor.fetchall():
            job_dict = dict(row)
            
            # Parse JSON fields if present
            if job_dict['result_json']:
                try:
                    job_dict['result'] = json.loads(job_dict['result_json'])
                except json.JSONDecodeError:
                    job_dict['result'] = None
            else:
                job_dict['result'] = None
            
            # Remove the raw JSON field
            del job_dict['result_json']
            
            jobs.append(job_dict)
        
        return jobs


def delete_job(job_id: str) -> bool:
    """
    Delete a job record from the database.
    
    Args:
        job_id: Job identifier to delete
        
    Returns:
        bool: True if job was deleted, False if not found
    """
    with get_conn() as conn:
        cursor = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        conn.commit()
        
        deleted = cursor.rowcount > 0
        
        if deleted:
            logger.info("Job deleted", extra={
                'job_id': job_id,
                'db_operation': 'delete'
            })
        
        return deleted


def get_job_count(project_id: Optional[str] = None) -> int:
    """
    Get the count of jobs, optionally filtered by project_id.
    
    Args:
        project_id: Optional project ID filter
        
    Returns:
        int: Number of jobs
    """
    with get_conn() as conn:
        if project_id:
            cursor = conn.execute("SELECT COUNT(*) FROM jobs WHERE pid = ?", (project_id,))
        else:
            cursor = conn.execute("SELECT COUNT(*) FROM jobs")
        
        return cursor.fetchone()[0]
