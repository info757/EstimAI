"""Agent adapters for bridging between protocols and legacy implementations."""

from .extract_adapter import ExtractPack, extract_any
from .http_extract_bridge import extract_via_route

__all__ = ["ExtractPack", "extract_any", "extract_via_route"]

