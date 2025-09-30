from pathlib import Path
import json
from vpdf.extract import extract_lines
from vpdf.scale import detect_scale_bar_ft_per_unit
from vpdf.measure import curb_length_lf

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "tests" / "assets" / "site_plan_warehouse_100k.pdf"
TRUTH = ROOT / "tests" / "assets" / "site_plan_ground_truth.json"

def test_scale_and_curb():
    assert PDF.exists() and TRUTH.exists()
    truth = json.loads(TRUTH.read_text())
    expected_curb = truth["curbs"]["total_length_ft"]  # 1740.0

    # extract_lines returns PageDraw with lines, texts, and filled_rects
    px = extract_lines(str(PDF), page_index=1)

    ft_per_unit = detect_scale_bar_ft_per_unit(px)
    assert ft_per_unit is not None, "Scale detection failed"
    # Expect ~0.27778 on the sample (100 ft / 360 units)
    assert abs(ft_per_unit - (100.0/360.0)) < 1e-3, f"Scale mismatch: {ft_per_unit} vs {100.0/360.0}"

    curb = curb_length_lf(px, ft_per_unit)
    assert abs(curb - expected_curb) < 0.5, f"Curb length mismatch: {curb} vs {expected_curb}"

