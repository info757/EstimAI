"""
Tests for the estimai_vector_pdf package.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest

PDF = Path("/mnt/data/site_plan_warehouse_100k.pdf")
TRUTH = Path("/mnt/data/site_plan_ground_truth.json")

@pytest.mark.skipif(not PDF.exists() or not TRUTH.exists(), reason="sample files missing")
def test_cli_against_truth():
    cmd = [sys.executable, "-m", "estimai_vector_pdf.cli",
           "takeoff", str(PDF),
           "--page", "1",
           "--truth-json", str(TRUTH),
           "--tol", "0.05"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
    assert proc.returncode == 0
