# backend/app/db/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.sql import func
from .core import Base

class CountItem(Base):
    __tablename__ = "count_items"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, index=True)
    subtype = Column(String, index=True)
    name = Column(String)
    quantity = Column(Float)
    unit = Column(String)
    attributes = Column(Text)  # JSON string
    source_hash = Column(String, index=True)
    source_sheet = Column(String, index=True)
    source_geom_id = Column(String, index=True)
    session_id = Column(String, index=True)
    created_at = Column(DateTime, default=func.now(), index=True)

class ReviewSession(Base):
    __tablename__ = "review_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    sheet_ref = Column(String)
    status = Column(String, index=True)
    payload = Column(Text)  # JSON string
    created_at = Column(DateTime, default=func.now(), index=True)
