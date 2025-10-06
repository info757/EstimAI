"""
Database migration utilities for adding indices and optimizing performance.
"""
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# SQLite indices for performance optimization
INDICES = [
    # Counts table indices
    "CREATE INDEX IF NOT EXISTS idx_counts_category ON counts(category);",
    "CREATE INDEX IF NOT EXISTS idx_counts_subtype ON counts(subtype);",
    "CREATE INDEX IF NOT EXISTS idx_counts_quantity ON counts(quantity);",
    "CREATE INDEX IF NOT EXISTS idx_counts_created_at ON counts(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_counts_session_id ON counts(session_id);",
    
    # Reviews table indices
    "CREATE INDEX IF NOT EXISTS idx_reviews_session_id ON reviews(session_id);",
    "CREATE INDEX IF NOT EXISTS idx_reviews_sheet_ref ON reviews(sheet_ref);",
    "CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON reviews(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews(status);",
    
    # Composite indices for common queries
    "CREATE INDEX IF NOT EXISTS idx_counts_category_subtype ON counts(category, subtype);",
    "CREATE INDEX IF NOT EXISTS idx_counts_session_category ON counts(session_id, category);",
    "CREATE INDEX IF NOT EXISTS idx_reviews_session_status ON reviews(session_id, status);",
    
    # Source reference indices
    "CREATE INDEX IF NOT EXISTS idx_counts_source_hash ON counts(source_hash);",
    "CREATE INDEX IF NOT EXISTS idx_counts_source_sheet ON counts(source_sheet);",
    "CREATE INDEX IF NOT EXISTS idx_counts_source_geom_id ON counts(source_geom_id);",
]


def get_db_path() -> Path:
    """Get the database file path."""
    return Path("backend/estimai.db")


def apply_migrations(db_path: str = None) -> List[str]:
    """
    Apply database migrations and indices.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        List of applied migration statements
    """
    if db_path is None:
        db_path = str(get_db_path())
    
    applied_migrations = []
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Apply indices
        for index_sql in INDICES:
            try:
                cursor.execute(index_sql)
                applied_migrations.append(index_sql)
                logger.info(f"Applied index: {index_sql}")
            except sqlite3.Error as e:
                logger.warning(f"Failed to apply index {index_sql}: {e}")
        
        conn.commit()
        logger.info(f"Applied {len(applied_migrations)} database migrations")
        
    except sqlite3.Error as e:
        logger.error(f"Database migration failed: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()
    
    return applied_migrations


def check_indices(db_path: str = None) -> Dict[str, List[str]]:
    """
    Check existing indices in the database.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        Dictionary with table names and their indices
    """
    if db_path is None:
        db_path = str(get_db_path())
    
    indices = {}
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all indices
        cursor.execute("""
            SELECT name, tbl_name, sql 
            FROM sqlite_master 
            WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
            ORDER BY tbl_name, name
        """)
        
        for row in cursor.fetchall():
            name, table, sql = row
            if table not in indices:
                indices[table] = []
            indices[table].append({
                'name': name,
                'sql': sql
            })
        
    except sqlite3.Error as e:
        logger.error(f"Failed to check indices: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()
    
    return indices


def optimize_database(db_path: str = None) -> Dict[str, Any]:
    """
    Optimize database performance.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        Optimization results
    """
    if db_path is None:
        db_path = str(get_db_path())
    
    results = {
        'indices_applied': 0,
        'vacuum_completed': False,
        'analyze_completed': False
    }
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Apply indices
        applied_migrations = apply_migrations(db_path)
        results['indices_applied'] = len(applied_migrations)
        
        # Vacuum database
        cursor.execute("VACUUM")
        results['vacuum_completed'] = True
        logger.info("Database vacuum completed")
        
        # Analyze database
        cursor.execute("ANALYZE")
        results['analyze_completed'] = True
        logger.info("Database analysis completed")
        
        conn.commit()
        
    except sqlite3.Error as e:
        logger.error(f"Database optimization failed: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()
    
    return results


if __name__ == "__main__":
    # Run migrations when script is executed directly
    print("🔧 Applying database migrations...")
    
    try:
        applied = apply_migrations()
        print(f"✅ Applied {len(applied)} migrations")
        
        # Check indices
        indices = check_indices()
        print(f"📊 Found indices for {len(indices)} tables")
        
        for table, table_indices in indices.items():
            print(f"  {table}: {len(table_indices)} indices")
        
        # Optimize database
        results = optimize_database()
        print(f"🚀 Database optimization completed:")
        print(f"  - Indices applied: {results['indices_applied']}")
        print(f"  - Vacuum completed: {results['vacuum_completed']}")
        print(f"  - Analysis completed: {results['analyze_completed']}")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()