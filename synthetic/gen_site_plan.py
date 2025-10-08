# synthetic/gen_site_plan.py
# Generate DXF (with layers/linetypes) + ground-truth JSON + PDF render
# Usage: python synthetic/gen_site_plan.py --seed 7 --count 3

import argparse, json, math, random
from pathlib import Path

import ezdxf
from ezdxf import units
from ezdxf.entities import Text
from ezdxf.enums import TextEntityAlignment
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt

# ---------- scene synthesis ----------

def gen_scene(seed=1):
    random.seed(seed)
    # simple 2x5 lots along a straight road
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

    # sample elevations (invert-out) for manholes
    invs = {"MH-1": 421.80, "MH-2": 421.10}

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

# ---------- PDF export (Matplotlib backend) ----------

def save_pdf(doc, out_pdf: Path):
    # This produces a vector PDF. Lineweights/linetypes are approximate but good enough for EstimAI tests.
    msp = doc.modelspace()
    fig = plt.figure(figsize=(36, 24), dpi=72)  # 36x24" sheet
    ax = fig.add_axes([0, 0, 1, 1])
    ctx = RenderContext(doc)
    backend = MatplotlibBackend(ax)
    Frontend(ctx, backend).draw_layout(msp, finalize=True)
    fig.savefig(out_pdf, bbox_inches="tight", pad_inches=0)
    plt.close(fig)

# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--count", type=int, default=1, help="number of sheets to generate with incremental seeds")
    ap.add_argument("--outdir", type=str, default="synthetic")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    seed = args.seed
    for i in range(args.count):
        scene = gen_scene(seed=seed)
        stem = f"site_plan_s{seed:02d}"
        dxf_path = outdir / f"{stem}.dxf"
        pdf_path = outdir / f"{stem}.pdf"
        gt_path  = outdir / f"ground_truth_s{seed:02d}.json"

        doc = build_dxf(scene, dxf_path)
        save_pdf(doc, pdf_path)
        gt_path.write_text(json.dumps(scene, indent=2))

        print(f"Wrote: {dxf_path}\n       {pdf_path}\n       {gt_path}")
        seed += 1

if __name__ == "__main__":
    main()

