import json, os
from pathlib import Path
from vpdf.extract import extract_lines
from vpdf.scale import detect_scale_bar_ft_per_unit
from vpdf.measure import curb_length_lf

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "tests" / "assets" / "site_plan_warehouse_100k.pdf"
TRUTH = ROOT / "tests" / "assets" / "site_plan_ground_truth.json"

def test_curb_matches_truth():
    assert os.path.exists(PDF) and os.path.exists(TRUTH)
    truth = json.load(open(TRUTH))
    expected = truth["curbs"]["total_length_ft"]
    
    pd = extract_lines(str(PDF), page_index=1)
    scale = detect_scale_bar_ft_per_unit(pd)
    assert scale, "scale not detected"
    
    got = curb_length_lf(pd, scale)
    assert abs(got - expected) < 0.5, f"Curb length mismatch: {got} vs {expected}"

