"""
Simple agent takeoff implementation using current detector functions.

This is a simplified version that works with the current detector API.
"""
import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

from backend.app.core.config import settings
from backend.app.schemas_estimai import EstimAIResult, Networks, StormNetwork, SanitaryNetwork, WaterNetwork

logger = logging.getLogger(__name__)


@dataclass
class ProposedReview:
    """Proposed review payload for takeoff analysis."""
    session_id: str
    sheet_ref: str
    payload: EstimAIResult
    warnings: list
    processing_time_sec: float
    ground_sources: Dict[str, str]


def run_takeoff_agent(session_id: str, file_ref: str) -> ProposedReview:
    """
    Run simplified takeoff agent workflow.
    
    Args:
        session_id: Unique session identifier
        file_ref: Path to PDF file
        
    Returns:
        ProposedReview with complete analysis
    """
    start_time = time.time()
    warnings = []
    
    try:
        logger.info(f"Starting takeoff agent for session {session_id}")
        
        # Check if Apryse is enabled
        if not settings.APR_USE_APRYSE:
            raise Exception("Apryse disabled (set APR_USE_APRYSE=1)")
        
        # Import detector functions
        from backend.app.services.detectors.storm import detect_storm_network
        from backend.app.services.detectors.sanitary import detect_sanitary_network
        from backend.app.services.detectors.water import detect_water_network
        from backend.app.services.ingest.pdfnet_runtime import open_doc, iter_pages
        from backend.app.services.ingest.extract import extract_text, extract_vectors
        from backend.app.services.ingest.scale import infer_scale_text, infer_scale_bar
        
        # Open PDF with Apryse
        doc = open_doc(file_ref)
        pages = list(iter_pages(doc))
        if not pages:
            raise Exception("No pages found in PDF")
        
        # Extract data from all pages
        all_vectors = []
        all_texts = []
        
        for page in pages:
            page_vectors = extract_vectors(page)
            page_texts = extract_text(page)
            all_vectors.extend(page_vectors)
            all_texts.extend(page_texts)
        
        # Detect scale
        scale_info = None
        scale_text = infer_scale_text(all_texts)
        if scale_text:
            scale_info = scale_text
        else:
            scale_bar = infer_scale_bar(all_vectors)
            if scale_bar:
                scale_info = scale_bar
            else:
                warnings.append("No scale information detected")
        
        # Prepare sheet data for ground elevation
        sheet_data = {"texts": all_texts, "vectors": all_vectors}
        
        # Detect networks
        logger.info("Detecting networks")
        
        storm_result = detect_storm_network(all_vectors, all_texts)
        sanitary_result = detect_sanitary_network(all_vectors, all_texts)
        water_result = detect_water_network(all_vectors, all_texts)
        
        # Collect ground sources and warnings
        ground_sources = {}
        all_qa_flags = []
        
        # Process storm network
        for pipe in storm_result.get("pipes", []):
            if "extra" in pipe and "_ground_source" in pipe["extra"]:
                ground_sources[f"storm_{pipe['id']}"] = pipe["extra"]["_ground_source"]
                if pipe["extra"]["_ground_source"] == "constant":
                    warnings.append(f"Storm pipe {pipe['id']} using constant ground elevation")
            all_qa_flags.extend(storm_result.get("qa_flags", []))
        
        # Process sanitary network
        for pipe in sanitary_result.get("pipes", []):
            if "extra" in pipe and "_ground_source" in pipe["extra"]:
                ground_sources[f"sanitary_{pipe['id']}"] = pipe["extra"]["_ground_source"]
                if pipe["extra"]["_ground_source"] == "constant":
                    warnings.append(f"Sanitary pipe {pipe['id']} using constant ground elevation")
            all_qa_flags.extend(sanitary_result.get("qa_flags", []))
        
        # Process water network
        for pipe in water_result.get("pipes", []):
            if "extra" in pipe and "_ground_source" in pipe["extra"]:
                ground_sources[f"water_{pipe['id']}"] = pipe["extra"]["_ground_source"]
                if pipe["extra"]["_ground_source"] == "constant":
                    warnings.append(f"Water pipe {pipe['id']} using constant ground elevation")
            all_qa_flags.extend(water_result.get("qa_flags", []))
        
        # Calculate sitework quantities
        from backend.app.services.detectors.sitework import (
            measure_curb_lf, measure_sidewalk_sf, measure_silt_fence_lf, count_inlet_protections
        )
        
        curb_lf = measure_curb_lf(all_vectors, scale_info)
        sidewalk_sf = measure_sidewalk_sf(all_vectors, scale_info)
        silt_fence_lf = measure_silt_fence_lf(all_vectors, scale_info)
        inlet_protection_ea = count_inlet_protections(all_vectors, all_texts)
        
        # Calculate earthwork
        from backend.app.services.detectors.earthwork_tables import parse_earthwork_summary
        from backend.app.services.detectors.earthwork_surface import estimate_earthwork_from_contours
        
        earthwork_tables = parse_earthwork_summary(all_texts)
        earthwork_surface = None
        
        if not earthwork_tables or (earthwork_tables.cut_cy is None and earthwork_tables.fill_cy is None):
            earthwork_surface = estimate_earthwork_from_contours(all_vectors, scale_info)
            if earthwork_surface:
                warnings.append("Using surface-based earthwork estimation (no tables found)")
        
        # Build EstimAIResult
        result = EstimAIResult(
            sheet_units="ft",
            scale=scale_info.scale_text if scale_info else None,
            networks=Networks(
                storm=StormNetwork(
                    pipes=storm_result.get("pipes", []),
                    structures=storm_result.get("nodes", [])
                ),
                sanitary=SanitaryNetwork(
                    pipes=sanitary_result.get("pipes", []),
                    manholes=sanitary_result.get("nodes", [])
                ),
                water=WaterNetwork(
                    pipes=water_result.get("pipes", []),
                    hydrants=water_result.get("nodes", []),
                    valves=[]
                )
            ),
            roadway={
                "curb_lf": curb_lf,
                "sidewalk_sf": sidewalk_sf
            },
            e_sc={
                "silt_fence_lf": silt_fence_lf,
                "inlet_protection_ea": inlet_protection_ea
            },
            earthwork={
                "cut_cy": earthwork_tables.cut_cy if earthwork_tables else None,
                "fill_cy": earthwork_tables.fill_cy if earthwork_tables else None,
                "source": "table" if earthwork_tables else "surface"
            },
            qa_flags=[
                {
                    "code": qa.code,
                    "message": qa.message,
                    "geom_id": qa.geom_id,
                    "sheet_ref": qa.sheet_ref
                } for qa in all_qa_flags
            ]
        )
        
        # Create proposed review
        processing_time = time.time() - start_time
        proposed_review = ProposedReview(
            session_id=session_id,
            sheet_ref="AUTO",
            payload=result,
            warnings=warnings,
            processing_time_sec=processing_time,
            ground_sources=ground_sources
        )
        
        logger.info(f"Takeoff agent completed for session {session_id} in {processing_time:.2f}s")
        return proposed_review
        
    except Exception as e:
        logger.error(f"Takeoff agent failed for session {session_id}: {e}")
        raise
