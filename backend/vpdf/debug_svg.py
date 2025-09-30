from __future__ import annotations
from pathlib import Path

def export_svg(px, out_path: str):
    xs = [p for ln in px.lines for p in (ln.p1[0], ln.p2[0])]
    ys = [p for ln in px.lines for p in (ln.p1[1], ln.p2[1])]
    if not xs or not ys:
        Path(out_path).write_text("<svg/>"); return
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    w, h = maxx-minx+20, maxy-miny+20
    lines = []
    for ln in px.lines:
        r,g,b = (ln.stroke or (0,0,0))
        r,g,b = int(r*255), int(g*255), int(b*255)
        x1,y1 = ln.p1[0]-minx+10, h-(ln.p1[1]-miny+10)
        x2,y2 = ln.p2[0]-minx+10, h-(ln.p2[1]-miny+10)
        lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="rgb({r},{g},{b})" stroke-width="{max(1, ln.width)}"/>')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{"".join(lines)}</svg>'
    Path(out_path).write_text(svg)

