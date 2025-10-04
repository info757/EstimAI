"""
Database migration utilities for SQLite.

Provides migration management, index creation, and database optimization
for production stability and demo performance.
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, text, Index, MetaData, Table, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Handles database migrations and optimizations."""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or settings.DATABASE_URL
        self.engine = create_engine(self.database_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)
        self.migrations_dir = Path("migrations")
        self.migrations_dir.mkdir(exist_ok=True)
    
    def create_indices(self):
        """Create database indices for performance optimization."""
        indices = [
            # CountItem indices
            {
                "name": "idx_countitem_file_page",
                "table": "countitem",
                "columns": ["file", "page"],
                "unique": False
            },
            {
                "name": "idx_countitem_type",
                "table": "countitem", 
                "columns": ["type"],
                "unique": False
            },
            {
                "name": "idx_countitem_status",
                "table": "countitem",
                "columns": ["status"],
                "unique": False
            },
            {
                "name": "idx_countitem_confidence",
                "table": "countitem",
                "columns": ["confidence"],
                "unique": False
            },
            {
                "name": "idx_countitem_file_type_status",
                "table": "countitem",
                "columns": ["file", "type", "status"],
                "unique": False
            },
            
            # ReviewSession indices
            {
                "name": "idx_reviewsession_file",
                "table": "reviewsession",
                "columns": ["file"],
                "unique": False
            },
            {
                "name": "idx_reviewsession_created_at",
                "table": "reviewsession",
                "columns": ["created_at"],
                "unique": False
            },
            
            # User indices (if users table exists)
            {
                "name": "idx_user_email",
                "table": "user",
                "columns": ["email"],
                "unique": True
            },
            {
                "name": "idx_user_username",
                "table": "user",
                "columns": ["username"],
                "unique": True
            }
        ]
        
        with self.engine.connect() as conn:
            for index_spec in indices:
                try:
                    self._create_index_if_not_exists(conn, index_spec)
                    logger.info(f"Created index: {index_spec['name']}")
                except Exception as e:
                    logger.warning(f"Failed to create index {index_spec['name']}: {e}")
    
    def _create_index_if_not_exists(self, conn, index_spec: Dict[str, Any]):
        """Create index if it doesn't exist."""
        # Check if index exists
        check_sql = f"""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name='{index_spec['name']}'
        """
        
        result = conn.execute(text(check_sql)).fetchone()
        if result:
            logger.info(f"Index {index_spec['name']} already exists")
            return
        
        # Create index
        columns_str = ", ".join(index_spec['columns'])
        unique_str = "UNIQUE" if index_spec.get('unique', False) else ""
        
        create_sql = f"""
        CREATE {unique_str} INDEX {index_spec['name']} 
        ON {index_spec['table']} ({columns_str})
        """
        
        conn.execute(text(create_sql))
        conn.commit()
    
    def optimize_database(self):
        """Optimize database for performance."""
        with self.engine.connect() as conn:
            try:
                # Analyze tables for query optimization
                conn.execute(text("ANALYZE"))
                logger.info("Database analysis completed")
                
                # Set pragmas for better performance
                pragmas = [
                    "PRAGMA journal_mode=WAL",
                    "PRAGMA synchronous=NORMAL", 
                    "PRAGMA cache_size=10000",
                    "PRAGMA temp_store=MEMORY",
                    "PRAGMA mmap_size=268435456"  # 256MB
                ]
                
                for pragma in pragmas:
                    conn.execute(text(pragma))
                
                logger.info("Database optimization completed")
                
            except Exception as e:
                logger.warning(f"Database optimization failed: {e}")
    
    def create_sample_data(self):
        """Create sample data for demos."""
        sample_data = {
            "count_items": [
                {
                    "file": "demo_site_plan.pdf",
                    "page": 1,
                    "type": "storm_pipe",
                    "confidence": 0.95,
                    "x_pdf": 100.0,
                    "y_pdf": 200.0,
                    "points_per_foot": 50.0,
                    "status": "accepted",
                    "name": "Storm Pipe 12\"",
                    "subtype": "concrete",
                    "quantity": 150.0,
                    "unit": "LF",
                    "attributes": {
                        "diameter_in": 12,
                        "material": "concrete",
                        "avg_depth_ft": 4.5,
                        "buckets_lf": {"0-5": 100, "5-8": 50}
                    }
                },
                {
                    "file": "demo_site_plan.pdf", 
                    "page": 1,
                    "type": "manhole",
                    "confidence": 0.88,
                    "x_pdf": 300.0,
                    "y_pdf": 400.0,
                    "points_per_foot": 50.0,
                    "status": "accepted",
                    "name": "Manhole 4ft",
                    "subtype": "concrete",
                    "quantity": 1.0,
                    "unit": "EA",
                    "attributes": {
                        "diameter_ft": 4,
                        "material": "concrete"
                    }
                },
                {
                    "file": "demo_site_plan.pdf",
                    "page": 1, 
                    "type": "curb",
                    "confidence": 0.92,
                    "x_pdf": 500.0,
                    "y_pdf": 600.0,
                    "points_per_foot": 50.0,
                    "status": "pending",
                    "name": "Concrete Curb",
                    "subtype": "concrete",
                    "quantity": 200.0,
                    "unit": "LF",
                    "attributes": {
                        "material": "concrete",
                        "height_in": 6
                    }
                }
            ],
            "review_sessions": [
                {
                    "id": "demo_session_1",
                    "file": "demo_site_plan.pdf",
                    "pages": [1],
                    "points_per_foot": 50.0,
                    "metrics": {
                        "total_items": 3,
                        "accepted_items": 2,
                        "precision": 0.95,
                        "recall": 0.88,
                        "f1": 0.91
                    }
                }
            ]
        }
        
        with self.Session() as session:
            try:
                # Insert sample count items
                from backend.app.models import CountItem, CountStatus
                
                for item_data in sample_data["count_items"]:
                    # Check if item already exists
                    existing = session.query(CountItem).filter(
                        CountItem.file == item_data["file"],
                        CountItem.page == item_data["page"],
                        CountItem.type == item_data["type"]
                    ).first()
                    
                    if not existing:
                        count_item = CountItem(
                            file=item_data["file"],
                            page=item_data["page"],
                            type=item_data["type"],
                            confidence=item_data["confidence"],
                            x_pdf=item_data["x_pdf"],
                            y_pdf=item_data["y_pdf"],
                            points_per_foot=item_data["points_per_foot"],
                            status=getattr(CountStatus, item_data["status"].upper()),
                            name=item_data["name"],
                            subtype=item_data["subtype"],
                            quantity=item_data["quantity"],
                            unit=item_data["unit"],
                            attributes=item_data["attributes"]
                        )
                        session.add(count_item)
                
                # Insert sample review sessions
                from backend.app.models import ReviewSession
                
                for session_data in sample_data["review_sessions"]:
                    existing = session.query(ReviewSession).filter(
                        ReviewSession.id == session_data["id"]
                    ).first()
                    
                    if not existing:
                        review_session = ReviewSession(
                            id=session_data["id"],
                            file=session_data["file"],
                            pages=session_data["pages"],
                            points_per_foot=session_data["points_per_foot"],
                            metrics=session_data["metrics"]
                        )
                        session.add(review_session)
                
                session.commit()
                logger.info("Sample data created successfully")
                
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to create sample data: {e}")
                raise
    
    def run_migrations(self):
        """Run all database migrations."""
        try:
            logger.info("Starting database migrations...")
            
            # Create indices
            self.create_indices()
            
            # Optimize database
            self.optimize_database()
            
            # Create sample data if in demo mode
            if settings.DEBUG or getattr(settings, 'DEMO_MODE', False):
                self.create_sample_data()
            
            logger.info("Database migrations completed successfully")
            
        except Exception as e:
            logger.error(f"Database migrations failed: {e}")
            raise


# Global migrator instance
_migrator = None


def get_migrator() -> DatabaseMigrator:
    """Get global database migrator instance."""
    global _migrator
    if _migrator is None:
        _migrator = DatabaseMigrator()
    return _migrator


def run_database_migrations():
    """Run database migrations on startup."""
    migrator = get_migrator()
    migrator.run_migrations()
