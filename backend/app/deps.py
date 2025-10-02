"""Dependencies for FastAPI routes."""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from .db import get_db

def get_current_user():
    """Placeholder for authentication - can be implemented later."""
    # For now, return a mock user
    return {"user_id": "default_user"}

def get_db_session(db: Session = Depends(get_db)):
    """Get database session dependency."""
    return db
