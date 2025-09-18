#!/usr/bin/env python3
"""
Database cleanup script for demo records.

This script removes all records with project_id == "demo" from the database.
It's idempotent and safe to run multiple times.

Usage:
    python -m backend.app.scripts.cleanup_demo_records
"""

import sys
import logging
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(backend_dir))

from app.services.db import get_conn
from app.core.paths import jobs_db_path

logger = logging.getLogger(__name__)


def cleanup_demo_records():
    """
    Remove all records with project_id == "demo" from the database.
    
    Returns:
        dict: Summary of deleted records
    """
    conn = get_conn()
    cursor = conn.cursor()
    
    deleted_counts = {}
    
    try:
        # Delete from jobs table
        cursor.execute("DELETE FROM jobs WHERE pid = ?", ("demo",))
        deleted_counts["jobs"] = cursor.rowcount
        
        # Note: The current database schema only has a 'jobs' table.
        # If other tables are added in the future that reference project_id,
        # they should be cleaned up here as well.
        
        conn.commit()
        
        logger.info(f"Demo cleanup completed: {deleted_counts}")
        return deleted_counts
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Demo cleanup failed: {e}")
        raise
    finally:
        conn.close()


def run():
    """Main entry point for the cleanup script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        deleted_counts = cleanup_demo_records()
        total_deleted = sum(deleted_counts.values())
        
        if total_deleted > 0:
            print(f"✅ Cleaned up {total_deleted} demo records:")
            for table, count in deleted_counts.items():
                if count > 0:
                    print(f"   - {table}: {count} records")
        else:
            print("✅ No demo records found to clean up")
            
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()
