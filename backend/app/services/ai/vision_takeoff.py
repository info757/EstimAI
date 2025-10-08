"""
LLM Vision-based takeoff - reads PDF pages as images and extracts everything.

This is a pure LLM approach that doesn't rely on Apryse vector extraction.
Instead, it uses GPT-4o with vision to read the drawing like a human would.
"""
import logging
import os
import base64
from typing import Any, Dict, List, Optional, Tuple
import json
import httpx
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

logger = logging.getLogger(__name__)


async def extract_pipes_from_pdf_vision_async(
    pdf_path: str,
    page_num: int = 0,
    model: str = "gpt-4o",
    timeout: int = 120
) -> Dict[str, Any]:
    """
    Extract utility pipes from a PDF page using GPT-4o vision.
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page index (0-based)
        model: OpenAI vision model to use
        timeout: Request timeout in seconds
    
    Returns:
        Dict with networks: {storm: [...], sanitary: [...], water: [...]}
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    
    # Convert PDF page to image
    image_base64 = await _pdf_page_to_base64(pdf_path, page_num)
    
    system_prompt = """You are an expert civil engineer analyzing utility construction plans. 
Your task is to identify ALL utility pipes and extract their complete information.

Read the drawing like a human engineer would:

1. FIND AND READ THE LEGEND
   - Understand what symbols, colors, and abbreviations mean
   - Note material specifications (e.g., "8\" DI" = 8-inch ductile iron)

2. FIND AND READ THE SCALE
   - Understand horizontal distances (e.g., "1\" = 40'")
   - If there's a profile view, note vertical scale too

3. IDENTIFY UTILITY LINES
   - Water main, sanitary sewer, storm drain
   - Look in both plan view (top-down) and profile view (side elevation) if present

4. EXTRACT COMPLETE INFORMATION:
   - Length in feet (measure using scale or read from stations)
   - Material (PVC, DI, RCP, concrete, etc.)
   - Diameter in inches
   - Invert elevations (IE or INV) in feet above sea level
     * Look for labels like "IE=420.0'" or "INV=410.8'"
     * In profile views, read the elevation values from the Y-axis grid
     * Invert is the BOTTOM INSIDE of the pipe
   - Ground elevation (GL) in feet above sea level
   - Slope percentage if shown

CRITICAL FOR ELEVATIONS:
- Elevation values are typically 100-500 feet above sea level (not 0-100)
- Read elevation labels carefully - look for "IE=420.0'" not coordinates
- In profile views, the Y-axis shows elevation (e.g., 410', 415', 420', 425', 430')
- Don't confuse station numbers (0+00, 1+00) with elevations

Be thorough but accurate:
- Only report pipes you can clearly see
- Don't guess at values - use null if not visible
- Read elevation labels from text annotations, not from visual position"""

    user_prompt = """Analyze this utility plan drawing and extract ALL utility pipes.

For EACH pipe you identify, provide:
- discipline: "storm", "sanitary", or "water"
- start_point: [x, y] coordinates in feet (use scale)
- end_point: [x, y] coordinates in feet
- length_ft: calculated length in feet
- material: pipe material (pvc, ductile_iron, concrete, etc.)
- dia_in: diameter in inches
- invert_in: invert elevation at start (if shown)
- invert_out: invert elevation at end (if shown)
- notes: any other relevant information

Return JSON with this structure:
{
  "scale": {"ratio": "1in=40ft", "feet_per_inch": 40.0},
  "legend": ["text from legend explaining symbols"],
  "storm_pipes": [
    {
      "id": "storm_1",
      "start_point": [20, 10],
      "end_point": [480, 10],
      "length_ft": 460.0,
      "material": "pvc",
      "dia_in": 12.0,
      "invert_in": null,
      "invert_out": null,
      "notes": "Main storm line along road"
    }
  ],
  "sanitary_pipes": [...],
  "water_pipes": [...]
}"""
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.info(f"🤖 Calling GPT-4o vision to analyze PDF page {page_num}...")
            
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_base64}",
                                        "detail": "high"
                                    }
                                }
                            ]
                        }
                    ],
                    "temperature": 0,
                    "max_tokens": 4000,
                    "response_format": {"type": "json_object"}
                }
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            
            # Log what we got
            storm_count = len(parsed.get("storm_pipes", []))
            sanitary_count = len(parsed.get("sanitary_pipes", []))
            water_count = len(parsed.get("water_pipes", []))
            
            logger.info(
                f"✅ Vision LLM extracted: {storm_count} storm, "
                f"{sanitary_count} sanitary, {water_count} water pipes"
            )
            
            return parsed
    
    except Exception as e:
        logger.error(f"❌ Vision LLM extraction failed: {e}", exc_info=True)
        return {
            "storm_pipes": [],
            "sanitary_pipes": [],
            "water_pipes": [],
            "error": str(e)
        }


async def _pdf_page_to_base64(pdf_path: str, page_num: int = 0) -> str:
    """Convert PDF page to base64-encoded PNG image."""
    try:
        import fitz  # PyMuPDF
        
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        
        # Render at high DPI for better quality
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale = 144 DPI
        
        # Convert to PNG bytes
        png_bytes = pix.tobytes("png")
        
        # Encode to base64
        import base64
        b64 = base64.b64encode(png_bytes).decode('utf-8')
        
        logger.info(f"Converted PDF page {page_num} to image: {len(png_bytes)} bytes → {len(b64)} b64 chars")
        
        doc.close()
        return b64
    
    except Exception as e:
        logger.error(f"Failed to convert PDF to image: {e}")
        raise


def extract_pipes_from_pdf_vision(
    pdf_path: str,
    page_num: int = 0,
    model: str = "gpt-4o",
    timeout: int = 120
) -> Dict[str, Any]:
    """Synchronous wrapper for vision-based extraction (single page)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    extract_pipes_from_pdf_vision_async(pdf_path, page_num, model, timeout)
                )
                return future.result(timeout=timeout + 10)
        else:
            return loop.run_until_complete(
                extract_pipes_from_pdf_vision_async(pdf_path, page_num, model, timeout)
            )
    except Exception as e:
        logger.error(f"Failed to run vision extraction: {e}")
        return {
            "storm_pipes": [],
            "sanitary_pipes": [],
            "water_pipes": [],
            "error": str(e)
        }


