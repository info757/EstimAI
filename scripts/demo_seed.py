#!/usr/bin/env python3
"""
Demo seed utility for EstimAI.

Copies sample files from backend/static/samples to a demo project's ingest directory
and creates/updates the ingest manifest for immediate testing.
"""

import os
import sys
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add backend to path for imports
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings
from app.core.paths import project_ingest_raw_dir, project_ingest_manifest


def copy_sample_files(demo_pid: str = "demo") -> List[Dict[str, Any]]:
    """
    Copy sample files to demo project's ingest raw directory.
    
    Args:
        demo_pid: Project ID for demo (default: "demo")
        
    Returns:
        List of manifest items for copied files
    """
    # Get paths
    samples_dir = backend_dir / "static" / "samples"
    raw_dir = project_ingest_raw_dir(demo_pid)
    
    # Ensure raw directory exists
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    # Get sample files
    sample_files = []
    if samples_dir.exists():
        for file_path in samples_dir.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                sample_files.append(file_path)
    
    if not sample_files:
        print(f"⚠️  No sample files found in {samples_dir}")
        return []
    
    # Copy files with timestamped names
    manifest_items = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for i, sample_file in enumerate(sample_files):
        # Create timestamped filename
        timestamped_name = f"{timestamp}_{i+1:02d}_{sample_file.name}"
        dest_path = raw_dir / timestamped_name
        
        # Copy file
        shutil.copy2(sample_file, dest_path)
        
        # Calculate file size and hash
        file_size = dest_path.stat().st_size
        with open(dest_path, 'rb') as f:
            content_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Create manifest item
        manifest_item = {
            "filename": sample_file.name,
            "content_hash": content_hash,
            "size": file_size,
            "indexed_at": datetime.now().isoformat(),
            "source_type": "upload",
            "status": "indexed",
            "raw_path": str(dest_path.relative_to(raw_dir.parent)),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        manifest_items.append(manifest_item)
        print(f"✅ Copied {sample_file.name} -> {timestamped_name}")
    
    return manifest_items


def update_manifest(demo_pid: str, manifest_items: List[Dict[str, Any]]) -> None:
    """
    Update the ingest manifest with the new items.
    
    Args:
        demo_pid: Project ID for demo
        manifest_items: List of manifest items to add
    """
    manifest_path = project_ingest_manifest(demo_pid)
    
    # Load existing manifest or create new one
    if manifest_path.exists():
        import json
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
        except (json.JSONDecodeError, IOError):
            manifest = create_empty_manifest(demo_pid)
    else:
        manifest = create_empty_manifest(demo_pid)
    
    # Add new items (avoid duplicates by content hash)
    existing_hashes = {item.get("content_hash") for item in manifest.get("items", [])}
    
    for item in manifest_items:
        if item["content_hash"] not in existing_hashes:
            manifest["items"].append(item)
            print(f"📝 Added {item['filename']} to manifest")
        else:
            print(f"⏭️  Skipped {item['filename']} (already in manifest)")
    
    # Update manifest timestamp
    manifest["updated_at"] = datetime.now().isoformat()
    
    # Save manifest
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"💾 Manifest saved to {manifest_path}")


def create_empty_manifest(pid: str) -> Dict[str, Any]:
    """Create an empty manifest structure."""
    return {
        "project_id": pid,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "items": []
    }


def main():
    """Main demo seed function."""
    print("🌱 EstimAI Demo Seed Utility")
    print("=" * 40)
    
    # Get demo PID from environment or use default
    demo_pid = os.getenv("DEMO_PID", "demo")
    print(f"📁 Demo Project ID: {demo_pid}")
    
    try:
        # Copy sample files
        print(f"\n📋 Copying sample files...")
        manifest_items = copy_sample_files(demo_pid)
        
        if not manifest_items:
            print("❌ No files were copied. Exiting.")
            sys.exit(1)
        
        # Update manifest
        print(f"\n📝 Updating ingest manifest...")
        update_manifest(demo_pid, manifest_items)
        
        # Print summary
        print(f"\n🎉 Demo seed completed successfully!")
        print(f"📊 Files processed: {len(manifest_items)}")
        print(f"📁 Raw files: {project_ingest_raw_dir(demo_pid)}")
        print(f"📋 Manifest: {project_ingest_manifest(demo_pid)}")
        print(f"\n💡 You can now test the ingest pipeline with existing files!")
        
    except Exception as e:
        print(f"❌ Demo seed failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
