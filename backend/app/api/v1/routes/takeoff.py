from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.app.core.config import settings
from backend.app.schemas_estimai import EstimAIResult, StormNetwork, SanitaryNetwork, WaterNetwork, Roadway, ESC, Earthwork, QAFlag
from typing import Dict, Any, List
import tempfile
import os
from pathlib import Path

router = APIRouter(prefix="/v1/takeoff", tags=["takeoff"])

@router.post("/pdf", response_model=EstimAIResult)
async def takeoff_pdf(file: UploadFile = File(...)):
    """
    Complete takeoff pipeline using Apryse PDFNet.
    
    Flow:
    1. Guard: Check APR_USE_APRYSE
    2. Open PDF with Apryse
    3. Extract scale information
    4. Extract vectors, text, and OCGs
    5. Build legend → symbol map
    6. Detect networks (storm/sanitary/water)
    7. Calculate sitework quantities
    8. Calculate earthwork (tables + optional surface)
    9. Apply depth analysis (via discipline detectors)
    10. Apply QA rules
    11. Return complete EstimAIResult
    """
    # Guard: Check if Apryse is enabled
    if not settings.APR_USE_APRYSE:
        raise HTTPException(
            status_code=422, 
            detail="Apryse disabled (set APR_USE_APRYSE=1)"
        )
    
    try:
        # Step 1: Open PDF with Apryse
        from backend.app.services.ingest.pdfnet_runtime import open_doc, iter_pages
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Open document with Apryse
            doc = open_doc(tmp_file_path)
            
            # Step 2: Extract scale information
            from backend.app.services.ingest.scale import infer_scale_text, infer_scale_bar, ScaleInfo
            from backend.app.services.ingest.extract import extract_text, extract_vectors
            
            # Process first page for scale detection
            pages = list(iter_pages(doc))
            if not pages:
                raise HTTPException(status_code=400, detail="No pages found in PDF")
            
            first_page = pages[0]
            
            # Extract text and vectors for scale detection
            texts = extract_text(first_page)
            vectors = extract_vectors(first_page)
            
            # Detect scale
            scale_info = None
            scale_text = infer_scale_text(texts)
            if scale_text:
                scale_info = scale_text
            else:
                scale_bar = infer_scale_bar(vectors)
                if scale_bar:
                    scale_info = scale_bar
            
            # Step 3: Extract vectors, text, and OCGs from all pages
            all_vectors = []
            all_texts = []
            
            for page in pages:
                page_vectors = extract_vectors(page)
                page_texts = extract_text(page)
                all_vectors.extend(page_vectors)
                all_texts.extend(page_texts)
            
            # Step 4: Build legend → symbol map
            from backend.app.services.detectors.legend import find_legend_regions, sample_symbol_snippets
            from backend.app.services.detectors.symbol_map import build_symbol_map_via_llm
            
            # Find legend regions
            legend_regions = find_legend_regions(all_texts)
            
            # Sample symbol snippets
            symbol_snippets = sample_symbol_snippets(all_vectors, all_texts, legend_regions)
            
            # Build symbol map via LLM
            notes_text = " ".join([t.get("text", "") for t in all_texts])
            symbol_map = build_symbol_map_via_llm(symbol_snippets, notes_text)
            
            # Step 5: Build networks using discipline detectors
            from backend.app.services.detectors.storm import detect_storm_network
            from backend.app.services.detectors.sanitary import detect_sanitary_network
            from backend.app.services.detectors.water import detect_water_network
            
            # Detect networks
            storm_result = detect_storm_network(all_vectors, all_texts)
            sanitary_result = detect_sanitary_network(all_vectors, all_texts)
            water_result = detect_water_network(all_vectors, all_texts)
            
            # Step 6: Calculate sitework quantities
            from backend.app.services.detectors.sitework import (
                measure_curb_lf, measure_sidewalk_sf, measure_silt_fence_lf, count_inlet_protections
            )
            
            # Calculate sitework
            curb_lf = measure_curb_lf(all_vectors, scale_info)
            sidewalk_sf = measure_sidewalk_sf(all_vectors, scale_info)
            silt_fence_lf = measure_silt_fence_lf(all_vectors, scale_info)
            inlet_protection_ea = count_inlet_protections(all_vectors, all_texts)
            
            # Step 7: Calculate earthwork
            from backend.app.services.detectors.earthwork_tables import parse_earthwork_summary
            from backend.app.services.detectors.earthwork_surface import estimate_earthwork_from_contours
            
            # Try to parse earthwork tables first
            earthwork_tables = parse_earthwork_summary(all_texts)
            
            # Optional: Try surface-based estimation if tables not available
            earthwork_surface = None
            if not earthwork_tables or (earthwork_tables.cut_cy is None and earthwork_tables.fill_cy is None):
                earthwork_surface = estimate_earthwork_from_contours(all_vectors, scale_info)
            
            # Step 8: Collect QA flags from all networks
            all_qa_flags = []
            all_qa_flags.extend(storm_result.get("qa_flags", []))
            all_qa_flags.extend(sanitary_result.get("qa_flags", []))
            all_qa_flags.extend(water_result.get("qa_flags", []))
            
            # Step 9: Build EstimAIResult
            result = EstimAIResult(
                sheet_units="ft",
                scale=scale_info.scale_text if scale_info else None,
                networks={
                    "storm": StormNetwork(
                        pipes=storm_result.get("pipes", []),
                        structures=storm_result.get("nodes", [])
                    ),
                    "sanitary": SanitaryNetwork(
                        pipes=sanitary_result.get("pipes", []),
                        manholes=sanitary_result.get("nodes", [])
                    ),
                    "water": WaterNetwork(
                        pipes=water_result.get("pipes", []),
                        hydrants=water_result.get("nodes", []),
                        valves=[]
                    )
                },
                roadway=Roadway(
                    curb_lf=curb_lf,
                    sidewalk_sf=sidewalk_sf
                ),
                e_sc=ESC(
                    silt_fence_lf=silt_fence_lf,
                    inlet_protection_ea=inlet_protection_ea
                ),
                earthwork=Earthwork(
                    cut_cy=earthwork_tables.cut_cy if earthwork_tables else None,
                    fill_cy=earthwork_tables.fill_cy if earthwork_tables else None,
                    undercut_cy=earthwork_tables.undercut_cy if earthwork_tables else None,
                    source="table" if earthwork_tables else "calc"
                ),
                qa_flags=[
                    QAFlag(
                        code=flag.get("code", ""),
                        message=flag.get("message", ""),
                        geom_id=flag.get("geom_id"),
                        sheet_ref=flag.get("sheet_ref")
                    )
                    for flag in all_qa_flags
                ]
            )
            
            return result
            
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
                
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Takeoff processing failed: {str(e)}"
        )
