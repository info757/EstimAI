"""Core configuration settings using Pydantic Settings v2."""
from typing import List, Literal, Optional, Union
from pydantic import AnyUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Base directory for absolute paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent  # .../backend/app
    
    # Database configuration
    DATABASE_URL: str = "sqlite:///./estimai.db"
    
    # File system paths (absolute)
    FILES_DIR: Path = BASE_DIR / "files"  # .../backend/app/files
    REPORTS_DIR: Path = Path("/tmp/estimai_reports")
    TEMPLATES_DIR: Path = BASE_DIR.parent / "templates"  # .../backend/templates
    
    # Detection configuration
    DETECTOR_IMPL: str = "vision_llm"
    
    # API configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "EstimAI"
    
    # Security settings (for future use)
    SECRET_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:5173"]
    
    # Debug settings
    DEBUG: bool = False
    
    # Detection settings
    TEMPLATE_MATCHING_THRESHOLD: float = 0.8
    MAX_DETECTIONS_PER_PAGE: int = 100
    
    # File processing settings
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_FILE_EXTENSIONS: List[str] = [".pdf"]
    
    # LLM configuration
    LLM_PROVIDER: str = "openai"
    VISION_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: Optional[str] = None
    
    # Image processing settings
    TILE_PX: int = 1024
    TILE_OVERLAP_PX: int = 128
    
    # --- fields your .env is providing (add these) ---
    artifact_dir: str = "backend/artifacts"

    # Accept a comma-separated string or a JSON array
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:5174"]

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # allow plain strings or URLs
    vite_api_base: Union[AnyUrl, str] = "http://localhost:8000/api"
    vite_file_base: Union[AnyUrl, str] = "http://localhost:8000"

    # --- Apryse flags we added in this thread ---
    APR_USE_APRYSE: bool = False
    APR_LICENSE_KEY: Optional[str] = None
    APR_ENABLE_SMART_TABLES: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",        # read vars as-is
        extra="ignore",       # ignore unknown .env keys (prevents crash)
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v):
        # Support comma-separated strings in .env:  "http://a,http://b"
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v
    
        
    def get_files_dir(self) -> Path:
        """Get files directory as Path object."""
        return self.FILES_DIR.resolve()
    
    def get_reports_dir(self) -> Path:
        """Get reports directory as Path object."""
        return self.REPORTS_DIR.resolve()
    
    def get_templates_dir(self) -> Path:
        """Get templates directory as Path object."""
        return self.TEMPLATES_DIR.resolve()
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.get_files_dir().mkdir(parents=True, exist_ok=True)
        self.get_reports_dir().mkdir(parents=True, exist_ok=True)
        self.get_templates_dir().mkdir(parents=True, exist_ok=True)


# Singleton settings instance
settings = Settings()

# Ensure directories exist on import
settings.ensure_directories()