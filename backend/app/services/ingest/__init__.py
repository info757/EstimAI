# Ingest services module
from .base import Ingestor
from .oss_ingestor import OpenSourceIngestor

def get_ingestor():
    """Get the appropriate ingestor based on available dependencies"""
    try:
        from .apryse_ingestor import ApryseIngestor
        return ApryseIngestor()
    except ImportError:
        return OpenSourceIngestor()

# Re-export functions from ingest.py for backward compatibility
def load_ingest_manifest(pid: str):
    """Load ingest manifest - delegates to ingest.py"""
    from ..ingest import load_ingest_manifest as _load
    return _load(pid)

def save_ingest_manifest(pid: str, manifest):
    """Save ingest manifest - delegates to ingest.py"""
    from ..ingest import save_ingest_manifest as _save
    return _save(pid, manifest)

def update_manifest_item(manifest, item):
    """Update manifest item - delegates to ingest.py"""
    from ..ingest import update_manifest_item as _update
    return _update(manifest, item)