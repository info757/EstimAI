import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from fastapi import UploadFile

from ..core.paths import project_ingest_raw_dir, project_ingest_parsed_dir
from ..core.logging import json_logger

logger = json_logger(__name__)


def ingest_files(pid: str, files: List[UploadFile], job_id: str = None) -> Dict[str, Any]:
    """
    Ingest uploaded files for a project.
    
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
    
    items = []
    raw_dir = project_ingest_raw_dir(pid)
    parsed_dir = project_ingest_parsed_dir(pid)
    
    for file in files:
        try:
            logger.info("Processing file", extra={
                "pid": pid,
                "job_id": job_id,
                "filename": file.filename,
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
            
            # Create parsed record (stub for now)
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
            
            items.append({
                "filename": file.filename,
                "content_hash": final_hash,
                "size": file_size,
                "content_type": file.content_type,
                "raw_path": str(file_path.relative_to(raw_dir.parent)),
                "parsed_path": str(parsed_file_path.relative_to(parsed_dir.parent))
            })
            
            logger.info("File processed successfully", extra={
                "pid": pid,
                "job_id": job_id,
                "filename": file.filename,
                "content_hash": final_hash,
                "size": file_size
            })
            
        except Exception as e:
            logger.error("Failed to process file", extra={
                "pid": pid,
                "job_id": job_id,
                "filename": file.filename,
                "error": str(e)
            })
            # Continue with other files even if one fails
    
    summary = {
        "files_count": len(items),
        "items": items
    }
    
    logger.info("File ingestion completed", extra={
        "pid": pid,
        "job_id": job_id,
        "files_count": len(items),
        "successful_files": len(items)
    })
    
    return summary
