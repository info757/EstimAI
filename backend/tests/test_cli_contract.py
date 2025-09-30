from pathlib import Path
import json, subprocess, sys
ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "tests" / "assets" / "site_plan_warehouse_100k.pdf"
TRUTH = ROOT / "tests" / "assets" / "site_plan_ground_truth.json"

def test_cli_contract():
    if not (PDF.exists() and TRUTH.exists()):
        return
    proc = subprocess.run([sys.executable, "-m", "vpdf.cli", "takeoff",
                           "--pdf", str(PDF),
                           "--page", "1"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr

