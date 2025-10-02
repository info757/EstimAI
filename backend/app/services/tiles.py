"""Image tiling service for processing large images in chunks."""
import base64
import io
import math
from typing import List, Dict, Any
import numpy as np
from PIL import Image
import cv2


def make_tiles(img: np.ndarray, tile_px: int, overlap_px: int) -> List[Dict[str, Any]]:
    """
    Split an image into overlapping tiles.
    
    Args:
        img: Input image as numpy array (H, W, C)
        tile_px: Size of each tile in pixels
        overlap_px: Overlap between tiles in pixels
        
    Returns:
        List of tile dictionaries with tile_id, coordinates, and cropped image
    """
    if len(img.shape) != 3:
        raise ValueError("Image must be 3D array (H, W, C)")
    
    # Enforce tile size limits to prevent memory issues
    MAX_TILE_SIZE = 1024
    MAX_OVERLAP = 128
    
    if tile_px > MAX_TILE_SIZE:
        raise ValueError(f"Tile size {tile_px} exceeds maximum {MAX_TILE_SIZE}px")
    if overlap_px > MAX_OVERLAP:
        raise ValueError(f"Overlap {overlap_px} exceeds maximum {MAX_OVERLAP}px")
    if overlap_px >= tile_px:
        raise ValueError(f"Overlap {overlap_px} must be less than tile size {tile_px}")
    
    height, width, channels = img.shape
    tiles = []
    tile_id = 0
    
    # Calculate step size (tile size minus overlap)
    step_size = tile_px - overlap_px
    
    # Generate tiles
    for y in range(0, height, step_size):
        for x in range(0, width, step_size):
            # Calculate tile boundaries
            x0 = x
            y0 = y
            x1 = min(x + tile_px, width)
            y1 = min(y + tile_px, height)
            
            # Skip if tile would be too small (less than half the intended size)
            if (x1 - x0) < tile_px // 2 or (y1 - y0) < tile_px // 2:
                continue
            
            # Crop the tile
            tile_img = img[y0:y1, x0:x1]
            
            # Ensure tile is RGB (3 channels)
            if channels == 1:
                tile_img = np.stack([tile_img.squeeze()] * 3, axis=-1)
            elif channels == 4:
                tile_img = tile_img[:, :, :3]  # Drop alpha channel
            
            tiles.append({
                "tile_id": tile_id,
                "x0": int(x0),
                "y0": int(y0), 
                "x1": int(x1),
                "y1": int(y1),
                "image": tile_img
            })
            
            tile_id += 1
    
    return tiles


def encode_png_b64_capped(img: np.ndarray, max_bytes: int = 900_000) -> str:
    """
    Encode as PNG; if larger than max_bytes, downscale progressively until it fits.
    Returns base64 str without logging image content.
    
    Args:
        img: Image array (H, W, C) with values 0-255
        max_bytes: Maximum size in bytes (default 900KB)
        
    Returns:
        Base64 encoded PNG string
    """
    # Ensure image is in correct format
    if img.dtype != np.uint8:
        img = img.astype(np.uint8)
    
    scale = 1.0
    h, w = img.shape[:2]
    
    while True:
        if scale < 1.0:
            new_w = max(64, int(w * scale))
            new_h = max(64, int(h * scale))
            resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            resized = img
            
        ok, buf = cv2.imencode(".png", resized, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        if not ok:
            raise RuntimeError("PNG encode failed")
            
        b = buf.tobytes()
        if len(b) <= max_bytes or (resized.shape[0] <= 256 or resized.shape[1] <= 256):
            return base64.b64encode(b).decode("ascii")
            
        # reduce by ~15% each loop
        scale *= 0.85


def encode_jpg_b64_capped(img: np.ndarray, max_bytes: int = 600_000, q: int = 85) -> str:
    """
    Encode as JPEG; if larger than max_bytes, downscale progressively until it fits.
    Returns base64 str without logging image content.
    
    Args:
        img: Image array (H, W, C) with values 0-255
        max_bytes: Maximum size in bytes (default 600KB)
        q: JPEG quality (default 85)
        
    Returns:
        Base64 encoded JPEG string
    """
    # Ensure image is in correct format
    if img.dtype != np.uint8:
        img = img.astype(np.uint8)
    
    scale = 1.0
    h, w = img.shape[:2]
    
    while True:
        if scale < 1.0:
            new_w = max(64, int(w * scale))
            new_h = max(64, int(h * scale))
            resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            resized = img
            
        ok, buf = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, q])
        if not ok:
            raise RuntimeError("JPG encode failed")
            
        b = buf.tobytes()
        if len(b) <= max_bytes or (resized.shape[0] <= 256 or resized.shape[1] <= 256):
            return base64.b64encode(b).decode("ascii")
            
        scale *= 0.85
        if q > 70:  # gently lower quality if needed
            q -= 2


def b64encode_tile(img: np.ndarray) -> str:
    """
    Encode a numpy image array as base64 JPEG string with size capping.
    Uses JPEG for better compression on symbol detection tasks.
    
    Args:
        img: Image array (H, W, C) with values 0-255
        
    Returns:
        Base64 encoded JPEG string
    """
    return encode_jpg_b64_capped(img, max_bytes=600_000, q=85)


def process_image_tiles(img: np.ndarray, tile_px: int, overlap_px: int) -> List[Dict[str, Any]]:
    """
    Convenience function to create tiles and encode them as base64.
    
    Args:
        img: Input image as numpy array
        tile_px: Size of each tile in pixels  
        overlap_px: Overlap between tiles in pixels
        
    Returns:
        List of tile dictionaries with base64 encoded images
    """
    tiles = make_tiles(img, tile_px, overlap_px)
    
    # Add base64 encoded image to each tile
    for tile in tiles:
        tile["image_b64"] = encode_jpg_b64_capped(tile["image"], max_bytes=600_000, q=85)
        # Remove the numpy array to save memory
        del tile["image"]
    
    return tiles
