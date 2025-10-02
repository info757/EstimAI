"""Database configuration and session management for SQLAlchemy 2.x."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator
from .core.config import settings

# Create engine with future=True for SQLAlchemy 2.x compatibility
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite specific
    future=True
)

# Create session factory with future=True
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True
)

# Declarative base for models
Base = declarative_base()

def get_db() -> Generator:
    """Dependency to get database session with proper cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """Initialize database by creating all tables."""
    Base.metadata.create_all(bind=engine)
