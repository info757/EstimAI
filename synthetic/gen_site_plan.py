# synthetic/gen_site_plan.py
# Generate DXF (with layers/linetypes) + ground-truth JSON + PDF render
# Usage: python synthetic/gen_site_plan.py --seed 7 --count 3

import argparse, json, math, random
from pathlib import Path

import ezdxf
from ezdxf import units
from ezdxf.entities import Text
from ezdxf.enums import TextEntityAlignment

# Optional: matplotlib for fallback
try:
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# ReportLab for true vector PDF
try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.colors import HexColor as RLHexColor
    from reportlab.lib.units import inch
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# ---------- scene synthesis ----------

def _calc_polyline_length(polyline):
    """Calculate total length of a polyline in feet."""
    if not polyline or len(polyline) < 2:
        return 0.0
    
    total = 0.0
    for i in range(len(polyline) - 1):
        x1, y1 = polyline[i]
        x2, y2 = polyline[i + 1]
        segment_len = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        total += segment_len
    
    return total

def gen_scene(seed=1, complexity="medium"):
    random.seed(seed)
    
    if complexity == "simple":
        return _gen_simple_linear(seed)
    elif complexity == "complex":
        return _gen_complex_subdivision(seed)
    else:
        return _gen_medium_site(seed)


def _gen_simple_linear(seed):
    """Generate a simple linear utility plan - good for accuracy testing."""
    random.seed(seed)
    
    # Straight road
    road = [(0,0),(600,0)]
    
    # No lots - just utilities
    lots = []
    
    # Three parallel utilities with different characteristics
    water = [(50,0),(550,0)]  # 500 ft
    sewer = [(50,-15),(550,-15)]  # 500 ft, offset 15ft
    storm = [(50,15),(550,15)]  # 500 ft, offset 15ft
    
    # Nodes along the lines
    nodes = {
        "hydrants":[(150,0),(350,0),(450,0)],
        "manholes":[(100,-15),(300,-15),(500,-15)],
        "inlets":[(200,15),(400,15)]
    }
    
    return _finalize_scene(road, lots, water, sewer, storm, nodes, seed)


