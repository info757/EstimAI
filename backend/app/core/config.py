"""Core configuration settings using Pydantic Settings v2."""
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database configuration
    DATABASE_URL: str = Field(
        default="sqlite:///./estimai.db",
        description="Database connection URL"
    )
    
    # File system paths
    FILES_DIR: str = Field(
        default="app/files",
        description="Directory for uploaded files"
    )
    
    REPORTS_DIR: str = Field(
        default="/tmp",
        description="Directory for generated reports"
    )
    
    TEMPLATES_DIR: str = Field(
        default="backend/templates",
        description="Directory for detection templates"
    )
    
    # Detection configuration
    DETECTOR_IMPL: str = Field(
        default="opencv_template",
        description="Detection implementation to use"
    )
    
    # API configuration
    API_V1_STR: str = Field(
        default="/api/v1",
        description="API v1 prefix"
    )
    
    PROJECT_NAME: str = Field(
        default="EstimAI",
        description="Project name"
    )
    
    # Security settings (for future use)
    SECRET_KEY: Optional[str] = Field(
        default=None,
        description="Secret key for JWT tokens"
    )
    
    ALGORITHM: str = Field(
        default="HS256",
        description="JWT algorithm"
    )
    
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access token expiration in minutes"
    )
    
    # CORS settings
    BACKEND_CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:5173"],
        description="Allowed CORS origins"
    )
    
    # Detection settings
    TEMPLATE_MATCHING_THRESHOLD: float = Field(
        default=0.8,
        description="Template matching confidence threshold"
    )
    
    MAX_DETECTIONS_PER_PAGE: int = Field(
        default=100,
        description="Maximum detections per page"
    )
    
    # File processing settings
    MAX_FILE_SIZE_MB: int = Field(
        default=50,
        description="Maximum file size in MB"
    )
    
    ALLOWED_FILE_EXTENSIONS: list[str] = Field(
        default=[".pdf"],
        description="Allowed file extensions"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        
    def get_files_dir(self) -> Path:
        """Get files directory as Path object."""
        return Path(self.FILES_DIR).resolve()
    
    def get_reports_dir(self) -> Path:
        """Get reports directory as Path object."""
        return Path(self.REPORTS_DIR).resolve()
    
    def get_templates_dir(self) -> Path:
        """Get templates directory as Path object."""
        return Path(self.TEMPLATES_DIR).resolve()
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.get_files_dir().mkdir(parents=True, exist_ok=True)
        self.get_reports_dir().mkdir(parents=True, exist_ok=True)
        self.get_templates_dir().mkdir(parents=True, exist_ok=True)


# Singleton settings instance
settings = Settings()

# Ensure directories exist on import
settings.ensure_directories()