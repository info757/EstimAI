#!/usr/bin/env python3
"""
Import normalization script for EstimAI backend.

Rewrites imports to use consistent backend.* prefix:
- from vpdf.* → from backend.vpdf.*
- import vpdf → import backend.vpdf
- from app.* → from backend.app.*
- import app → import backend.app

Usage:
    python scripts/fix_imports.py --dry-run    # Show proposed changes
    python scripts/fix_imports.py --write     # Apply changes
"""
import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


def find_python_files(root_dir: Path) -> List[Path]:
    """Find all Python files under root_dir."""
    return list(root_dir.rglob("*.py"))


def should_rewrite_line(line: str) -> bool:
    """Check if a line should be rewritten."""
    # Skip commented lines and strings
    stripped = line.strip()
    if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
        return False
    
    # Only process top-level import statements
    if not (stripped.startswith('from ') or stripped.startswith('import ')):
        return False
    
    # Skip if already starts with backend.
    if stripped.startswith('from backend.') or stripped.startswith('import backend.'):
        return False
    
    return True


def rewrite_imports(content: str) -> Tuple[str, int]:
    """Rewrite imports in content and return (new_content, changes_count)."""
    lines = content.split('\n')
    changes = 0
    
    for i, line in enumerate(lines):
        if not should_rewrite_line(line):
            continue
        
        original = line
        
        # Rewrite patterns
        # from vpdf.* → from backend.vpdf.*
        line = re.sub(r'^from\s+vpdf(\s|\.)', r'from backend.vpdf\1', line)
        
        # import vpdf → import backend.vpdf
        line = re.sub(r'^import\s+vpdf(\s|\.|$)', r'import backend.vpdf\1', line)
        
        # from app.* → from backend.app.*
        line = re.sub(r'^from\s+app(\s|\.)', r'from backend.app\1', line)
        
        # import app → import backend.app
        line = re.sub(r'^import\s+app(\s|\.|$)', r'import backend.app\1', line)
        
        if line != original:
            lines[i] = line
            changes += 1
    
    return '\n'.join(lines), changes


def process_file(file_path: Path, dry_run: bool = True) -> Tuple[bool, int]:
    """Process a single file and return (changed, changes_count)."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False, 0
    
    new_content, changes = rewrite_imports(original_content)
    
    if changes == 0:
        return False, 0
    
    if dry_run:
        print(f"\n--- {file_path} ---")
        # Show diff-like output
        original_lines = original_content.split('\n')
        new_lines = new_content.split('\n')
        
        for i, (orig, new) in enumerate(zip(original_lines, new_lines)):
            if orig != new:
                print(f"Line {i+1}:")
                print(f"- {orig}")
                print(f"+ {new}")
    else:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ Updated {file_path} ({changes} changes)")
        except Exception as e:
            print(f"❌ Error writing {file_path}: {e}")
            return False, 0
    
    return True, changes


def main():
    parser = argparse.ArgumentParser(description="Normalize Python imports in backend")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show proposed changes without applying")
    parser.add_argument("--write", action="store_true",
                       help="Apply changes to files")
    parser.add_argument("--root", default="backend",
                       help="Root directory to process (default: backend)")
    
    args = parser.parse_args()
    
    if args.write and args.dry_run:
        print("❌ Cannot use both --write and --dry-run")
        sys.exit(1)
    
    if args.write:
        dry_run = False
        print("🔧 Applying import normalization...")
    elif args.dry_run:
        dry_run = True
        print("🔍 Dry run - showing proposed changes...")
    else:
        # Default to dry-run if no arguments provided
        dry_run = True
        print("🔍 Dry run - showing proposed changes...")
        print("💡 Use --write to apply changes")
    
    root_dir = Path(args.root)
    if not root_dir.exists():
        print(f"❌ Root directory {root_dir} does not exist")
        sys.exit(1)
    
    python_files = find_python_files(root_dir)
    print(f"📁 Found {len(python_files)} Python files")
    
    files_changed = 0
    total_changes = 0
    
    for file_path in python_files:
        changed, changes = process_file(file_path, dry_run)
        if changed:
            files_changed += 1
            total_changes += changes
    
    print(f"\n📊 Summary:")
    print(f"   Files changed: {files_changed}")
    print(f"   Lines modified: {total_changes}")
    
    if dry_run and total_changes > 0:
        print(f"\n💡 To apply changes, run: python scripts/fix_imports.py --write")
    elif not dry_run:
        print(f"\n✅ Import normalization complete!")


if __name__ == "__main__":
    main()