def _gen_medium_site(seed):
    """Generate medium complexity site - original design."""
    random.seed(seed)
    
    # 2x5 lots along a straight road
    lots = []
    road = [(0,0),(500,0)]
    for i in range(10):
        x0 = 25 + (i % 5) * 90
        y0 = 50 + (i // 5) * 120
        lots.append([(x0,y0),(x0+80,y0),(x0+80,y0+100),(x0,y0+100),(x0,y0)])

    # utilities along corridor, offset a bit
    water = [(20,0),(480,0)]
    sewer = [(20,-10),(480,-10)]
    storm = [(20,10),(480,10)]

    nodes = {
        "hydrants":[(100,5),(300,5)],
        "manholes":[(150,-10),(350,-10)],
        "inlets":[(200,10),(400,10)]
    }
    
    return _finalize_scene(road, lots, water, sewer, storm, nodes, seed)


def _gen_complex_subdivision(seed):
    """Generate complex subdivision with branches and varying materials."""
    random.seed(seed)
    
    # Curved road with cul-de-sac
    road = [(0,0),(300,0),(400,20),(450,60),(450,120)]
    
    # 8 lots around cul-de-sac
    lots = []
    for i in range(8):
        angle = i * 45  # degrees
        r = 80
        cx, cy = 450, 90  # cul-de-sac center
        x0 = cx + r * math.cos(math.radians(angle))
        y0 = cy + r * math.sin(math.radians(angle))
        # Simple rectangular lots radiating out
        lots.append([
            (x0, y0),
            (x0 + 40, y0),
            (x0 + 40, y0 + 60),
            (x0, y0 + 60),
            (x0, y0)
        ])
    
    # Utilities with branches
    # Main trunk along road
    water_main = [(20,0),(300,0),(400,20),(450,60)]
    # Branch to cul-de-sac
    water_branch = [(400,20),(450,90)]
    water = water_main  # For now, just main trunk
    
    sewer_main = [(20,-10),(300,-10),(400,10),(450,50)]
    sewer = sewer_main
    
    storm_main = [(20,10),(300,10),(400,30),(450,70)]
    storm = storm_main
    
    nodes = {
        "hydrants":[(100,5),(250,2),(400,25)],
        "manholes":[(80,-10),(200,-10),(350,15),(450,55)],
        "inlets":[(150,15),(300,15),(420,35)]
    }
    
    return _finalize_scene(road, lots, water, sewer, storm, nodes, seed)


def _finalize_scene(road, lots, water, sewer, storm, nodes, seed):
    """Finalize scene with elevations and profiles."""
    random.seed(seed)

    # Calculate actual utility lengths from coordinates
    water_len = _calc_polyline_length(water)
    sewer_len = _calc_polyline_length(sewer)
    storm_len = _calc_polyline_length(storm)
    
    # Generate realistic elevations based on seed
    base_elev = 420.0 + (seed % 5) * 10  # Vary base elevation: 420-460
    
    # Vary depths by utility type (realistic ranges)
    water_depth = 6.0 + random.uniform(0, 2)  # 6-8 ft (shallower)
    sewer_depth = 8.0 + random.uniform(0, 3)  # 8-11 ft (medium)
    storm_depth = 7.0 + random.uniform(0, 3)  # 7-10 ft (medium)
    
    # Vary slopes (realistic ranges)
    water_slope = 0.5 + random.uniform(0, 0.5)  # 0.5-1.0% (gentle)
    sewer_slope = 1.0 + random.uniform(0, 1.5)  # 1.0-2.5% (steeper)
    storm_slope = 0.5 + random.uniform(0, 1.0)  # 0.5-1.5% (variable)
    
    # Vary materials by seed
    materials = {
        "water": ["DI", "PVC C900", "HDPE"][seed % 3],
        "sewer": ["PVC SDR-35", "PVC SDR-26", "VCP"][seed % 3],
        "storm": ["RCP", "HDPE", "PVC"][seed % 3]
    }
    
    # Vary diameters
    diameters = {
        "water": [6, 8, 10, 12][seed % 4],
        "sewer": [8, 10, 12][seed % 3],
        "storm": [12, 15, 18][seed % 3]
    }
    
    # Build profiles with realistic variation
    ground_start = base_elev + 10.0
    ground_end = ground_start - (water_len * 0.005)  # 0.5% ground slope
    
    # Sample elevations for manholes
    invs = {}
    mh_nodes = nodes.get("manholes", [])
    for i, (x, y) in enumerate(mh_nodes, start=1):
        # Calculate invert based on position along sewer line
        progress = x / (sewer_len if sewer_len > 0 else 1)
        inv = (ground_start - sewer_depth) - (progress * sewer_len * sewer_slope / 100)
        invs[f"MH-{i}"] = round(inv, 2)
    
    profiles = {
        "water": {
            "start_station": 0,
            "end_station": int(water_len),
            "diameter_in": diameters["water"],
            "material": materials["water"],
            "ground_start": ground_start,
            "ground_end": ground_end,
            "invert_start": ground_start - water_depth,
            "invert_end": ground_end - water_depth - (water_len * water_slope / 100),
            "slope_pct": round(water_slope, 2)
        },
        "sewer": {
            "start_station": 0,
            "end_station": int(sewer_len),
            "diameter_in": diameters["sewer"],
            "material": materials["sewer"],
            "ground_start": ground_start,
            "ground_end": ground_end,
            "invert_start": ground_start - sewer_depth,
            "invert_end": ground_end - sewer_depth - (sewer_len * sewer_slope / 100),
            "slope_pct": round(sewer_slope, 2)
        },
        "storm": {
            "start_station": 0,
            "end_station": int(storm_len),
            "diameter_in": diameters["storm"],
            "material": materials["storm"],
            "ground_start": ground_start,
            "ground_end": ground_end,
            "invert_start": ground_start - storm_depth,
            "invert_end": ground_end - storm_depth - (storm_len * storm_slope / 100),
            "slope_pct": round(storm_slope, 2)
        }
    }

    legend = {
        "materials":[{"raw":"DIP","norm":"ductile_iron"},{"raw":"PVC","norm":"pvc"}],
        "line_types":[
            {"raw":"WATER MAIN","norm":"water","clues":["WM","HYD","GV"]},
            {"raw":"SANITARY SEWER","norm":"sewer","clues":["SS","SSMH","INV"]},
            {"raw":"STORM DRAIN","norm":"storm","clues":["CB","DI","FES"]},
        ],
        "color_map":[
            {"raw":"Blue solid","norm":"water"},
            {"raw":"Green dashed","norm":"sewer"},
            {"raw":"Cyan solid","norm":"storm"},
        ],
    }

    return {
        "scale": {"ratio":"1in=40ft", "points_per_foot": 72/40},  # 1.8 pt/ft (for the PDF exporter)
        "road": road, "lots": lots,
        "water": water, "sewer": sewer, "storm": storm,
        "nodes": nodes, "elevations": invs, "legend": legend,
        "profiles": profiles,  # Profile view data
    }

# ---------- DXF helpers ----------

def ensure_layers(doc):
    # Autodesk color indices: 1=red, 3=green, 5=blue-ish, 7=white/black, 8=dark gray, 252=light gray
    wanted = [
        ("C-ROAD", 8),
        ("C-PROP-LOT", 252),
        ("C-UTIL-WATR", 5),
        ("C-UTIL-SSWR", 3),
        ("C-UTIL-STRM", 4),  # cyan-ish
        ("C-TEXT", 7),
    ]
    for name, color in wanted:
        if name not in doc.layers:
            doc.layers.add(name, color=color)

def ensure_dashed_linetype(doc):
    # Some viewers crash if a referenced linetype doesn't exist.
    if "DASHED" not in doc.linetypes:
        # pattern: [total_length, line, gap, line, gap, ...]
        doc.linetypes.add(
            name="DASHED",
            pattern=[0.5, 0.35, -0.15],
            description="Dashed __ __ __ __",
        )

def add_text(msp, s, xy, layer="C-TEXT", h=2.5):
    text = msp.add_text(s, dxfattribs={"layer": layer, "height": h, "insert": xy})
    text.set_placement(xy, align=TextEntityAlignment.LEFT)

def build_dxf(scene, out_dxf: Path):
    # Use R2010 DXF; set units to FEET so CAD tools know your intent
    doc = ezdxf.new("R2010")
    doc.units = units.FT
    doc.header["$INSUNITS"] = units.FT

    ensure_layers(doc)
    ensure_dashed_linetype(doc)

    msp = doc.modelspace()

    # road centerline
    msp.add_lwpolyline(scene["road"], dxfattribs={"layer":"C-ROAD", "lineweight":25})

    # lots
    for poly in scene["lots"]:
        msp.add_lwpolyline(poly, dxfattribs={"layer":"C-PROP-LOT", "lineweight":15, "closed": True})

    # utilities
    msp.add_lwpolyline(scene["water"], dxfattribs={"layer":"C-UTIL-WATR", "lineweight":35})
    msp.add_lwpolyline(scene["sewer"], dxfattribs={"layer":"C-UTIL-SSWR", "lineweight":35, "linetype":"DASHED"})
    msp.add_lwpolyline(scene["storm"], dxfattribs={"layer":"C-UTIL-STRM", "lineweight":35})

    # nodes + labels
    for (x,y) in scene["nodes"]["hydrants"]:
        msp.add_circle((x,y), 3, dxfattribs={"layer":"C-UTIL-WATR"})
        add_text(msp, "HYD", (x+4,y+2))

    for i,(x,y) in enumerate(scene["nodes"]["manholes"], start=1):
        msp.add_circle((x,y), 2.5, dxfattribs={"layer":"C-UTIL-SSWR"})
        inv = scene["elevations"].get(f"MH-{i}", 421.00)
        add_text(msp, f"SSMH-{i}  INV OUT={inv:.2f}'", (x+4,y-2))

    for (x,y) in scene["nodes"]["inlets"]:
        msp.add_solid([(x-2,y-2),(x+2,y-2),(x+2,y+2),(x-2,y+2)], dxfattribs={"layer":"C-UTIL-STRM"})
        add_text(msp, "DI", (x+4,y))

    # legend block (simple text)
    add_text(msp, "LEGEND:", (20,60))
    add_text(msp, "WATER MAIN (Blue, Solid)  - WM, HYD, GV", (20,56))
    add_text(msp, "SANITARY SEWER (Green, Dashed) - SS, SSMH, INV", (20,52))
    add_text(msp, "STORM DRAIN (Cyan, Solid) - CB, DI, FES", (20,48))

    # quick modelspace view so some viewers center content
    try:
        doc.set_modelspace_vport(350, center=(250, 60))
    except Exception:
        pass

    doc.saveas(out_dxf)
    return doc

# ---------- PDF export (ReportLab - TRUE vector) ----------

def save_pdf_reportlab(scene, out_pdf: Path):
    """Generate TRUE vector PDF using ReportLab (Apryse can extract these!)"""
    if not HAS_REPORTLAB:
        raise ImportError("ReportLab not installed. Run: pip install reportlab")
    
    # Create PDF canvas - landscape letter
    c = rl_canvas.Canvas(str(out_pdf), pagesize=landscape(letter))
    width, height = landscape(letter)
    
    # Scale factor: our scene is 0-500 ft wide, PDF is 11 inches wide
    # Leave margins: use 10 inches for drawing
    scale = (10 * inch) / 500  # points per foot in our coordinate system
    
    # Origin offset (1 inch margin from left, center vertically)
    origin_x = 0.5 * inch
    origin_y = 1 * inch
    
    def to_pdf(x, y):
        """Convert scene coordinates (feet) to PDF points"""
        return (origin_x + x * scale, origin_y + y * scale)
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(width/2 - 100, height - 30, "UTILITY PLAN - TEST SITE")
    
    # Scale bar
    c.setFont("Helvetica-Bold", 10)
    c.drawString(width - 150, height - 30, "SCALE: 1\" = 40'")
    
    # Legend
    legend_x, legend_y = 30, height - 80
    c.setFont("Helvetica-Bold", 10)
    c.drawString(legend_x, legend_y, "LEGEND:")
    c.setFont("Helvetica", 9)
    
    # Water legend
    c.setStrokeColor(RLHexColor('#0000FF'))
    c.setLineWidth(2)
    c.line(legend_x, legend_y - 20, legend_x + 30, legend_y - 20)
    c.setFillColor(RLHexColor('#000000'))
    c.drawString(legend_x + 35, legend_y - 23, "WATER MAIN (Blue, Solid) - WM, HYD, GV")
    
    # Sanitary legend
    c.setStrokeColor(RLHexColor('#00AA00'))
    c.setLineWidth(2)
    c.setDash([3, 2])
    c.line(legend_x, legend_y - 40, legend_x + 30, legend_y - 40)
    c.setDash([])
    c.drawString(legend_x + 35, legend_y - 43, "SANITARY SEWER (Green, Dashed) - SS, SSMH, INV")
    
    # Storm legend
    c.setStrokeColor(RLHexColor('#00AAAA'))
    c.setLineWidth(2)
    c.line(legend_x, legend_y - 60, legend_x + 30, legend_y - 60)
    c.drawString(legend_x + 35, legend_y - 63, "STORM DRAIN (Cyan, Solid) - CB, DI, FES")
    
    # Draw road
    c.setStrokeColor(RLHexColor('#666666'))
    c.setLineWidth(3)
    pts = [to_pdf(x, y) for x, y in scene["road"]]
    p = c.beginPath()
    p.moveTo(*pts[0])
    for pt in pts[1:]:
        p.lineTo(*pt)
    c.drawPath(p, stroke=1, fill=0)
    
    # Draw lots
    c.setStrokeColor(RLHexColor('#CCCCCC'))
    c.setLineWidth(1)
    for lot in scene["lots"]:
        pts = [to_pdf(x, y) for x, y in lot]
        p = c.beginPath()
        p.moveTo(*pts[0])
        for pt in pts[1:]:
            p.lineTo(*pt)
        c.drawPath(p, stroke=1, fill=0)
    
    # Draw water main
    c.setStrokeColor(RLHexColor('#0000FF'))
    c.setLineWidth(2)
    pts = [to_pdf(x, y) for x, y in scene["water"]]
    p = c.beginPath()
    p.moveTo(*pts[0])
    for pt in pts[1:]:
        p.lineTo(*pt)
    c.drawPath(p, stroke=1, fill=0)
    
    # Draw sanitary sewer (dashed)
    c.setStrokeColor(RLHexColor('#00AA00'))
    c.setLineWidth(2)
    c.setDash([3, 2])
    pts = [to_pdf(x, y) for x, y in scene["sewer"]]
    p = c.beginPath()
    p.moveTo(*pts[0])
    for pt in pts[1:]:
        p.lineTo(*pt)
    c.drawPath(p, stroke=1, fill=0)
    c.setDash([])
    
    # Draw storm drain
    c.setStrokeColor(RLHexColor('#00AAAA'))
    c.setLineWidth(2)
    pts = [to_pdf(x, y) for x, y in scene["storm"]]
    p = c.beginPath()
    p.moveTo(*pts[0])
    for pt in pts[1:]:
        p.lineTo(*pt)
    c.drawPath(p, stroke=1, fill=0)
    
    # Draw nodes and labels
    c.setFont("Helvetica", 7)
    c.setFillColor(RLHexColor('#000000'))
    
    # Hydrants
    c.setStrokeColor(RLHexColor('#0000FF'))
    c.setLineWidth(1)
    for x, y in scene["nodes"]["hydrants"]:
        px, py = to_pdf(x, y)
        c.circle(px, py, 3, stroke=1, fill=0)
        c.drawString(px + 4, py + 2, "HYD")
    
    # Manholes with invert elevations
    c.setStrokeColor(RLHexColor('#00AA00'))
    for i, (x, y) in enumerate(scene["nodes"]["manholes"], start=1):
        px, py = to_pdf(x, y)
        c.circle(px, py, 2.5, stroke=1, fill=0)
        inv = scene["elevations"].get(f"MH-{i}", 421.00)
        c.drawString(px + 4, py - 2, f"SSMH-{i}  INV OUT={inv:.2f}'")
    
    # Inlets
    c.setStrokeColor(RLHexColor('#00AAAA'))
    c.setFillColor(RLHexColor('#00AAAA'))
    for x, y in scene["nodes"]["inlets"]:
        px, py = to_pdf(x, y)
        c.rect(px - 2, py - 2, 4, 4, stroke=0, fill=1)
        c.setFillColor(RLHexColor('#000000'))
        c.drawString(px + 4, py, "DI")
        c.setFillColor(RLHexColor('#00AAAA'))
    
    c.save()


def save_pdf_reportlab_with_profile(scene, out_pdf: Path):
    """Generate TRUE vector PDF with plan view (page 1) and profile view (page 2)."""
    if not HAS_REPORTLAB:
        raise ImportError("ReportLab not installed. Run: pip install reportlab")
    
    # Create PDF canvas - landscape letter
    c = rl_canvas.Canvas(str(out_pdf), pagesize=landscape(letter))
    width, height = landscape(letter)
    
    # ========== PAGE 1: PLAN VIEW ==========
    _draw_plan_view(c, scene, width, height)
    c.showPage()  # Start new page
    
    # ========== PAGE 2: PROFILE VIEW ==========
    _draw_profile_view(c, scene, width, height)
    
    c.save()


def _draw_plan_view(c, scene, width, height):
    """Draw the plan view (same as before)."""
    # Scale factor: our scene is 0-500 ft wide, PDF is 11 inches wide
    # Leave margins: use 10 inches for drawing
    scale = (10 * inch) / 500  # points per foot in our coordinate system
    
    # Origin offset (1 inch margin from left, center vertically)
    origin_x = 0.5 * inch
    origin_y = 1 * inch
    
    def to_pdf(x, y):
        """Convert scene coordinates (feet) to PDF points"""
        return (origin_x + x * scale, origin_y + y * scale)
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(width/2 - 100, height - 30, "UTILITY PLAN - PLAN VIEW")
    
    # Scale bar
    c.setFont("Helvetica-Bold", 10)
    c.drawString(width - 150, height - 30, "SCALE: 1\" = 40'")
    
    # Legend
    legend_x, legend_y = 30, height - 80
    c.setFont("Helvetica-Bold", 10)
    c.drawString(legend_x, legend_y, "LEGEND:")
    c.setFont("Helvetica", 9)
    
    # Water legend
    c.setStrokeColor(RLHexColor('#0000FF'))
    c.setLineWidth(2)
    c.line(legend_x, legend_y - 20, legend_x + 30, legend_y - 20)
    c.setFillColor(RLHexColor('#000000'))
    c.drawString(legend_x + 35, legend_y - 23, "WATER MAIN (Blue, Solid) - WM, HYD, GV - 8\" DI")
    
    # Sanitary legend
    c.setStrokeColor(RLHexColor('#00AA00'))
    c.setLineWidth(2)
    c.setDash([3, 2])
    c.line(legend_x, legend_y - 40, legend_x + 30, legend_y - 40)
    c.setDash([])
    c.drawString(legend_x + 35, legend_y - 43, "SANITARY SEWER (Green, Dashed) - SS, SSMH, INV - 8\" PVC")
    
    # Storm legend
    c.setStrokeColor(RLHexColor('#00AAAA'))
    c.setLineWidth(2)
    c.line(legend_x, legend_y - 60, legend_x + 30, legend_y - 60)
    c.drawString(legend_x + 35, legend_y - 63, "STORM DRAIN (Cyan, Solid) - CB, DI, FES - 12\" RCP")
    
    # Draw road
    c.setStrokeColor(RLHexColor('#666666'))
    c.setLineWidth(3)
    pts = [to_pdf(x, y) for x, y in scene["road"]]
    p = c.beginPath()
    p.moveTo(*pts[0])
    for pt in pts[1:]:
        p.lineTo(*pt)
    c.drawPath(p, stroke=1, fill=0)
    
    # Draw lots
    c.setStrokeColor(RLHexColor('#CCCCCC'))
    c.setLineWidth(1)
    for lot in scene["lots"]:
        pts = [to_pdf(x, y) for x, y in lot]
        p = c.beginPath()
        p.moveTo(*pts[0])
        for pt in pts[1:]:
            p.lineTo(*pt)
        c.drawPath(p, stroke=1, fill=0)
    
    # Draw water main
    c.setStrokeColor(RLHexColor('#0000FF'))
    c.setLineWidth(2)
    pts = [to_pdf(x, y) for x, y in scene["water"]]
    p = c.beginPath()
    p.moveTo(*pts[0])
    for pt in pts[1:]:
        p.lineTo(*pt)
    c.drawPath(p, stroke=1, fill=0)
    
    # Draw sanitary sewer (dashed)
    c.setStrokeColor(RLHexColor('#00AA00'))
    c.setLineWidth(2)
    c.setDash([3, 2])
    pts = [to_pdf(x, y) for x, y in scene["sewer"]]
    p = c.beginPath()
    p.moveTo(*pts[0])
    for pt in pts[1:]:
        p.lineTo(*pt)
    c.drawPath(p, stroke=1, fill=0)
    c.setDash([])
    
    # Draw storm drain
    c.setStrokeColor(RLHexColor('#00AAAA'))
    c.setLineWidth(2)
    pts = [to_pdf(x, y) for x, y in scene["storm"]]
    p = c.beginPath()
    p.moveTo(*pts[0])
    for pt in pts[1:]:
        p.lineTo(*pt)
    c.drawPath(p, stroke=1, fill=0)
    
    # Draw nodes and labels
    c.setFont("Helvetica", 7)
    c.setFillColor(RLHexColor('#000000'))
    
    # Hydrants
    c.setStrokeColor(RLHexColor('#0000FF'))
    c.setLineWidth(1)
    for x, y in scene["nodes"]["hydrants"]:
        px, py = to_pdf(x, y)
        c.circle(px, py, 3, stroke=1, fill=0)
        c.drawString(px + 4, py + 2, "HYD")
    
    # Manholes with invert elevations
    c.setStrokeColor(RLHexColor('#00AA00'))
    for i, (x, y) in enumerate(scene["nodes"]["manholes"], start=1):
        px, py = to_pdf(x, y)
        c.circle(px, py, 2.5, stroke=1, fill=0)
        inv = scene["elevations"].get(f"MH-{i}", 421.00)
        c.drawString(px + 4, py - 2, f"SSMH-{i}  INV OUT={inv:.2f}'")
    
    # Inlets
    c.setStrokeColor(RLHexColor('#00AAAA'))
    c.setFillColor(RLHexColor('#00AAAA'))
    for x, y in scene["nodes"]["inlets"]:
        px, py = to_pdf(x, y)
        c.rect(px - 2, py - 2, 4, 4, stroke=0, fill=1)
        c.setFillColor(RLHexColor('#000000'))
        c.drawString(px + 4, py, "DI")
        c.setFillColor(RLHexColor('#00AAAA'))


def _draw_profile_view(c, scene, width, height):
    """Draw profile view with three separate profile strips (one per utility)."""
    profiles = scene.get("profiles", {})
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(width/2 - 120, height - 30, "UTILITY PLAN - PROFILE VIEW")
    
    # Scale
    c.setFont("Helvetica", 10)
    c.drawString(width - 200, height - 30, "HORIZ: 1\" = 40'  VERT: 1\" = 10'")
    
    # Drawing area - divide into 3 horizontal strips (one per utility)
    margin_x = 1.5 * inch
    margin_y = 0.5 * inch
    draw_width = width - (2 * margin_x)
    strip_height = (height - margin_y - (1 * inch)) / 3  # Divide into 3 strips
    
    # Horizontal scale: 460 ft → draw_width
    h_scale = draw_width / 500  # points per foot horizontal
    
    # Vertical scale within each strip: ~20 ft range
    v_scale = strip_height / 30  # points per foot vertical
    
    # Draw each utility in its own strip
    utilities = [
        ("water", profiles.get("water", {}), RLHexColor('#0000FF'), "WATER MAIN", 0),
        ("sewer", profiles.get("sewer", {}), RLHexColor('#00AA00'), "SANITARY SEWER", 1),
        ("storm", profiles.get("storm", {}), RLHexColor('#00AAAA'), "STORM DRAIN", 2),
    ]
    
    for util_name, prof, color, label, strip_idx in utilities:
        if not prof:
            continue
        
        # Calculate strip base Y
        strip_base_y = height - (1 * inch) - ((strip_idx + 1) * strip_height)
        
        def to_profile(station, elevation_offset):
            """Convert station and elevation offset to PDF coordinates."""
            x = margin_x + (station * h_scale)
            y = strip_base_y + (elevation_offset * v_scale)
            return (x, y)
        
        # Draw strip border
        c.setStrokeColor(RLHexColor('#CCCCCC'))
        c.setLineWidth(0.5)
        c.rect(margin_x, strip_base_y, draw_width, strip_height, stroke=1, fill=0)
        
        # Title for this strip
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(color)
        c.drawString(margin_x + 10, strip_base_y + strip_height - 20, label)
        
        # Ground elevation (flat line at top of strip)
        ground_avg = (prof["ground_start"] + prof["ground_end"]) / 2
        c.setStrokeColor(RLHexColor('#000000'))
        c.setLineWidth(2)
        x1, y_ground = to_profile(0, 25)  # Top of strip
        x2, _ = to_profile(prof["end_station"], 25)
        c.line(x1, y_ground, x2, y_ground)
        
        # Ground elevation label
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(RLHexColor('#000000'))
        c.drawString(x1 - 80, y_ground - 3, f"GL={ground_avg:.1f}'")
        
        # Pipe invert line (sloping down)
        # Calculate vertical positions relative to strip base
        depth_start = prof["ground_start"] - prof["invert_start"]
        depth_end = prof["ground_end"] - prof["invert_end"]
        
        # Position pipe relative to ground line
        c.setStrokeColor(color)
        c.setLineWidth(3)
        xi1, yi1 = to_profile(0, 25 - depth_start)
        xi2, yi2 = to_profile(prof["end_station"], 25 - depth_end)
        c.line(xi1, yi1, xi2, yi2)
        
        # Draw pipe diameter (circle at start and end)
        dia_pts = (prof["diameter_in"] / 12.0) * v_scale
        c.circle(xi1, yi1, dia_pts/2, stroke=1, fill=0)
        c.circle(xi2, yi2, dia_pts/2, stroke=1, fill=0)
        
        # Station markers
        c.setFont("Helvetica", 7)
        c.setFillColor(RLHexColor('#666666'))
        for sta in range(0, 500, 100):
            x, y_marker = to_profile(sta, 0)
            c.setStrokeColor(RLHexColor('#DDDDDD'))
            c.setLineWidth(0.5)
            c.line(x, strip_base_y, x, strip_base_y + strip_height)
            c.setFillColor(RLHexColor('#666666'))
            c.drawString(x - 12, strip_base_y - 8, f"{sta}+00")
        
        # Start point annotations (left side)
        c.setFont("Helvetica", 8)
        c.setFillColor(RLHexColor('#000000'))
        c.drawString(xi1 + 5, yi1 + 15, f"IE={prof['invert_start']:.1f}'")
        c.drawString(xi1 + 5, yi1 + 5, f"Depth={depth_start:.1f}'")
        c.drawString(xi1 + 5, yi1 - 5, f"{prof['diameter_in']}\" {prof['material']}")
        
        # End point annotations (right side)
        c.drawString(xi2 - 80, yi2 + 15, f"IE={prof['invert_end']:.1f}'")
        c.drawString(xi2 - 80, yi2 + 5, f"Depth={depth_end:.1f}'")
        c.drawString(xi2 - 80, yi2 - 5, f"Slope={prof['slope_pct']:.1f}%")
    
    # Legend for profile
    legend_x = 30
    legend_y = 100
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(RLHexColor('#000000'))
    c.drawString(legend_x, legend_y, "PROFILE LEGEND:")
    c.setFont("Helvetica", 9)
    c.drawString(legend_x, legend_y - 15, "IE = Invert Elevation (BOTTOM INSIDE of pipe, feet above sea level)")
    c.drawString(legend_x, legend_y - 28, "GL = Ground Level (surface, feet above sea level)")
    c.drawString(legend_x, legend_y - 41, "STA = Station (horizontal distance in feet)")
    c.drawString(legend_x, legend_y - 54, "Black line = Ground surface")
    c.drawString(legend_x, legend_y - 67, "Colored line = Pipe invert (bottom of pipe)")
    c.drawString(legend_x, legend_y - 80, "Circle = Pipe diameter (shown to scale)")
    
    # Note about depth calculation
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(RLHexColor('#CC0000'))
    c.drawString(legend_x, legend_y - 100, "DEPTH TO INVERT = GL - IE")
    c.drawString(legend_x, legend_y - 113, "COVER (to top of pipe) = GL - IE - diameter")
    
    # Add note about elevations being in feet above sea level
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(RLHexColor('#CC0000'))
    c.drawString(width/2 - 150, height - 50, "NOTE: All elevations in feet above sea level (MSL)")

# ---------- PDF export (Matplotlib backend - FALLBACK) ----------

def save_pdf_matplotlib(doc, out_pdf: Path):
    """Matplotlib backend - produces rasterized content (not ideal for Apryse)"""
    if not HAS_MATPLOTLIB:
        raise ImportError("Matplotlib not installed")
    
    msp = doc.modelspace()
    fig = plt.figure(figsize=(11, 8.5), dpi=72, facecolor='white')
    ax = fig.add_axes([0, 0, 1, 1], facecolor='white')
    ax.set_xlim(0, 500)
    ax.set_ylim(-20, 180)
    ax.set_aspect('equal')
    ax.axis('off')
    
    ctx = RenderContext(doc)
    backend = MatplotlibBackend(ax)
    Frontend(ctx, backend).draw_layout(msp, finalize=True)
    
    fig.savefig(out_pdf, format='pdf', bbox_inches='tight', pad_inches=0.1, dpi=72, facecolor='white')
    plt.close(fig)

def save_pdf(scene, doc, out_pdf: Path):
    """Save PDF using best available method"""
    if HAS_REPORTLAB:
        print(f"  Using ReportLab (true vector PDF with profile view)")
        save_pdf_reportlab_with_profile(scene, out_pdf)
    elif HAS_MATPLOTLIB:
        print(f"  Using Matplotlib (rasterized PDF - not ideal)")
        save_pdf_matplotlib(doc, out_pdf)
    else:
        raise ImportError("Neither ReportLab nor Matplotlib available for PDF export")

# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="Generate synthetic utility construction plans")
    ap.add_argument("--seed", type=int, default=7, help="Random seed for generation")
    ap.add_argument("--count", type=int, default=1, help="Number of sheets to generate")
    ap.add_argument("--complexity", type=str, default="medium", 
                    choices=["simple", "medium", "complex"],
                    help="Complexity level: simple (linear), medium (subdivision), complex (curved)")
    ap.add_argument("--outdir", type=str, default="synthetic", help="Output directory")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    seed = args.seed
    for i in range(args.count):
        scene = gen_scene(seed=seed, complexity=args.complexity)
        
        # Include complexity in filename
        complexity_code = {"simple": "lin", "medium": "sub", "complex": "cplx"}[args.complexity]
        stem = f"site_plan_{complexity_code}_s{seed:02d}"
        dxf_path = outdir / f"{stem}.dxf"
        pdf_path = outdir / f"{stem}.pdf"
        gt_path  = outdir / f"ground_truth_{complexity_code}_s{seed:02d}.json"

        doc = build_dxf(scene, dxf_path)
        save_pdf(scene, doc, pdf_path)
        gt_path.write_text(json.dumps(scene, indent=2))

        print(f"[{args.complexity.upper()}] Wrote:")
        print(f"  DXF:  {dxf_path}")
        print(f"  PDF:  {pdf_path}")
        print(f"  JSON: {gt_path}")
        print(f"  Pipes: {len(scene['water'])} water, {len(scene['sewer'])} sewer, {len(scene['storm'])} storm")
        print()
        seed += 1

if __name__ == "__main__":
    main()

