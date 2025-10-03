#!/usr/bin/env python3
"""Test script for database initialization."""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app.db import init_db, get_db, SessionLocal
from backend.app.models import CountItem, ReviewSession
from backend.app.core.config import settings

def test_db_connection():
    """Test database connection and table creation."""
    print("Testing database connection...")
    
    try:
        # Initialize database
        init_db()
        print("✅ Database initialized successfully")
        
        # Test session creation
        db = SessionLocal()
        print("✅ Database session created successfully")
        
        # Test basic query
        count = db.query(CountItem).count()
        print(f"✅ CountItem table accessible, current count: {count}")
        
        # Test review session query
        session_count = db.query(ReviewSession).count()
        print(f"✅ ReviewSession table accessible, current count: {session_count}")
        
        db.close()
        print("✅ Database session closed successfully")
        
        print(f"\nDatabase URL: {settings.DATABASE_URL}")
        print(f"Files directory: {settings.get_files_dir()}")
        print(f"Templates directory: {settings.get_templates_dir()}")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_db_connection()
    sys.exit(0 if success else 1)
