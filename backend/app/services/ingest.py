import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import UploadFile

from ..core.paths import project_ingest_raw_dir, project_ingest_parsed_dir, project_ingest_manifest
from ..core.logging import json_logger

logger = json_logger(__name__)


def load_ingest_manifest(pid: str) -> Dict[str, Any]:
    """Load the ingest manifest for a project, creating empty if missing."""
    manifest_path = project_ingest_manifest(pid)
    
    if manifest_path.exists():
        try:
            with open(manifest_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("Failed to load existing manifest, creating new one", extra={
                "pid": pid,
                "error": str(e)
            })
    
    # Return empty manifest structure
    return {
        "project_id": pid,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "items": []
    }


def save_ingest_manifest(pid: str, manifest: Dict[str, Any]) -> None:
    """Save the ingest manifest for a project."""
    manifest_path = project_ingest_manifest(pid)
    manifest["updated_at"] = datetime.now().isoformat()
    
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


def find_existing_item(manifest: Dict[str, Any], content_hash: str, filename: str) -> Optional[Dict[str, Any]]:
    """Find an existing item in the manifest by content hash and filename."""
    for item in manifest["items"]:
        if item.get("content_hash") == content_hash and item.get("filename") == filename:
            return item
    return None


def find_existing_item_by_hash(manifest: Dict[str, Any], content_hash: str) -> Optional[Dict[str, Any]]:
    """Find an existing item in the manifest by content hash only (for deduplication)."""
    for item in manifest["items"]:
        if item.get("content_hash") == content_hash:
            return item
    return None


def update_manifest_item(manifest: Dict[str, Any], item: Dict[str, Any]) -> None:
    """Update or add an item to the manifest."""
    # Find existing item by content hash and filename
    existing_item = find_existing_item(manifest, item["content_hash"], item["filename"])
    
    if existing_item:
        # Update existing item
        existing_item.update(item)
        existing_item["updated_at"] = datetime.now().isoformat()
        logger.info("Updated existing manifest item", extra={
            "file_name": item["filename"],
            "content_hash": item["content_hash"][:8]
        })
    else:
        # Add new item
        item["created_at"] = datetime.now().isoformat()
        item["updated_at"] = datetime.now().isoformat()
        manifest["items"].append(item)
        logger.info("Added new manifest item", extra={
            "file_name": item["filename"],
            "content_hash": item["content_hash"][:8]
        })


def update_manifest_item_by_hash(manifest: Dict[str, Any], item: Dict[str, Any]) -> None:
    """Update or add an item to the manifest by content hash only (for deduplication)."""
    # Find existing item by content hash only
    existing_item = find_existing_item_by_hash(manifest, item["content_hash"])
    
    if existing_item:
        # Update existing item
        existing_item.update(item)
        existing_item["updated_at"] = datetime.now().isoformat()
        logger.info("Updated existing manifest item by hash", extra={
            "file_name": item["filename"],
            "content_hash": item["content_hash"][:8]
        })
    else:
        # Add new item
        item["created_at"] = datetime.now().isoformat()
        item["updated_at"] = datetime.now().isoformat()
        manifest["items"].append(item)
        logger.info("Added new manifest item by hash", extra={
            "file_name": item["filename"],
            "content_hash": item["content_hash"][:8]
        })


def ingest_files(pid: str, files: List[UploadFile], job_id: str = None) -> Dict[str, Any]:
    """
    Ingest uploaded files for a project with deduplication.
    
    Args:
        pid: Project ID
        files: List of uploaded files
        job_id: Optional job ID for logging context
    
    Returns:
        Dictionary with ingestion summary
    """
    logger.info("Starting file ingestion", extra={
        "pid": pid,
        "job_id": job_id,
        "files_count": len(files)
    })
    
    # Load existing manifest
    manifest = load_ingest_manifest(pid)
    raw_dir = project_ingest_raw_dir(pid)
    parsed_dir = project_ingest_parsed_dir(pid)
    
    processed_items = []
    skipped_items = []
    error_items = []
    
    for file in files:
        try:
            logger.info("Processing file", extra={
                "pid": pid,
                "job_id": job_id,
                "file_name": file.filename,
                "content_type": file.content_type
            })
            
            # Generate timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = file.filename.replace(" ", "_").replace("/", "_")
            timestamped_filename = f"{timestamp}_{safe_filename}"
            file_path = raw_dir / timestamped_filename
            
            # Stream file to disk and compute hash
            content_hash = hashlib.sha256()
            file_size = 0
            
            with open(file_path, "wb") as f:
                # Read in chunks to handle large files efficiently
                chunk_size = 8192  # 8KB chunks
                while chunk := file.file.read(chunk_size):
                    f.write(chunk)
                    content_hash.update(chunk)
                    file_size += len(chunk)
            
            # Compute final hash
            final_hash = content_hash.hexdigest()
            
            # Check for duplicates by content hash (for true deduplication)
            existing_item_by_hash = find_existing_item_by_hash(manifest, final_hash)
            
            if existing_item_by_hash and existing_item_by_hash.get("status") == "indexed":
                # Skip indexing - file already exists and is indexed
                logger.info("Skipping duplicate file", extra={
                    "pid": pid,
                    "job_id": job_id,
                    "file_name": file.filename,
                    "content_hash": final_hash[:8],
                    "reason": "duplicate"
                })
                
                # Update timestamp but keep status as skipped
                skipped_item = {
                    "filename": file.filename,
                    "content_hash": final_hash,
                    "size": file_size,
                    "source_type": "upload",
                    "status": "skipped",
                    "reason": "duplicate",
                    "raw_path": str(file_path.relative_to(raw_dir.parent))
                }
                update_manifest_item_by_hash(manifest, skipped_item)
                skipped_items.append(skipped_item)
                
            else:
                # Process new or changed file
                logger.info("Processing new/changed file", extra={
                    "pid": pid,
                    "job_id": job_id,
                    "file_name": file.filename,
                    "content_hash": final_hash[:8]
                })
                
                # Create parsed record (stub for now - will be expanded in future)
                parsed_record = {
                    "filename": file.filename,
                    "timestamped_filename": timestamped_filename,
                    "content_hash": final_hash,
                    "size": file_size,
                    "content_type": file.content_type,
                    "uploaded_at": datetime.now().isoformat(),
                    "status": "processed"
                }
                
                # Save parsed record
                parsed_file_path = parsed_dir / f"{final_hash[:8]}_{safe_filename}.json"
                with open(parsed_file_path, "w") as f:
                    json.dump(parsed_record, f, indent=2)
                
                # Add to manifest
                manifest_item = {
                    "filename": file.filename,
                    "content_hash": final_hash,
                    "size": file_size,
                    "indexed_at": datetime.now().isoformat(),
                    "source_type": "upload",
                    "status": "indexed",
                    "raw_path": str(file_path.relative_to(raw_dir.parent)),
                    "parsed_path": str(parsed_file_path.relative_to(parsed_dir.parent))
                }
                
                update_manifest_item(manifest, manifest_item)
                processed_items.append(manifest_item)
                
                logger.info("File processed successfully", extra={
                    "pid": pid,
                    "job_id": job_id,
                    "file_name": file.filename,
                    "content_hash": final_hash[:8],
                    "size": file_size
                })
                
        except Exception as e:
            logger.error("Failed to process file", extra={
                "pid": pid,
                "job_id": job_id,
                "file_name": file.filename,
                "error": str(e)
            })
            
            # Add error item to manifest
            error_item = {
                "filename": file.filename,
                "content_hash": "unknown",
                "size": 0,
                "source_type": "upload",
                "status": "error",
                "error": str(e),
                "raw_path": str(file_path.relative_to(raw_dir.parent)) if 'file_path' in locals() else "unknown"
            }
            update_manifest_item(manifest, error_item)
            error_items.append(error_item)
    
    # Save updated manifest
    save_ingest_manifest(pid, manifest)
    
    summary = {
        "files_count": len(files),
        "processed": len(processed_items),
        "skipped": len(skipped_items),
        "errors": len(error_items),
        "items": processed_items + skipped_items + error_items
    }
    
    logger.info("File ingestion completed", extra={
        "pid": pid,
        "job_id": job_id,
        "files_count": len(files),
        "processed": len(processed_items),
        "skipped": len(skipped_items),
        "errors": len(error_items)
    })
    
    return summary


def get_ingest_manifest(pid: str) -> Dict[str, Any]:
    """Get the ingest manifest for a project."""
    return load_ingest_manifest(pid)


def rebuild_ingest_indices(pid: str, job_id: str = None) -> Dict[str, Any]:
    """
    Rebuild ingest indices from raw files.
    
    Args:
        pid: Project ID
        job_id: Optional job ID for logging context
    
    Returns:
        Dictionary with rebuild summary
    """
    logger.info("Starting ingest index rebuild", extra={
        "pid": pid,
        "job_id": job_id
    })
    
    # This is a placeholder for future implementation
    # Will scan raw files and rebuild manifest/index
    logger.info("Ingest index rebuild completed (placeholder)", extra={
        "pid": pid,
        "job_id": job_id
    })
    
    return {
        "status": "completed",
        "message": "Index rebuild completed (placeholder implementation)",
        "project_id": pid
    }
