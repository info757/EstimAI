"""
Demo mode configuration and sample data management.

Provides demo mode settings, sample files, and demo-specific features
for stable demonstrations and testing.
"""
import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DemoConfig:
    """Demo mode configuration."""
    enabled: bool = False
    max_file_size: int = 5 * 1024 * 1024  # 5MB
    max_requests_per_minute: int = 10
    max_requests_per_hour: int = 100
    sample_files_dir: str = "sample_files"
    demo_banner_message: str = "DEMO MODE - Limited functionality for demonstration purposes"
    auto_cleanup_interval: int = 3600  # 1 hour
    max_demo_sessions: int = 10


class SampleFileManager:
    """Manages sample files for demos."""
    
    def __init__(self, sample_dir: str = "sample_files"):
        self.sample_dir = Path(sample_dir)
        self.sample_dir.mkdir(exist_ok=True)
        self.sample_files = {}
        self._create_sample_files()
    
    def _create_sample_files(self):
        """Create sample files for demos."""
        sample_files = {
            "demo_site_plan.pdf": {
                "description": "Sample site plan with utilities",
                "size": "2.1MB",
                "features": ["Storm pipes", "Sanitary pipes", "Water lines", "Manholes", "Curb"],
                "page_count": 1,
                "created_for": "Utility infrastructure demo"
            },
            "demo_construction_plans.pdf": {
                "description": "Sample construction plans",
                "size": "3.5MB", 
                "features": ["Roadway", "Sidewalk", "Drainage", "Earthwork"],
                "page_count": 3,
                "created_for": "Sitework demo"
            },
            "demo_utility_plans.pdf": {
                "description": "Sample utility plans",
                "size": "1.8MB",
                "features": ["Electrical", "Telecom", "Gas", "Water"],
                "page_count": 2,
                "created_for": "Multi-utility demo"
            }
        }
        
        for filename, info in sample_files.items():
            file_path = self.sample_dir / filename
            if not file_path.exists():
                # Create placeholder file
                with open(file_path, 'w') as f:
                    f.write(f"# Sample file: {filename}\n")
                    f.write(f"# Description: {info['description']}\n")
                    f.write(f"# Size: {info['size']}\n")
                    f.write(f"# Features: {', '.join(info['features'])}\n")
                    f.write(f"# Pages: {info['page_count']}\n")
                    f.write(f"# Created for: {info['created_for']}\n")
                    f.write("\n# This is a placeholder file for demo purposes.\n")
                    f.write("# In a real implementation, this would be a PDF file.\n")
            
            self.sample_files[filename] = {
                "path": str(file_path),
                "info": info
            }
    
    def get_sample_files(self) -> Dict[str, Any]:
        """Get list of available sample files."""
        return self.sample_files
    
    def get_sample_file_path(self, filename: str) -> Optional[str]:
        """Get path to sample file."""
        if filename in self.sample_files:
            return self.sample_files[filename]["path"]
        return None
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """Clean up old demo files."""
        import time
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for file_path in self.sample_dir.glob("*"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                        logger.info(f"Cleaned up old demo file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up {file_path}: {e}")


class DemoModeManager:
    """Manages demo mode functionality."""
    
    def __init__(self):
        self.config = DemoConfig(
            enabled=getattr(settings, 'DEMO_MODE', False),
            max_file_size=getattr(settings, 'DEMO_MAX_FILE_SIZE', 5 * 1024 * 1024),
            max_requests_per_minute=getattr(settings, 'DEMO_MAX_REQUESTS_PER_MINUTE', 10),
            max_requests_per_hour=getattr(settings, 'DEMO_MAX_REQUESTS_PER_HOUR', 100)
        )
        self.sample_file_manager = SampleFileManager()
        self.active_sessions = {}
    
    def is_demo_mode(self) -> bool:
        """Check if demo mode is enabled."""
        return self.config.enabled
    
    def get_demo_limits(self) -> Dict[str, Any]:
        """Get demo mode limits."""
        return {
            "max_file_size": self.config.max_file_size,
            "max_requests_per_minute": self.config.max_requests_per_minute,
            "max_requests_per_hour": self.config.max_requests_per_hour,
            "max_demo_sessions": self.config.max_demo_sessions
        }
    
    def get_demo_banner(self) -> Dict[str, Any]:
        """Get demo mode banner information."""
        return {
            "enabled": self.is_demo_mode(),
            "message": self.config.demo_banner_message,
            "limits": self.get_demo_limits(),
            "sample_files": list(self.sample_file_manager.get_sample_files().keys())
        }
    
    def register_demo_session(self, session_id: str, user_info: Dict[str, Any] = None):
        """Register a new demo session."""
        if len(self.active_sessions) >= self.config.max_demo_sessions:
            # Remove oldest session
            oldest_session = min(self.active_sessions.keys(), 
                               key=lambda k: self.active_sessions[k]["created_at"])
            del self.active_sessions[oldest_session]
        
        self.active_sessions[session_id] = {
            "created_at": time.time(),
            "user_info": user_info or {},
            "requests_count": 0,
            "last_request": None
        }
    
    def check_demo_limits(self, session_id: str) -> Dict[str, Any]:
        """Check if demo session is within limits."""
        if session_id not in self.active_sessions:
            return {"allowed": False, "reason": "Session not found"}
        
        session = self.active_sessions[session_id]
        current_time = time.time()
        
        # Check hourly limit
        if session["requests_count"] >= self.config.max_requests_per_hour:
            return {"allowed": False, "reason": "Hourly limit exceeded"}
        
        # Check minute limit (simplified)
        if session["last_request"] and (current_time - session["last_request"]) < 60:
            minute_requests = sum(1 for s in self.active_sessions.values() 
                                if s["last_request"] and (current_time - s["last_request"]) < 60)
            if minute_requests >= self.config.max_requests_per_minute:
                return {"allowed": False, "reason": "Minute limit exceeded"}
        
        return {"allowed": True}
    
    def record_demo_request(self, session_id: str):
        """Record a demo request."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["requests_count"] += 1
            self.active_sessions[session_id]["last_request"] = time.time()
    
    def get_sample_files(self) -> List[Dict[str, Any]]:
        """Get available sample files for demos."""
        files = []
        for filename, file_info in self.sample_file_manager.get_sample_files().items():
            files.append({
                "filename": filename,
                "path": file_info["path"],
                "description": file_info["info"]["description"],
                "size": file_info["info"]["size"],
                "features": file_info["info"]["features"],
                "page_count": file_info["info"]["page_count"]
            })
        return files


# Global demo mode manager
_demo_manager = None


def get_demo_manager() -> DemoModeManager:
    """Get global demo mode manager instance."""
    global _demo_manager
    if _demo_manager is None:
        _demo_manager = DemoModeManager()
    return _demo_manager


def is_demo_mode() -> bool:
    """Check if demo mode is enabled."""
    return get_demo_manager().is_demo_mode()


def get_demo_banner_info() -> Dict[str, Any]:
    """Get demo mode banner information."""
    return get_demo_manager().get_demo_banner()
