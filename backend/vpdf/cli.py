#!/usr/bin/env python3
"""
CLI for vpdf (vector PDF parser).

Usage:
    python -m vpdf.cli takeoff --pdf <path> --page <index>
"""
from __future__ import annotations
import sys
import json
import argparse
from pathlib import Path
from .extract import extract_lines
from .scale import detect_scale_bar_ft_per_unit
from .measure import curb_length_lf
from .classify import classify_areas


def cmd_takeoff(args):
    """Run takeoff analysis on a PDF page."""
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}", file=sys.stderr)
        return 1
    
    # Extract page data
    px = extract_lines(str(pdf_path), page_index=args.page)
    
    # Detect scale
    ft_per_unit = detect_scale_bar_ft_per_unit(px)
    if ft_per_unit is None:
        print("Error: Could not detect scale", file=sys.stderr)
        return 1
    
    # Compute curb length
    curb_lf = curb_length_lf(px, ft_per_unit)
    
    # Classify areas
    areas = classify_areas(px)
    
    # Output results as JSON
    result = {
        "scale_ft_per_unit": ft_per_unit,
        "curb_length_lf": curb_lf,
        "areas": {
            "building_count": len(areas["building"]),
            "pavement_count": len(areas["pavement"]),
        }
    }
    
    print(json.dumps(result, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(description="Vector PDF takeoff tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Takeoff command
    takeoff_parser = subparsers.add_parser("takeoff", help="Run quantity takeoff")
    takeoff_parser.add_argument("--pdf", required=True, help="Path to PDF file")
    takeoff_parser.add_argument("--page", type=int, default=0, help="Page index (0-based)")
    
    args = parser.parse_args()
    
    if args.command == "takeoff":
        return cmd_takeoff(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

