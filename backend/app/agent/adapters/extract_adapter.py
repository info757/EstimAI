"""Resilient extract adapter that handles multiple function signatures.

This adapter provides a stable interface to the extract pipeline, automatically
discovering and calling the appropriate extract function regardless of signature
changes or module reorganization.
"""
from __future__ import annotations
import importlib
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Callable

logger = logging.getLogger(__name__)

# --- A thin normalized result the agent can consume ---------------------------
@dataclass
class ExtractPack:
    """Normalized extract result that the agent can consume."""
    raw: Any
    networks: Dict[str, Any]
    surface: Any = None

    def to_payload_networks(self) -> Dict[str, Any]:
        """
        If the raw extract already has a payload method, use it.
        Otherwise, assume `networks` is serializable.
        """
        if hasattr(self.raw, "to_payload_networks") and callable(self.raw.to_payload_networks):
            return self.raw.to_payload_networks()
        return self.networks

    def collect_qa_counts(self) -> Dict[str, int]:
        """Collect QA counts from the raw extract if available."""
        if hasattr(self.raw, "collect_qa_counts") and callable(self.raw.collect_qa_counts):
            return self.raw.collect_qa_counts()
        return {}


# --- Helpers to call candidate functions with flexible args -------------------
def _try_call(fn: Callable, file_ref: str, max_pages: Optional[int]) -> Any:
    """Try common signatures without exploding if they differ."""
    # Try common signatures without exploding if they differ
    try:
        return fn(file_ref=file_ref, max_pages=max_pages)
    except TypeError:
        pass
    try:
        return fn(file_ref=file_ref)
    except TypeError:
        pass
    try:
        return fn(path=file_ref, max_pages=max_pages)
    except TypeError:
        pass
    try:
        return fn(path=file_ref)
    except TypeError:
        pass
    # As a last resort, try positional:
    try:
        return fn(file_ref, max_pages)
    except TypeError:
        try:
            return fn(file_ref)
        except TypeError:
            raise


def _first_attr(mod: Any, *names: str) -> Optional[Callable]:
    """Find the first callable attribute matching any of the given names."""
    for n in names:
        if hasattr(mod, n):
            fn = getattr(mod, n)
            if callable(fn):
                return fn
    return None


def extract_any(file_ref: str, max_pages: Optional[int] = None) -> ExtractPack:
    """
    Calls whatever extract/detect pipeline your detectors package exposes
    and returns a normalized ExtractPack for the agent.
    
    This function is resilient to signature changes and module reorganization.
    It tries multiple candidates in priority order and provides clear error
    messages when no compatible function is found.
    
    Args:
        file_ref: Path to the PDF file to extract from
        max_pages: Optional maximum number of pages to process
        
    Returns:
        ExtractPack: Normalized extract result with networks and surface data
        
    Raises:
        RuntimeError: If no compatible extract function is found
    """
    # 1) import the detectors package
    try:
        detectors = importlib.import_module("backend.app.services.detectors")
    except ImportError as e:
        raise RuntimeError(f"Failed to import detectors module: {e}") from e

    # 2) Candidate call targets, in priority order
    candidates = [
        # New-style pipeline module names
        ("backend.app.services.detectors.pipeline", ("run_extract", "run", "extract_all")),
        # Legacy flat functions on the package
        ("backend.app.services.detectors", ("run_extract", "run", "extract_all")),
        # Older split modules
        ("backend.app.services.detectors.extract", ("run_extract", "extract", "build")),
        ("backend.app.services.detectors.core", ("run_extract", "run")),
    ]

    last_err: Optional[Exception] = None
    raw = None

    for mod_name, func_names in candidates:
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:
            logger.debug(f"Could not import {mod_name}: {e}")
            last_err = e
            continue
        
        fn = _first_attr(mod, *func_names)
        if not fn:
            logger.debug(f"No matching function in {mod_name}: tried {func_names}")
            continue
        
        try:
            logger.info(f"Trying extract function: {mod_name}.{fn.__name__}")
            raw = _try_call(fn, file_ref=file_ref, max_pages=max_pages)
            logger.info(f"Successfully called {mod_name}.{fn.__name__}")
            break
        except Exception as e:
            logger.debug(f"Failed to call {mod_name}.{fn.__name__}: {e}")
            last_err = e
            continue

    if raw is None:
        msg = (
            "No compatible extract function found. Tried modules/functions:\n"
            + "\n".join(f"- {m}: {', '.join(fns)}" for m, fns in candidates)
        )
        if last_err:
            msg += f"\nLast error: {type(last_err).__name__}: {last_err}"
        logger.error(msg)
        raise RuntimeError(msg)

    # 3) Normalize to ExtractPack
    # networks: prefer attribute, else dict key
    networks = {}
    if hasattr(raw, "networks"):
        networks = getattr(raw, "networks")
    elif isinstance(raw, dict) and "networks" in raw:
        networks = raw["networks"]

    # surface (optional)
    surface = None
    if hasattr(raw, "surface"):
        surface = getattr(raw, "surface")
    elif isinstance(raw, dict) and "surface" in raw:
        surface = raw["surface"]

    logger.info(f"Normalized extract result: {len(networks)} networks, surface={'present' if surface else 'absent'}")
    return ExtractPack(raw=raw, networks=networks or {}, surface=surface)

