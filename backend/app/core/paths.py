# backend/app/core/paths.py
from pathlib import Path
from .config import get_settings


def artifacts_root() -> Path:
    """Get the root artifacts directory."""
    settings = get_settings()
    return Path(settings.ARTIFACT_DIR)


def project_dir(pid: str) -> Path:
    """Get the project directory for a given project ID."""
    project_path = artifacts_root() / pid
    project_path.mkdir(parents=True, exist_ok=True)
    return project_path


def stage_dir(pid: str, stage: str) -> Path:
    """Get the stage directory for a given project and stage."""
    stage_path = project_dir(pid) / stage
    stage_path.mkdir(parents=True, exist_ok=True)
    return stage_path


def docs_dir(pid: str) -> Path:
    """Get the docs directory for a given project."""
    return stage_dir(pid, "docs")


def bid_dir(pid: str) -> Path:
    """Get the bid directory for a given project."""
    return stage_dir(pid, "bid")


def ensure_dir(path: Path) -> Path:
    """Ensure a directory exists and return the path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def jobs_db_path() -> Path:
    """Get the path to the jobs SQLite database."""
    db_path = artifacts_root() / "jobs.db"
    return db_path


def project_ingest_dir(pid: str) -> Path:
    """Get the ingest directory for a given project."""
    ingest_path = project_dir(pid) / "ingest"
    ingest_path.mkdir(parents=True, exist_ok=True)
    return ingest_path


def project_ingest_raw_dir(pid: str) -> Path:
    """Get the raw files directory for ingest."""
    raw_path = project_ingest_dir(pid) / "raw"
    raw_path.mkdir(parents=True, exist_ok=True)
    return raw_path


def project_ingest_parsed_dir(pid: str) -> Path:
    """Get the parsed files directory for ingest."""
    parsed_path = project_ingest_dir(pid) / "parsed"
    parsed_path.mkdir(parents=True, exist_ok=True)
    return parsed_path


def project_ingest_manifest(pid: str) -> Path:
    """Get the ingest manifest file path for a given project."""
    return project_ingest_dir(pid) / "ingest_manifest.json"


def ensure_demo_project_structure(demo_pid: str) -> None:
    """Ensure demo project directory structure exists with all necessary subdirectories.
    
    Creates the following structure:
    ARTIFACT_DIR/{demo_pid}/
    ├── ingest/
    │   ├── raw/
    │   ├── parsed/
    │   └── ingest_manifest.json
    ├── bid/
    ├── docs/
    └── .keep
    """
    from .config import get_settings
    settings = get_settings()
    
    # Get demo project root
    demo_root = project_dir(demo_pid)
    
    # Ensure all required subdirectories exist
    ingest_dir = project_ingest_dir(demo_pid)
    project_ingest_raw_dir(demo_pid)
    project_ingest_parsed_dir(demo_pid)
    bid_dir(demo_pid)
    docs_dir(demo_pid)
    
    # Create .keep files to ensure directories persist in git-ignored volumes
    keep_files = [
        demo_root / ".keep",
        ingest_dir / ".keep",
        project_ingest_raw_dir(demo_pid) / ".keep",
        project_ingest_parsed_dir(demo_pid) / ".keep",
        bid_dir(demo_pid) / ".keep",
        docs_dir(demo_pid) / ".keep",
    ]
    
    for keep_file in keep_files:
        if not keep_file.exists():
            keep_file.touch()
    
    # Create empty ingest manifest if it doesn't exist
    manifest_path = project_ingest_manifest(demo_pid)
    if not manifest_path.exists():
        import json
        empty_manifest = {"items": []}
        with open(manifest_path, "w") as f:
            json.dump(empty_manifest, f, indent=2)
