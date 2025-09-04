#!/usr/bin/env python3
"""
Demo reset script for EstimAI.
Clears demo artifacts and reseeds the environment.
"""

import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

def get_demo_project_id() -> str:
    """Get demo project ID from environment or default."""
    return os.getenv("DEMO_PROJECT_ID", "demo")

def get_artifacts_root() -> Path:
    """Get the artifacts root directory."""
    from ..core.config import get_settings
    settings = get_settings()
    return Path(settings.ARTIFACT_DIR)

def clear_demo_artifacts(demo_pid: str) -> int:
    """Clear all artifacts under the demo project directory."""
    artifacts_root = get_artifacts_root()
    demo_dir = artifacts_root / demo_pid
    
    if not demo_dir.exists():
        logger.info(f"Demo directory doesn't exist: {demo_dir}")
        return 0
    
    # Count files before deletion
    file_count = 0
    for root, dirs, files in os.walk(demo_dir):
        file_count += len(files)
    
    # Remove the entire demo directory
    shutil.rmtree(demo_dir)
    logger.info(f"🗑️  Removed demo artifacts directory: {demo_dir}")
    
    return file_count

def clear_demo_database_rows(demo_pid: str) -> Dict[str, int]:
    """Clear demo project rows from database tables."""
    from ..core.paths import jobs_db_path
    
    db_path = jobs_db_path()
    if not db_path.exists():
        logger.info("Jobs database doesn't exist, skipping database cleanup")
        return {}
    
    deleted_counts = {}
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        
        # Get list of tables
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row['name'] for row in cursor.fetchall()]
        
        for table in tables:
            try:
                # Check if table has project_id column
                cursor = conn.execute(f"PRAGMA table_info({table})")
                columns = [col['name'] for col in cursor.fetchall()]
                
                if 'project_id' in columns:
                    # Delete rows where project_id matches demo_pid
                    cursor = conn.execute(f"DELETE FROM {table} WHERE project_id = ?", (demo_pid,))
                    deleted_count = cursor.rowcount
                    if deleted_count > 0:
                        deleted_counts[table] = deleted_count
                        logger.info(f"🗑️  Deleted {deleted_count} rows from {table}")
                
                elif 'pid' in columns:
                    # Alternative column name
                    cursor = conn.execute(f"DELETE FROM {table} WHERE pid = ?", (demo_pid,))
                    deleted_count = cursor.rowcount
                    if deleted_count > 0:
                        deleted_counts[table] = deleted_count
                        logger.info(f"🗑️  Deleted {deleted_count} rows from {table}")
                        
            except Exception as e:
                logger.warning(f"⚠️  Could not clean table {table}: {e}")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Database cleanup failed: {e}")
    
    return deleted_counts

def recreate_demo_directories(demo_pid: str) -> None:
    """Recreate necessary demo project directories."""
    from ..core.paths import ensure_demo_project_structure
    
    try:
        ensure_demo_project_structure(demo_pid)
        logger.info(f"📁 Recreated demo project directory structure")
    except Exception as e:
        logger.error(f"❌ Failed to recreate demo directories: {e}")

def run() -> None:
    """Main function to reset the demo environment."""
    demo_pid = get_demo_project_id()
    
    logger.info(f"🔄 Starting demo reset for project: {demo_pid}")
    
    # Clear artifacts
    logger.info("🗑️  Clearing demo artifacts...")
    deleted_files = clear_demo_artifacts(demo_pid)
    
    # Clear database rows
    logger.info("🗑️  Clearing demo database rows...")
    deleted_rows = clear_demo_database_rows(demo_pid)
    
    # Recreate directories
    logger.info("📁 Recreating demo directories...")
    recreate_demo_directories(demo_pid)
    
    # Reseed samples
    logger.info("🌱 Reseeding demo samples...")
    from .seed_demo import run as seed_demo
    seed_demo()
    
    # Summary
    logger.info("✅ Demo reset completed!")
    logger.info(f"📊 Summary:")
    logger.info(f"   • Deleted {deleted_files} artifact files")
    
    if deleted_rows:
        total_rows = sum(deleted_rows.values())
        logger.info(f"   • Deleted {total_rows} database rows from {len(deleted_rows)} tables")
        for table, count in deleted_rows.items():
            logger.info(f"     - {table}: {count} rows")
    else:
        logger.info("   • No database rows deleted")
    
    logger.info(f"   • Recreated directory structure")
    logger.info(f"   • Reseeded sample files")
    logger.info(f"🎉 Demo environment is now fresh and ready!")

if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    run()
