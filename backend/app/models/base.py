"""SQLAlchemy 2.x models for EstimAI."""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Enum as SQLEnum
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy import JSON as GenericJSON
from sqlalchemy.sql import func
from ..db import Base

# Use SQLite JSON if available, fallback to generic JSON
try:
    JSON = SQLiteJSON
except ImportError:
    JSON = GenericJSON

class CountStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"

class CountItem(Base):
    __tablename__ = "count_items"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    file = Column(String, nullable=False, index=True)
    page = Column(Integer, nullable=False, index=True)
    type = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    x_pdf = Column(Float, nullable=False)
    y_pdf = Column(Float, nullable=False)
    points_per_foot = Column(Float, nullable=False)
    status = Column(SQLEnum(CountStatus), nullable=False, default=CountStatus.PENDING)
    reviewer_note = Column(Text, nullable=True)
    x_pdf_edited = Column(Float, nullable=True)
    y_pdf_edited = Column(Float, nullable=True)
    type_edited = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ReviewSession(Base):
    __tablename__ = "review_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    file = Column(String, nullable=False, index=True)
    pages = Column(JSON, nullable=False)
    points_per_foot = Column(Float, nullable=False)
    metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
