#!/usr/bin/env python3
"""
Generate synthetic vector PDF site plan for deterministic takeoff tests.

Creates:
- tests/assets/site_plan_warehouse_100k.pdf (5-page vector PDF)
- tests/assets/site_plan_ground_truth.json (exact quantities)

Specifications:
- Scale: 1" = 20' (PT_PER_FT = 72/20 = 3.6 PDF points per foot)
- NO viewport scaling - all geometry uses true scale
- Scale bar: 100 ft = 360 PDF points
- Building: 100' × 80' = 8,000 SF
- Pavement: 170' × 120' = 20,400 SF (gross), 12,400 SF (net)
- Curb: 580 LF perimeter (explicit width=2.0 strokes)
- Parking: 20 stalls (9' × 18')
"""
from __future__ import annotations
import json
from pathlib import Path
import fitz  # PyMuPDF

# Scale: 1" = 20' → 72 PDF points = 20 feet → 3.6 PDF units per foot
PT_PER_FT = 72.0 / 20.0  # Exactly 3.6
PDF_UNITS_PER_FOOT = PT_PER_FT

# Colors (RGB 0-1)
BLACK = (0, 0, 0)
RED = (1, 0, 0)      # Sanitary
BLUE = (0, 0, 1)     # Storm
GREEN = (0, 1, 0)    # Water
GREY_BUILDING = (0.827, 0.827, 0.827)  # Building fill
GREY_PAVEMENT = (0.961, 0.961, 0.961)  # Pavement fill

def ft_to_pdf(feet: float) -> float:
    """Convert feet to PDF units."""
    return feet * PDF_UNITS_PER_FOOT

