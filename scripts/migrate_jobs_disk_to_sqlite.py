#!/usr/bin/env python3
"""
Migration script to migrate legacy JSON job files to SQLite database.

This script scans for any existing JSON job files from earlier versions
and migrates them to the new SQLite database system.

Usage:
    python scripts/migrate_jobs_disk_to_sqlite.py

The script is safe to run multiple times - it uses INSERT OR IGNORE
to avoid duplicate entries.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import sqlite3
from datetime import datetime, timezone

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings
from app.services.db import get_conn


def find_legacy_job_files() -> list[Path]:
    """
    Scan for legacy JSON job files in the artifacts directory.
    
    Returns:
        List of paths to JSON job files
    """
    settings = get_settings()
    artifact_dir = Path(settings.ARTIFACT_DIR)
    job_files = []
    
    # Look for jobs in the old structure: artifacts/**/jobs/*.json
    for job_file in artifact_dir.rglob("jobs/*.json"):
        if job_file.is_file():
            job_files.append(job_file)
    
    return job_files


def parse_legacy_job_file(job_file: Path) -> Optional[Dict[str, Any]]:
    """
    Parse a legacy JSON job file and extract the relevant data.
    
    Args:
        job_file: Path to the JSON job file
        
    Returns:
        Dictionary with job data, or None if parsing fails
    """
    try:
        with open(job_file, 'r') as f:
            data = json.load(f)
        
        # Extract the job ID from the filename (remove .json extension)
        job_id = job_file.stem
        
        # Map the legacy fields to the new database schema
        job_data = {
            'id': job_id,
            'pid': data.get('project_id', 'unknown'),
            'status': data.get('status', 'unknown'),
            'created_at': data.get('created_at'),
            'updated_at': data.get('updated_at'),
            'result_json': None,
            'error_text': data.get('error')
        }
        
        # Handle the result/artifacts field
        if 'result' in data and data['result']:
            job_data['result_json'] = json.dumps(data['result'])
        elif 'artifacts' in data and data['artifacts']:
            job_data['result_json'] = json.dumps(data['artifacts'])
        
        # Ensure timestamps are in ISO format
        for time_field in ['created_at', 'updated_at']:
            if job_data[time_field]:
                # If it's already a string, try to parse and reformat
                if isinstance(job_data[time_field], str):
                    try:
                        # Try to parse the timestamp and convert to ISO format
                        dt = datetime.fromisoformat(job_data[time_field].replace('Z', '+00:00'))
                        job_data[time_field] = dt.isoformat()
                    except ValueError:
                        # If parsing fails, use current time
                        job_data[time_field] = datetime.now(timezone.utc).isoformat()
                else:
                    # If it's not a string, use current time
                    job_data[time_field] = datetime.now(timezone.utc).isoformat()
            else:
                # If no timestamp, use current time
                job_data[time_field] = datetime.now(timezone.utc).isoformat()
        
        return job_data
        
    except (json.JSONDecodeError, IOError) as e:
        print(f"  ⚠️  Failed to parse {job_file}: {e}")
        return None


def migrate_job_to_database(job_data: Dict[str, Any]) -> bool:
    """
    Insert a job record into the SQLite database.
    
    Args:
        job_data: Dictionary with job data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with get_conn() as conn:
            # Use INSERT OR IGNORE to avoid duplicates
            cursor = conn.execute("""
                INSERT OR IGNORE INTO jobs 
                (id, pid, status, created_at, updated_at, result_json, error_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                job_data['id'],
                job_data['pid'],
                job_data['status'],
                job_data['created_at'],
                job_data['updated_at'],
                job_data['result_json'],
                job_data['error_text']
            ))
            
            # Check if a row was actually inserted
            return cursor.rowcount > 0
            
    except sqlite3.Error as e:
        print(f"  ❌ Database error: {e}")
        return False


def main():
    """Main migration function."""
    settings = get_settings()
    print("🔄 Starting migration of legacy JSON job files to SQLite database...")
    print(f"📁 Scanning for job files in: {settings.ARTIFACT_DIR}")
    
    # Find legacy job files
    job_files = find_legacy_job_files()
    
    if not job_files:
        print("✅ No legacy JSON job files found. Migration not needed.")
        return
    
    print(f"📋 Found {len(job_files)} legacy job files to migrate:")
    
    # Process each job file
    migrated_count = 0
    skipped_count = 0
    error_count = 0
    
    for job_file in job_files:
        print(f"  📄 Processing: {job_file.relative_to(Path(settings.ARTIFACT_DIR))}")
        
        # Parse the job file
        job_data = parse_legacy_job_file(job_file)
        if not job_data:
            error_count += 1
            continue
        
        # Migrate to database
        if migrate_job_to_database(job_data):
            migrated_count += 1
            print(f"    ✅ Migrated job {job_data['id']}")
        else:
            skipped_count += 1
            print(f"    ⏭️  Skipped job {job_data['id']} (already exists)")
    
    # Print summary
    print("\n" + "="*50)
    print("📊 Migration Summary:")
    print(f"  Total files found: {len(job_files)}")
    print(f"  Successfully migrated: {migrated_count}")
    print(f"  Skipped (already exists): {skipped_count}")
    print(f"  Errors: {error_count}")
    
    if migrated_count > 0:
        print(f"\n✅ Successfully migrated {migrated_count} jobs to SQLite database!")
        print("💡 You can now safely delete the old JSON job files if desired.")
    elif skipped_count > 0:
        print(f"\nℹ️  All {skipped_count} jobs were already in the database.")
    else:
        print(f"\n⚠️  No jobs were successfully migrated due to errors.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Migration interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Migration failed with error: {e}")
        sys.exit(1)
