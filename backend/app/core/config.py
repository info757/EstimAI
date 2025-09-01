# backend/app/core/config.py
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Centralized configuration for EstimAI backend."""
    
    # Required: Artifact directory (absolute path recommended)
    ARTIFACT_DIR: str
    
    # CORS configuration
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Optional: Costbook and markup settings
    COSTBOOK_PATH: str = ""
    OVERHEAD_PCT: float = 10.0
    PROFIT_PCT: float = 5.0
    
    @validator('ARTIFACT_DIR')
    def validate_artifact_dir(cls, v):
        """Ensure ARTIFACT_DIR is an absolute path and create if it doesn't exist."""
        artifact_path = Path(v).resolve()
        artifact_path.mkdir(parents=True, exist_ok=True)
        return str(artifact_path)
    
    @validator('CORS_ORIGINS')
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS string into list."""
        return [origin.strip() for origin in v.split(',') if origin.strip()]
    
    @validator('LOG_LEVEL')
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'LOG_LEVEL must be one of: {valid_levels}')
        return v.upper()
    
    class Config:
        env_file = [".env", "../.env", "../../.env"]
        env_file_encoding = "utf-8"


# Global settings instance
_settings: Settings = None


def get_settings() -> Settings:
    """Get the global settings instance (singleton pattern)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