def make_pdf_and_truth():
    """Generate the PDF and ground truth JSON."""
    
    # Page size (US Letter landscape: 11" × 8.5")
    page_width = 792  # 11" at 72 dpi
    page_height = 612  # 8.5" at 72 dpi
    
    # Create PDF
    doc = fitz.open()
    
    # === PAGE 1: COVER / LEGEND ===
    page1 = doc.new_page(width=page_width, height=page_height)
    
    # Title
    page1.insert_text((36, 30), "SITE PLAN - Schematic Site Plan (Vector Test)", fontsize=16)
    page1.insert_text((56, 552), "Scale Bar (100 ft @ 1\"=20')", fontsize=9)
    page1.insert_text((352.6, 566), "N", fontsize=9)  # North arrow
    
    # Scale bar: 100 ft at true scale
    scale_bar_length_pt = 100 * PT_PER_FT  # 360 pt
    scale_bar_start = (56, 540)
    scale_bar_end = (56 + scale_bar_length_pt, 540)
    page1.draw_line(scale_bar_start, scale_bar_end, color=BLACK, width=2.0)
    
    # Border
    page1.draw_rect(fitz.Rect(18, 18, page_width-18, page_height-18), color=BLACK, width=1.0)
    
    # === PAGE 2: SITE PLAN (Footprint, Pavement, Curbs, Parking) ===
    page2 = doc.new_page(width=page_width, height=page_height)
    page2.insert_text((36, 30), "SITE PLAN – Footprint, Pavement, Curbs, Sidewalks, Stalls (schematic)", fontsize=16)
    page2.insert_text((36, 50), "WAREHOUSE 100,000 SF (250' x 400')", fontsize=12)
    page2.insert_text((56, 552), "Scale Bar (100 ft @ 1\"=20')", fontsize=9)
    page2.insert_text((356, 566), "N", fontsize=9)
    
    # Scale bar: 100 ft at true scale
    page2.draw_line((56, 540), (56 + scale_bar_length_pt, 540), color=BLACK, width=2.0)
    
    # Use consistent scale throughout: 1" = 20' (3.6 PDF units per foot)
    # All geometry uses this same scale
    # Site will be smaller to fit on page at true scale
    
    margin = 56
    origin_x = margin
    origin_y = 70  # Leave room at bottom for scale bar
    
    def ft_to_page(ft_x: float, ft_y: float) -> tuple:
        """Convert feet coordinates to PDF page coordinates at true scale."""
        pdf_x = origin_x + ft_to_pdf(ft_x)
        # Flip Y for PDF (origin at top-left)
        pdf_y = page_height - origin_y - ft_to_pdf(ft_y)
        return (pdf_x, pdf_y)
    
    # Pavement boundary: Adjusted to fit page at true scale
    # At 3.6 units/ft, available space is ~189' × 142'
    # Use 170' × 120' site: perimeter = 2*(170+120) = 580 LF
    pave_w_ft = 170.0
    pave_h_ft = 120.0
    pave_p1 = ft_to_page(0, 0)
    pave_p2 = ft_to_page(pave_w_ft, pave_h_ft)
    # Ensure proper rect orientation (x0 < x1, y0 < y1)
    pave_rect_fitz = fitz.Rect(
        min(pave_p1[0], pave_p2[0]), min(pave_p1[1], pave_p2[1]),
        max(pave_p1[0], pave_p2[0]), max(pave_p1[1], pave_p2[1])
    )
    
    # Draw pavement fill
    page2.draw_rect(pave_rect_fitz, color=BLACK, fill=GREY_PAVEMENT, width=1.0)
    
    # Building: 100' × 80' = 8,000 SF, centered in pavement
    bldg_w_ft = 100.0
    bldg_h_ft = 80.0
    bldg_cx_ft = pave_w_ft / 2
    bldg_cy_ft = pave_h_ft / 2
    bldg_p1 = ft_to_page(bldg_cx_ft - bldg_w_ft/2, bldg_cy_ft - bldg_h_ft/2)
    bldg_p2 = ft_to_page(bldg_cx_ft + bldg_w_ft/2, bldg_cy_ft + bldg_h_ft/2)
    # Ensure proper rect orientation (x0 < x1, y0 < y1)
    bldg_rect_fitz = fitz.Rect(
        min(bldg_p1[0], bldg_p2[0]), min(bldg_p1[1], bldg_p2[1]),
        max(bldg_p1[0], bldg_p2[0]), max(bldg_p1[1], bldg_p2[1])
    )
    
    # Draw building fill
    page2.draw_rect(bldg_rect_fitz, color=BLACK, fill=GREY_BUILDING, width=1.0)
    
    # Curb (heavy black perimeter around pavement)
    pave_corners = [
        ft_to_page(0, 0),
        ft_to_page(pave_w_ft, 0),
        ft_to_page(pave_w_ft, pave_h_ft),
        ft_to_page(0, pave_h_ft)
    ]
    for i in range(4):
        page2.draw_line(pave_corners[i], pave_corners[(i+1)%4], color=BLACK, width=2.0)
    
    # Parking stalls (20 stalls, 9' × 18' each)
    # Draw along left side
    num_stalls = 20
    stall_w_ft = 9.0
    stall_h_ft = 18.0
    stall_start_x = 10.0
    stall_start_y = 10.0
    
    for i in range(num_stalls):
        x_ft = stall_start_x
        y_ft = stall_start_y + i * (stall_h_ft + 2)  # 2' spacing
        if y_ft + stall_h_ft > pave_h_ft - 10:
            break
        stall_p1 = ft_to_page(x_ft, y_ft)
        stall_p2 = ft_to_page(x_ft + stall_w_ft, y_ft + stall_h_ft)
        # Ensure proper rect orientation
        stall_rect = fitz.Rect(
            min(stall_p1[0], stall_p2[0]), min(stall_p1[1], stall_p2[1]),
            max(stall_p1[0], stall_p2[0]), max(stall_p1[1], stall_p2[1])
        )
        page2.draw_rect(stall_rect, color=BLACK, width=0.5)
    
    # Border
    page2.draw_rect(fitz.Rect(18, 18, page_width-18, page_height-18), color=BLACK, width=1.0)
    
    # === PAGE 3: UTILITY PLAN (Sanitary, Storm, Water) ===
    page3 = doc.new_page(width=page_width, height=page_height)
    page3.insert_text((36, 30), "UTILITY PLAN – Sanitary, Storm, Water (schematic)", fontsize=16)
    page3.insert_text((56, 552), "Scale Bar (100 ft @ 1\"=20')", fontsize=9)
    page3.insert_text((356, 566), "N", fontsize=9)
    
    # Scale bar: 100 ft at true scale
    page3.draw_line((56, 540), (56 + scale_bar_length_pt, 540), color=BLACK, width=2.0)
    
    # Sanitary sewer (red): 350 LF horizontal line
    san_y_ft = 80
    san_start = ft_to_page(100, san_y_ft)
    san_end = ft_to_page(450, san_y_ft)  # 350 feet
    page3.draw_line(san_start, san_end, color=RED, width=1.0)
    
    # 5 manholes along sanitary line (depths 10, 12, 14, 16, 18')
    mh_x_positions_ft = [100, 187.5, 275, 362.5, 450]
    mh_depths = [10, 12, 14, 16, 18]
    for mh_x_ft, depth in zip(mh_x_positions_ft, mh_depths):
        mh_pos = ft_to_page(mh_x_ft, san_y_ft)
        # Draw MH symbol (small cross)
        page3.draw_line((mh_pos[0]-3, mh_pos[1]), (mh_pos[0]+3, mh_pos[1]), color=RED, width=1.0)
        page3.draw_line((mh_pos[0], mh_pos[1]-3), (mh_pos[0], mh_pos[1]+3), color=RED, width=1.0)
    
    # Storm drain (blue): 430 LF total
    # Main run: 350 LF horizontal + 4 × 20 LF drops = 430 LF
    storm_y_ft = 530
    storm_start = ft_to_page(100, storm_y_ft)
    storm_end = ft_to_page(450, storm_y_ft)  # 350 feet
    page3.draw_line(storm_start, storm_end, color=BLUE, width=1.0)
    
    # 4 inlet drops (20 LF each)
    inlet_x_positions_ft = [135, 222.5, 327.5, 415]
    for inlet_x_ft in inlet_x_positions_ft:
        inlet_top = ft_to_page(inlet_x_ft, 510)
        inlet_bottom = ft_to_page(inlet_x_ft, 530)
        page3.draw_line(inlet_top, inlet_bottom, color=BLUE, width=1.0)
        # Draw inlet symbol (small square)
        inlet_rect = fitz.Rect(inlet_top[0]-3, inlet_top[1]-3, inlet_top[0]+3, inlet_top[1]+3)
        page3.draw_rect(inlet_rect, color=BLUE, width=1.0)
    
    # Water main (green): 1,460 LF total
    # Rectangle loop: 290 + 440 + 290 + 440 = 1,460 LF
    water_points_ft = [
        (130, 80),
        (420, 80),   # 290 LF
        (420, 520),  # 440 LF
        (130, 520),  # 290 LF
        (130, 80)    # 440 LF (close loop)
    ]
    water_points_pdf = [ft_to_page(x, y) for x, y in water_points_ft]
    for i in range(len(water_points_pdf)-1):
        page3.draw_line(water_points_pdf[i], water_points_pdf[i+1], color=GREEN, width=1.0)
    
    # 2 hydrants
    hydrant_positions_ft = [(130, 520), (420, 80)]
    for hyd_ft in hydrant_positions_ft:
        hyd_pos = ft_to_page(hyd_ft[0], hyd_ft[1])
        # Draw hydrant symbol (small circle)
        page3.draw_circle(hyd_pos, 3, color=GREEN, width=1.0)
    
    # Border
    page3.draw_rect(fitz.Rect(18, 18, page_width-18, page_height-18), color=BLACK, width=1.0)
    
    # === PAGE 4: GRADING PLAN ===
    page4 = doc.new_page(width=page_width, height=page_height)
    page4.insert_text((36, 30), "GRADING – Existing / Proposed Contours (schematic)", fontsize=16)
    page4.insert_text((56, 552), "Scale Bar (100 ft @ 1\"=20')", fontsize=9)
    page4.insert_text((356, 566), "N", fontsize=9)
    
    # Scale bar: 100 ft at true scale
    page4.draw_line((56, 540), (56 + scale_bar_length_pt, 540), color=BLACK, width=2.0)
    
    # Draw some contour lines (not measured, just for visual)
    for elev in range(10):
        y_ft = 80 + elev * 40
        c_start = ft_to_page(60, y_ft)
        c_end = ft_to_page(540, y_ft)
        page4.draw_line(c_start, c_end, color=BLACK, width=0.5, dashes="[3 3] 0")
    
    # Border
    page4.draw_rect(fitz.Rect(18, 18, page_width-18, page_height-18), color=BLACK, width=1.0)
    
    # === PAGE 5: DETAILS ===
    page5 = doc.new_page(width=page_width, height=page_height)
    page5.insert_text((36, 30), "DETAILS – Schematic Sections (not to scale)", fontsize=16)
    page5.insert_text((36, 60), "Notes: Details are schematic. For software testing only.", fontsize=10)
    
    # Border
    page5.draw_rect(fitz.Rect(18, 18, page_width-18, page_height-18), color=BLACK, width=1.0)
    
    # Save PDF
    output_dir = Path(__file__).parent.parent / "backend" / "tests" / "assets"
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / "site_plan_warehouse_100k.pdf"
    doc.save(str(pdf_path))
    doc.close()
    
    # === GENERATE GROUND TRUTH JSON ===
    ground_truth = {
        "meta": {
            "title": "Schematic Site Plan - Test Vector PDF (True Scale)",
            "scale": "1\" = 20'",
            "units": "feet",
            "note": "Schematic for software validation. Not for construction."
        },
        "building": {
            "lower_left_ft": [bldg_cx_ft - bldg_w_ft/2, bldg_cy_ft - bldg_h_ft/2],
            "width_ft": bldg_w_ft,
            "height_ft": bldg_h_ft,
            "area_sf": bldg_w_ft * bldg_h_ft
        },
        "curbs": {
            "total_length_ft": 2 * (pave_w_ft + pave_h_ft),
            "segments": [{
                "polyline_ft": [[0, 0], [pave_w_ft, 0], [pave_w_ft, pave_h_ft], [0, pave_h_ft]],
                "length_ft": 2 * (pave_w_ft + pave_h_ft)
            }]
        },
        "sidewalks": {
            "total_area_sf": 0.0,
            "polygons": []
        },
        "pavement": {
            "total_area_sf": pave_w_ft * pave_h_ft - bldg_w_ft * bldg_h_ft,
            "polygons": [{
                "polygon_ft": [[0, 0], [pave_w_ft, 0], [pave_w_ft, pave_h_ft], [0, pave_h_ft]],
                "area_sf": pave_w_ft * pave_h_ft
            }]
        },
        "parking_stalls": {
            "count": num_stalls,
            "stall_size_ft": [stall_w_ft, stall_h_ft]
        },
        "utilities": {
            "sanitary": {
                "pipe_diam_in": 8,
                "total_length_ft": 350.0,
                "segments": [{
                    "from_ft": [100, 80],
                    "to_ft": [450, 80],
                    "length_ft": 350.0
                }],
                "manholes": [
                    {"center_ft": [100, 80], "invert_depth_ft": 10.0},
                    {"center_ft": [187.5, 80], "invert_depth_ft": 12.0},
                    {"center_ft": [275, 80], "invert_depth_ft": 14.0},
                    {"center_ft": [362.5, 80], "invert_depth_ft": 16.0},
                    {"center_ft": [450, 80], "invert_depth_ft": 18.0}
                ]
            },
            "storm": {
                "pipe_diam_in": 24,
                "total_length_ft": 430.0,
                "segments": [
                    {"from_ft": [100, 530], "to_ft": [450, 530], "length_ft": 350.0},
                    {"from_ft": [135, 510], "to_ft": [135, 530], "length_ft": 20.0},
                    {"from_ft": [222.5, 510], "to_ft": [222.5, 530], "length_ft": 20.0},
                    {"from_ft": [327.5, 510], "to_ft": [327.5, 530], "length_ft": 20.0},
                    {"from_ft": [415, 510], "to_ft": [415, 530], "length_ft": 20.0}
                ],
                "inlets": [
                    {"center_ft": [135, 510]},
                    {"center_ft": [222.5, 510]},
                    {"center_ft": [327.5, 510]},
                    {"center_ft": [415, 510]}
                ]
            },
            "water": {
                "pipe_diam_in": 12,
                "total_length_ft": 1460.0,
                "segments": [
                    {"from_ft": [130, 80], "to_ft": [420, 80], "length_ft": 290.0},
                    {"from_ft": [420, 80], "to_ft": [420, 520], "length_ft": 440.0},
                    {"from_ft": [420, 520], "to_ft": [130, 520], "length_ft": 290.0},
                    {"from_ft": [130, 520], "to_ft": [130, 80], "length_ft": 440.0}
                ],
                "hydrants": [
                    {"center_ft": [130, 520]},
                    {"center_ft": [420, 80]}
                ]
            }
        },
        "structures": {
            "count": 11
        },
        "contours": {
            "existing": [
                {"polyline_ft": [[60, 80+i*40], [540, 90+i*40]]} 
                for i in range(10)
            ],
            "proposed": [
                {"polyline_ft": [[80, 110+i*40], [520, 110+i*40]]} 
                for i in range(8)
            ]
        }
    }
    
    truth_path = output_dir / "site_plan_ground_truth.json"
    with open(truth_path, 'w') as f:
        json.dump(ground_truth, f, indent=2)
    
    # Print summary
    print("=" * 60)
    print("✅ Generated synthetic test site plan")
    print("=" * 60)
    print(f"PDF: {pdf_path}")
    print(f"Truth JSON: {truth_path}")
    print()
    print("Ground Truth Quantities:")
    print(f"  Building: {ground_truth['building']['area_sf']:.1f} SF ({bldg_w_ft}' × {bldg_h_ft}')")
    print(f"  Pavement: {ground_truth['pavement']['total_area_sf']:.1f} SF ({pave_w_ft}' × {pave_h_ft}')")
    print(f"  Curbs: {ground_truth['curbs']['total_length_ft']:.1f} LF (perimeter)")
    print(f"  Sanitary: {ground_truth['utilities']['sanitary']['total_length_ft']:,.0f} LF + {len(ground_truth['utilities']['sanitary']['manholes'])} MH")
    print(f"  Storm: {ground_truth['utilities']['storm']['total_length_ft']:,.0f} LF + {len(ground_truth['utilities']['storm']['inlets'])} inlets")
    print(f"  Water: {ground_truth['utilities']['water']['total_length_ft']:,.0f} LF + {len(ground_truth['utilities']['water']['hydrants'])} hydrants")
    print(f"  Parking: {ground_truth['parking_stalls']['count']} stalls")
    print("=" * 60)

if __name__ == "__main__":
    make_pdf_and_truth()