async def extract_pipes_from_pdf_vision_multipage_async(
    pdf_path: str,
    model: str = "gpt-4o",
    timeout: int = 180
) -> Dict[str, Any]:
    """
    Extract pipes from ALL pages of a PDF (plan view + profile views).
    
    Sends all pages as images to the LLM in a single request.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    
    # Get page count
    import fitz
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    doc.close()
    
    logger.info(f"📄 Processing {page_count} pages with vision LLM...")
    
    # Convert all pages to images
    image_contents = []
    max_pages = min(page_count, 10)  # Process up to 10 pages
    logger.info(f"Converting {max_pages} pages to images...")
    
    for page_num in range(max_pages):
        image_base64 = await _pdf_page_to_base64(pdf_path, page_num)
        image_contents.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{image_base64}",
                "detail": "high"
            }
        })
        logger.info(f"  Page {page_num + 1}/{max_pages} converted")
    
    system_prompt = """You are an expert civil engineer analyzing utility construction plans. 
Your task is to identify ALL utility pipes and extract their complete information.

You will see multiple pages from the same drawing set. Each page may contain different information:
- Plan views (top-down)
- Profile views (side elevation)
- Details, notes, legends
- Tables with measurements

READ ALL PAGES BEFORE MAKING MEASUREMENTS OR DECISIONS.
Different pages may have better or more accurate information for the same pipe.

For each measurement or attribute:
1. Check ALL pages to see where the information is clearest
2. Use the most explicit/detailed source (e.g., a table or annotation is better than visual measurement)
3. Cross-reference between pages to ensure consistency

When extracting data:
- Lengths: Look for station labels, dimension annotations, or tables before measuring visually
- Elevations: Look for IE/INV/GL labels with numeric values
- Materials: Read from legends, labels, or notes
- Diameters: Read from text annotations
- Depths: Calculate from elevations when available, or read if annotated

Be thorough but accurate:
- Only report values you can clearly read or calculate
- If multiple pages show the same information, use the clearest one
- Use null if information is not visible on any page"""

    user_prompt = """Analyze ALL pages of this utility plan and extract complete pipe information.

For EACH pipe, provide:
- discipline: "storm", "sanitary", or "water"
- length_ft: length in feet (from plan view scale)
- material: pipe material
- dia_in: diameter in inches
- invert_in: invert elevation at START (from profile view)
- invert_out: invert elevation at END (from profile view)
- ground_elev: ground elevation (from profile view)
- notes: any other relevant info

Return JSON with this structure:
{
  "scale": {"ratio": "1in=40ft"},
  "storm_pipes": [{...}],
  "sanitary_pipes": [{...}],
  "water_pipes": [{...}]
}"""
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.info(f"🤖 Calling GPT-4o vision with {len(image_contents)} pages...")
            
            # Build message content with text + all images
            message_content = [{"type": "text", "text": user_prompt}] + image_contents
            
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message_content}
                    ],
                    "temperature": 0,
                    "max_tokens": 4000,
                    "response_format": {"type": "json_object"}
                }
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Log raw response for debugging
            logger.info(f"📝 Vision LLM raw response (first 500 chars): {content[:500]}")
            
            parsed = json.loads(content)
            
            # Log what we got
            storm_count = len(parsed.get("storm_pipes", []))
            sanitary_count = len(parsed.get("sanitary_pipes", []))
            water_count = len(parsed.get("water_pipes", []))
            
            logger.info(
                f"✅ Vision LLM (multipage) extracted: {storm_count} storm, "
                f"{sanitary_count} sanitary, {water_count} water pipes"
            )
            
            # If 0 pipes, log the full response for debugging
            if storm_count == 0 and sanitary_count == 0 and water_count == 0:
                logger.warning(f"⚠️ Vision LLM returned 0 pipes. Full response: {content[:1000]}")
            
            return parsed
    
    except Exception as e:
        logger.error(f"❌ Vision LLM multipage extraction failed: {e}", exc_info=True)
        return {
            "storm_pipes": [],
            "sanitary_pipes": [],
            "water_pipes": [],
            "error": str(e)
        }


def extract_pipes_from_pdf_vision_multipage(
    pdf_path: str,
    model: str = "gpt-4o",
    timeout: int = 180
) -> Dict[str, Any]:
    """Synchronous wrapper for multipage vision extraction."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    extract_pipes_from_pdf_vision_multipage_async(pdf_path, model, timeout)
                )
                return future.result(timeout=timeout + 10)
        else:
            return loop.run_until_complete(
                extract_pipes_from_pdf_vision_multipage_async(pdf_path, model, timeout)
            )
    except Exception as e:
        logger.error(f"Failed to run multipage vision extraction: {e}")
        return {
            "storm_pipes": [],
            "sanitary_pipes": [],
            "water_pipes": [],
            "error": str(e)
        }
