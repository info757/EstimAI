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