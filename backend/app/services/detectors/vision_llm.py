import cv2, math, json, base64
import numpy as np
from typing import List, Tuple
from pathlib import Path
from backend.app.core.config import settings
from backend.app.services.llm_client import VisionLLM
from backend.app.services.prompts import prompt_takeoff, TYPES

# ---- helpers (local to this file to keep things simple)

def make_tiles(img: np.ndarray, tile_px: int, overlap: int) -> List[dict]:
    H, W = img.shape[:2]
    tiles = []
    y = 0
    while y < H:
        x = 0
        y1 = min(H, y + tile_px)
        while x < W:
            x1 = min(W, x + tile_px)
            crop = img[y:y1, x:x1]
            tiles.append({"x0": x, "y0": y, "x1": x1, "y1": y1, "image": crop})
            x += tile_px - overlap
        y += tile_px - overlap
    return tiles

def encode_png_b64_capped(img: np.ndarray, max_bytes: int = 900_000) -> str:
    scale = 1.0
    h, w = img.shape[:2]
    while True:
        resized = img if scale >= 0.999 else cv2.resize(img, (max(64,int(w*scale)), max(64,int(h*scale))), cv2.INTER_AREA)
        ok, buf = cv2.imencode(".png", resized, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        if not ok: raise RuntimeError("PNG encode failed")
        b = buf.tobytes()
        if len(b) <= max_bytes or min(resized.shape[:2]) <= 256:
            return base64.b64encode(b).decode("ascii")
        scale *= 0.85

def nms_merge(points: List[Tuple[float,float,str,float]], radius: float = 24.0) -> List[Tuple[float,float,str,float]]:
    # points: (x, y, type, conf)
    out = []
    used = [False]*len(points)
    for i,(xi,yi,ti,ci) in enumerate(points):
        if used[i]: continue
        group = [(xi,yi,ti,ci)]
        used[i]=True
        for j,(xj,yj,tj,cj) in enumerate(points[i+1:], start=i+1):
            if used[j]: continue
            if tj!=ti: continue
            if (xi-xj)**2 + (yi-yj)**2 <= radius*radius:
                group.append((xj,yj,tj,cj)); used[j]=True
        # average weighted by conf
        s = sum(g[3] for g in group) or 1.0
        x = sum(g[0]*g[3] for g in group)/s
        y = sum(g[1]*g[3] for g in group)/s
        t = group[0][2]
        c = max(g[3] for g in group)
        out.append((x,y,t,c))
    return out

# ---- detector entry

class VisionLLMDetector:
    def __init__(self, model: str, tile_px: int, overlap_px: int):
        self.tile_px = tile_px
        self.overlap_px = overlap_px
        self.llm = VisionLLM(model)

    async def detect(self, page_rgb: np.ndarray) -> List[dict]:
        prompt, schema = prompt_takeoff(TYPES)
        tiles = make_tiles(page_rgb, self.tile_px, self.overlap_px)
        results: List[Tuple[float,float,str,float]] = []

        # sequential loop keeps payloads small and avoids rate spikes
        for t in tiles:
            b64 = encode_png_b64_capped(t["image"], 900_000)
            resp = await self.llm.infer(b64, prompt, schema)
            for d in resp.get("detections", []):
                x_abs = t["x0"] + float(d["x_px"])
                y_abs = t["y0"] + float(d["y_px"])
                results.append((x_abs, y_abs, d["type"], float(d["confidence"])))

        merged = nms_merge(results, radius=24.0)
        # jsonify
        return [{"type": t, "x_px": float(x), "y_px": float(y), "confidence": float(c)} for x,y,t,c in merged]
    
