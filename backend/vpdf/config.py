from __future__ import annotations
import math, json
from pathlib import Path

DEFAULT_CFG = {
  "colors": {
    "sanitary": "#cc0000",
    "storm":    "#0080ff",
    "water":    "#00aa55",
    "curb":     "#000000",
    "pavement_fill": "#f5f5f5",
    "building_fill": "#d4d4d4"
  },
  "tolerances": {
    "color": 0.08,
    "snap": 0.5,
    "min_scale_len": 120,
    "max_scale_len": 600,
    "min_curb_width": 1.5
  }
}

def _hex_to_rgb(hexcode: str):
  h = hexcode.lstrip("#")
  return tuple(int(h[i:i+2],16)/255.0 for i in (0,2,4))

def load_config(path: str | None = None):
  cfg = DEFAULT_CFG.copy()
  if path and Path(path).exists():
    user = json.loads(Path(path).read_text()) if path.endswith(".json") else None
    if user: cfg.update(user)
  palette = {k: _hex_to_rgb(v) for k,v in cfg["colors"].items()}
  return cfg, palette

def nearest_color(rgb, palette):
  name, dist = None, 10.0
  for n, c in palette.items():
    d = math.sqrt(sum((a-b)**2 for a,b in zip(rgb, c)))
    if d < dist:
      dist, name = d, n
  return name, dist

