# Synthetic Site Plan Generator

This directory contains a synthetic utility plan generator for testing EstimAI's takeoff pipeline.

## Overview

`gen_site_plan.py` generates:
- **DXF files** with proper layers, linetypes, and units (feet)
- **PDF files** (vector format via Matplotlib)
- **Ground truth JSON** with exact coordinates, elevations, and legend information

## Usage

```bash
# Generate 3 site plans with seeds 7, 8, 9
python synthetic/gen_site_plan.py --seed 7 --count 3

# Generate a single plan with seed 42
python synthetic/gen_site_plan.py --seed 42 --count 1
```

## Output Files

For seed 7, generates:
- `site_plan_s07.dxf` - AutoCAD DXF file with layers
- `site_plan_s07.pdf` - Vector PDF for EstimAI ingestion
- `ground_truth_s07.json` - Exact coordinates and metadata

## Features

### DXF Layers
- `C-ROAD` - Road centerline (dark gray)
- `C-PROP-LOT` - Property boundaries (light gray)
- `C-UTIL-WATR` - Water main (blue, solid)
- `C-UTIL-SSWR` - Sanitary sewer (green, dashed)
- `C-UTIL-STRM` - Storm drain (cyan, solid)
- `C-TEXT` - Text labels and annotations

### Coordinate System
- Units: **Feet** (`units.FT`)
- Scale: 1" = 40' (1.8 points per foot)
- All coordinates are in drawing feet

### Legend Information
- Water Main: Blue solid line, labeled "WM", "HYD", "GV"
- Sanitary Sewer: Green dashed line, labeled "SS", "SSMH", "INV"
- Storm Drain: Cyan solid line, labeled "CB", "DI", "FES"

### Elevations
- Manholes include invert elevations (e.g., "INV OUT=421.80'")
- Ground truth JSON contains exact elevation values
- Elevations stored in `ground_truth_sXX.json` under `elevations` key

## Scene Structure

Each generated plan contains:
- **Road**: 500ft straight centerline
- **Lots**: 10 rectangular lots (2 rows × 5 columns)
- **Water main**: Parallel to road
- **Sanitary sewer**: Parallel to road, offset -10ft
- **Storm drain**: Parallel to road, offset +10ft
- **Nodes**:
  - 2 hydrants (water)
  - 2 manholes (sanitary, with invert elevations)
  - 2 inlets (storm)

## Dependencies

```bash
pip install ezdxf matplotlib
```

## Common Issues & Notes

### Dashed Linetype
The code creates a `DASHED` linetype so `linetype:"DASHED"` won't crash in viewers that require it to exist.

### Units
Set to feet (`doc.units = units.FT`) so downstream CAD tools don't assume millimeters.

### Lineweights
Visually meaningful; exact thickness varies by viewer—fine for our tests.

### PDF Export
Matplotlib backend is good enough for EstimAI ingestion. If you prefer Inkscape/LibreCAD for higher CAD fidelity, you can still convert `*.dxf → *.pdf` later.

### API Changes
The script is compatible with `ezdxf >= 1.4.2`. Earlier versions had different APIs for:
- `units.FOOT` → `units.FT`
- `linetypes.add(name, dxfattribs={...})` → `linetypes.add(name, pattern=[...], description="...")`
- `text.set_pos(xy, align="LEFT")` → `text.set_placement(xy, align=TextEntityAlignment.LEFT)`

## Testing with EstimAI

```bash
# Upload the generated PDF to EstimAI
curl -F "session_id=test_synthetic" \
     -F "file=@synthetic/site_plan_s07.pdf" \
     http://localhost:8000/v1/agent/takeoff

# Compare results against ground truth
python scripts/compare_to_ground_truth.py \
    --result results/test_synthetic.json \
    --ground_truth synthetic/ground_truth_s07.json
```

## Ground Truth Structure

```json
{
  "scale": {"ratio": "1in=40ft", "points_per_foot": 1.8},
  "road": [[x1, y1], [x2, y2]],
  "lots": [[[x1,y1], [x2,y2], ...], ...],
  "water": [[x1, y1], [x2, y2]],
  "sewer": [[x1, y1], [x2, y2]],
  "storm": [[x1, y1], [x2, y2]],
  "nodes": {
    "hydrants": [[x, y], ...],
    "manholes": [[x, y], ...],
    "inlets": [[x, y], ...]
  },
  "elevations": {
    "MH-1": 421.80,
    "MH-2": 421.10
  },
  "legend": {
    "materials": [...],
    "line_types": [...],
    "color_map": [...]
  }
}
```

## Future Enhancements

Potential additions:
- More complex network topologies (branches, laterals)
- Varying pipe diameters and materials
- Elevation profiles along pipe runs
- Additional utility types (gas, electric, fiber)
- Curved roads and irregular lot shapes
- More realistic manhole labels and station references

