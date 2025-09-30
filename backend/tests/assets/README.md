# Test Assets

This directory contains **synthetic vector PDF plans** for deterministic takeoff tests.

## Purpose

These files are programmatically generated to provide:
- **Reproducible test data** with known ground truth quantities
- **Vector-based geometry** (no raster/scanned content)
- **Predictable scale and dimensions** for validation

## Files

- `site_plan_warehouse_100k.pdf` - Multi-page vector PDF with site plan, utilities, and grading
- `site_plan_ground_truth.json` - JSON with exact quantities for validation

## Generation

To regenerate these files:

```bash
cd /Users/williamholt/estimai
python scripts/make_test_siteplan.py
```

The script is idempotent and will print the exact quantities being generated.

## Ground Truth Specifications

- **Scale**: 1" = 20' (72 PDF units = 20 feet)
- **Building**: 250' × 400' = 100,000 SF
- **Pavement**: Ring around building, net area = 85,000 SF
- **Curb**: Perimeter = 1,740 LF
- **Sanitary Sewer**: 350 LF + 5 manholes (depths 10-18')
- **Storm Drain**: 430 LF + 4 inlets
- **Water Main**: 1,460 LF + 2 hydrants
- **Parking**: 60 stalls

## Usage in Tests

Tests should use these paths:
```python
PDF = Path(__file__).parent / "assets" / "site_plan_warehouse_100k.pdf"
TRUTH = Path(__file__).parent / "assets" / "site_plan_ground_truth.json"
```

