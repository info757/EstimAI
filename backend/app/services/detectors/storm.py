"""
Storm network detection and analysis using Apryse + LLM.

This module provides functions to detect storm network elements using:
1. Apryse PDFNet for vector geometry extraction
2. LLM-based classification for pipe attribution
3. Real-world measurements from scale conversion
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from backend.app.services.detectors.depth import init_depth_config, sample_depth_along_run, summarize_depth
from backend.app.services.detectors.qa_rules import validate_pipe_qa
from backend.app.services.ai.pipe_rules import should_include_in_network, assign_discipline_by_rules

logger = logging.getLogger(__name__)

# Feature flag: Use demo data or real pipeline
USE_DEMO = os.getenv("ESTIMAI_USE_DEMO", "0") == "1"

# Configurable confidence threshold for pipe classification
MIN_CONFIDENCE = float(os.getenv("ESTIMAI_PIPE_MIN_CONF", "0.35"))
logger.info(f"Storm detector: MIN_CONFIDENCE threshold = {MIN_CONFIDENCE}")


class Pipe:
    """Simple pipe representation for storm network."""
    def __init__(self, id: str, from_id: str, to_id: str, length_ft: float, 
                 dia_in: float, mat: str = "pvc"):
        self.id = id
        self.from_id = from_id
        self.to_id = to_id
        self.length_ft = length_ft
        self.dia_in = dia_in
        self.mat = mat
        self.avg_depth_ft: Optional[float] = None
        self.extra: Dict[str, Any] = {}


def _demo_detect_nodes(texts: List[Dict]) -> List[Dict]:
    """DEMO: Generate placeholder nodes."""
    nodes = []
    for i, text in enumerate(texts[:3]):
        nodes.append({
            "id": f"inlet_{i}",
            "kind": "inlet",
            "x": text.get("x", 0.0),
            "y": text.get("y", 0.0),
            "attrs": {"label": text.get("text", "")}
        })
    return nodes


def _demo_trace_edges(nodes: List[Dict]) -> List[Pipe]:
    """DEMO: Generate placeholder pipes."""
    pipes = []
    for i in range(len(nodes) - 1):
        pipe = Pipe(
            id=f"storm_pipe_{i}",
            from_id=nodes[i]["id"],
            to_id=nodes[i + 1]["id"],
            length_ft=50.0 + (i * 25.0),
            dia_in=12.0 + (i * 2.0),
            mat="pvc"
        )
        pipes.append(pipe)
    return pipes


def _find_nearby_text(polyline, text_runs: List, search_radius_ft: float = 40.0) -> List[str]:
    """
    Find text runs near a polyline using simple bbox expansion.
    
    Args:
        polyline: Polyline object with bbox in world feet
        text_runs: List of TextRun objects with coordinates in world feet
        search_radius_ft: Search radius in feet (default 40.0 for wider search)
        
    Returns:
        List of text strings near the polyline (up to first 3)
        
    Notes:
        - Uses simple bbox expansion (±40 ft) without spatial index
        - Returns first 3 matches to avoid overwhelming the LLM
        - Larger radius to compensate for potential coordinate issues
    """
    bbox = polyline.bbox
    expanded_bbox = (
        bbox[0] - search_radius_ft,
        bbox[1] - search_radius_ft,
        bbox[2] + search_radius_ft,
        bbox[3] + search_radius_ft
    )
    
    nearby = []
    for run in text_runs:
        # Check if text center is within expanded bbox
        if (expanded_bbox[0] <= run.x <= expanded_bbox[2] and
            expanded_bbox[1] <= run.y <= expanded_bbox[3]):
            if run.text and run.text.strip():
                nearby.append(run.text)
                # Limit to first 3 to avoid overwhelming
                if len(nearby) >= 3:
                    break
    
    return nearby


def detect_storm_network(vectors: List[Dict], texts: List[Dict], pdf_path: str | None = None) -> Dict[str, Any]:
    """
    Detect storm network using Apryse + LLM pipeline.
    
    Args:
        vectors: Vector geometry from Apryse (deprecated - use pdf_path instead)
        texts: Text annotations from Apryse (deprecated - use pdf_path instead)
        pdf_path: Path to PDF file for direct extraction
        
    Returns:
        Dictionary with nodes, pipes, and qa_flags
        
    Process:
    1. Extract polylines from PDF using VectorExtractor
    2. Filter by layer hints (STORM, SD, etc.)
    3. Find nearby text annotations for each polyline
    4. Classify using PipeClassifier
    5. Build network topology
    6. Calculate depth and QA flags
    """
    # Feature flag: Use demo data
    if USE_DEMO:
        logger.info("ESTIMAI_USE_DEMO=1: Using demo data for storm network")
        nodes = _demo_detect_nodes(texts)
        pipes = _demo_trace_edges(nodes)
        return _attach_labels_and_qa(pipes, texts, "storm")
    
    # Real pipeline
    logger.info("Detecting storm network using Apryse + LLM pipeline")
    
    if not pdf_path:
        if USE_DEMO:
            logger.warning("No pdf_path provided, using demo data (ESTIMAI_USE_DEMO=1)")
            nodes = _demo_detect_nodes(texts)
            pipes = _demo_trace_edges(nodes)
            return _attach_labels_and_qa(pipes, texts, "storm")
        else:
            logger.error("No pdf_path provided and ESTIMAI_USE_DEMO=0 - cannot proceed")
            return {"nodes": [], "pipes": [], "qa_flags": []}
    
    try:
        from backend.app.services.extract.apryse_vectors import VectorExtractor, ApryseUnavailable
        from backend.app.services.ai.pipe_classifier import PipeClassifier
        
        # Step 1: Initialize extractor
        extractor = VectorExtractor(pdf_path)
        scale = extractor.load_scale(page_num=0)
        logger.info(f"Loaded scale: {scale.scale_text} ({scale.points_per_foot:.2f} pts/ft)")
        
        # Step 2: Extract candidate polylines
        layer_hints = ["STORM", "SD", "STORM SEWER", "STORM DRAIN", "C-STRM"]
        polylines = extractor.extract_layer_lines(layer_hints, page_num=0)
        logger.info(f"Extracted {len(polylines)} candidate polylines from storm layers")
        
        # Step 3: Extract text using unified API and build spatial index
        text_runs = extractor.build_text_index(page_num=0)
        text_stats = extractor.get_text_stats(page_num=0)
        text_index = extractor.get_text_index(page_num=0)
        logger.info(f"📝 Text extraction: {text_stats['runs_count']} runs, {text_stats['chars_total']} chars")
        
        # Parse legend from full page text
        from backend.app.services.extract.legend_parser import parse_legend_from_text
        full_page_text = " ".join(run.text for run in text_runs)
        legend_tokens = parse_legend_from_text(full_page_text)
        logger.info(f"📋 Parsed legend_tokens: {legend_tokens[:5]}")
        
        # Debug: Log first few text runs
        for i, run in enumerate(text_runs[:3]):
            logger.info(f"  Text[{i}]: '{run.text[:30]}' at ({run.x:.1f}, {run.y:.1f}) ft")
        
        # Step 4: Build patches for classifier
        patches = []
        for polyline in polylines:
            # Debug: Log polyline bbox
            logger.info(f"  Polyline {polyline.id}: bbox={polyline.bbox}, layer='{polyline.layer}'")
            
            # Find nearby text using spatial index (adaptive expansion)
            nearby_text = []
            if text_index:
                nearby_text = text_index.query_expand(
                    polyline.bbox,
                    expand_ft=40.0,
                    limit=20,
                    adaptive=True
                )
            logger.info(f"    Found {len(nearby_text)} nearby texts: {nearby_text[:3] if nearby_text else '[]'}")
            
            # Add legend tokens to nearby_text to provide context
            # Even if spatial matching fails, legend gives LLM/heuristics material hints
            enriched_nearby = nearby_text.copy() if nearby_text else []
            enriched_nearby.extend(legend_tokens[:5])  # Add top 5 legend tokens
            
            patch = {
                "polyline_id": polyline.id,
                "length_ft": polyline.length_ft,
                "bbox": polyline.bbox,
                "layer": polyline.layer,
                "color": polyline.stride,
                "nearby_text": enriched_nearby  # Now includes indexed nearby text + legend
            }
            patches.append(patch)
        
        logger.info(f"Built {len(patches)} patches for classification")
        
        # Step 5: Classify polylines as storm pipes
        classifier = PipeClassifier()
        detections = classifier.classify(patches)
        
        # Log what LLM actually returned (before filtering)
        logger.info(f"LLM Classification Results (BEFORE filtering):")
        logger.info(f"  Total patches sent: {len(patches)}")
        logger.info(f"  Detections returned: {len(detections)}")
        
        # Show sample of first 5 detections
        for i, det in enumerate(detections[:5]):
            logger.info(
                f"  [{i+1}] {det.polyline_id}: "
                f"discipline={det.attrs.discipline}, "
                f"material={det.attrs.material}, "
                f"dia_in={det.attrs.dia_in}, "
                f"confidence={det.attrs.confidence:.2f}, "
                f"reason={det.reason[:60]}"
            )
        
        if len(detections) > 5:
            logger.info(f"  ... and {len(detections) - 5} more")
        
        # Filter for storm discipline with configurable confidence threshold
        # Use heuristic fallback when LLM is uncertain, then post-classification rules
        storm_detections = []
        assignment_stats = {"llm": 0, "heuristic": 0, "rule_material": 0, "rule_legend": 0, "rule_layer": 0, "unknown": 0}
        
        for i, d in enumerate(detections):
            # Get original patch data for heuristics
            patch_data = patches[i] if i < len(patches) else {}
            
            # Track how this was classified
            assignment_method = None
            
            # Check discipline match (with heuristic fallback)
            should_include, reason = should_include_in_network(d, "storm", patch_data)
            
            # If still no match, try post-classification rules
            if not should_include and (d.attrs.discipline is None or d.attrs.discipline != "storm"):
                # Apply rule-based assignment
                assigned_discipline, rule_method = assign_discipline_by_rules(
                    material=d.attrs.material,
                    legend_tokens=legend_tokens,
                    layer_hint=patch_data.get("layer")
                )
                
                # Update detection if rule assigned storm
                if assigned_discipline == "storm":
                    d.attrs.discipline = "storm"
                    should_include = True
                    reason = f"Rule-based: {rule_method}"
                    assignment_method = rule_method
                    
                    # Boost confidence for rule-based assignments
                    if d.attrs.confidence is not None and d.attrs.confidence < 0.50:
                        original_conf = d.attrs.confidence
                        d.attrs.confidence = 0.50  # Boost to pass threshold
                        logger.debug(f"Boosted confidence for {d.polyline_id}: {original_conf:.2f} → 0.50 (rule-based)")
                else:
                    assignment_method = rule_method if assigned_discipline else "unknown"
            else:
                # Determine if it was LLM or heuristic
                if "LLM:" in reason:
                    assignment_method = "llm"
                elif "Heuristic" in reason:
                    assignment_method = "heuristic"
            
            if not should_include:
                logger.debug(f"Excluding {d.polyline_id}: {reason} (conf={d.attrs.confidence})")
                if assignment_method:
                    assignment_stats[assignment_method] = assignment_stats.get(assignment_method, 0) + 1
                continue
            
            # Check confidence threshold (after potential boosting)
            if d.attrs.confidence is not None and d.attrs.confidence < MIN_CONFIDENCE:
                logger.debug(f"Excluding {d.polyline_id}: confidence {d.attrs.confidence:.2f} < {MIN_CONFIDENCE}")
                continue
            
            logger.debug(f"Including {d.polyline_id} in storm network: {reason}")
            if assignment_method:
                assignment_stats[assignment_method] = assignment_stats.get(assignment_method, 0) + 1
            storm_detections.append(d)
        
        avg_conf = (sum(d.attrs.confidence for d in storm_detections) / len(storm_detections)) if storm_detections else 0.0
        logger.info(
            f"AFTER filtering (discipline='storm', confidence>={MIN_CONFIDENCE}): "
            f"{len(storm_detections)} storm pipes from {len(patches)} candidates "
            f"(avg confidence: {avg_conf:.2f})"
        )
        
        # Log assignment statistics
        logger.info(
            f"📊 Storm assignment breakdown: "
            f"llm={assignment_stats.get('llm', 0)}, "
            f"heuristic={assignment_stats.get('heuristic', 0)}, "
            f"rule_material={assignment_stats.get('rule_material', 0)}, "
            f"rule_legend={assignment_stats.get('rule_legend', 0)}, "
            f"rule_layer={assignment_stats.get('rule_layer', 0)}, "
            f"unknown={assignment_stats.get('unknown', 0)}"
        )
        
        # Explicit warning if zero pipes after classification
        if len(storm_detections) == 0:
            logger.warning(
                f"⚠️ 0 storm pipes after classification (from {len(patches)} candidates, {len(detections)} detections). "
                f"Reasons: {assignment_stats.get('unknown', 0)} unclassifiable. "
                f"Check: (1) confidence threshold (current: {MIN_CONFIDENCE}), "
                f"(2) discipline assignment (material/legend/layer hints), "
                f"(3) text/layer extraction quality."
            )
            if not USE_DEMO:
                logger.info("ℹ️ ESTIMAI_USE_DEMO=0, no fallback data will be injected.")
        
        # Step 6: Build network model
        nodes = []
        pipe_dicts = []
        
        # Create nodes from pipe endpoints
        node_ids = set()
        for i, detection in enumerate(storm_detections):
            # Find original polyline and patch
            polyline = next((p for p in polylines if p.id == detection.polyline_id), None)
            patch = next((p for p in patches if p["polyline_id"] == detection.polyline_id), None)
            
            if not polyline:
                continue
            
            # Get nearby text from patch for audit
            nearby_text = patch.get("nearby_text", []) if patch else []
            
            # Create from/to nodes from polyline endpoints
            from_id = f"inlet_{len(nodes)}"
            to_id = f"inlet_{len(nodes) + 1}"
            
            if polyline.points and len(polyline.points) >= 2:
                from_pt = polyline.points[0]
                to_pt = polyline.points[-1]
                
                if from_id not in node_ids:
                    nodes.append({
                        "id": from_id,
                        "kind": "inlet",
                        "x": from_pt[0],
                        "y": from_pt[1],
                        "attrs": {}
                    })
                    node_ids.add(from_id)
                
                if to_id not in node_ids:
                    nodes.append({
                        "id": to_id,
                        "kind": "inlet",
                        "x": to_pt[0],
                        "y": to_pt[1],
                        "attrs": {}
                    })
                    node_ids.add(to_id)
            
            # Create pipe dict with comprehensive audit trail
            pipe_dict = {
                "id": f"storm_pipe_{i}",
                "from_id": from_id,
                "to_id": to_id,
                "length_ft": polyline.length_ft,
                "dia_in": detection.attrs.dia_in or 12.0,  # Default if not detected
                "mat": detection.attrs.material or "pvc",
                "slope": None,
                "avg_depth_ft": None,
                "extra": {
                    "confidence": detection.attrs.confidence,
                    "classification_reason": detection.reason,
                    "layer": polyline.layer,
                    "scale_used": scale.scale_text,
                    "nearby_text_audit": nearby_text[:5],  # Keep first 5 text snippets for audit
                    "bbox_ft": polyline.bbox,  # Bounding box in world feet
                    "stroke_width": polyline.stride  # Original stroke info
                }
            }
            
            pipe_dicts.append(pipe_dict)
        
        extractor.close()
        
        # Step 7: Calculate QA flags
        qa_flags = []
        for pipe_dict in pipe_dicts:
            pipe_qa_flags = validate_pipe_qa(pipe_dict, "storm")
            qa_flags.extend(pipe_qa_flags)
        
        logger.info(f"Storm network: {len(nodes)} nodes, {len(pipe_dicts)} pipes, {len(qa_flags)} QA flags")
        
        return {
            "nodes": nodes,
            "pipes": pipe_dicts,
            "qa_flags": qa_flags
        }
    
    except ApryseUnavailable as e:
        if USE_DEMO:
            logger.warning(f"Apryse unavailable, using demo data (ESTIMAI_USE_DEMO=1): {e}")
            nodes = _demo_detect_nodes(texts)
            pipes = _demo_trace_edges(nodes)
            return _attach_labels_and_qa(pipes, texts, "storm")
        else:
            logger.error(f"❌ Apryse unavailable and ESTIMAI_USE_DEMO=0: {e}")
            logger.error("Set APR_USE_APRYSE=1 or ESTIMAI_USE_DEMO=1 to proceed")
            return {"nodes": [], "pipes": [], "qa_flags": []}
    
    except Exception as e:
        if USE_DEMO:
            logger.error(f"Real storm detection failed: {e}", exc_info=True)
            logger.warning("Falling back to demo data (ESTIMAI_USE_DEMO=1)")
            nodes = _demo_detect_nodes(texts)
            pipes = _demo_trace_edges(nodes)
            return _attach_labels_and_qa(pipes, texts, "storm")
        else:
            logger.error(f"❌ Real storm detection failed and ESTIMAI_USE_DEMO=0: {e}", exc_info=True)
            logger.error("No vector candidates found - check PDF has vector geometry")
            return {"nodes": [], "pipes": [], "qa_flags": []}


def _attach_labels_and_qa(pipes: List[Pipe], texts: List[Dict], discipline: str) -> Dict[str, Any]:
    """DEMO: Attach labels and QA flags to demo pipes."""
    init_depth_config()
    
    pipe_dicts = []
    qa_flags = []
    
    for pipe in pipes:
        # Create simple s-profile
        s_profile = [(0.0, 100.0), (1.0, 98.0)]
        
        # Simple ground profile
        def ground_at_s(station: float) -> float:
            return 102.0 - (station * 1.0)
        
        # Sample depth
        samples = sample_depth_along_run(
            s_profile, ground_at_s, pipe.mat, pipe.dia_in, n_samples=20
        )
        
        # Calculate depth summary
        summary = summarize_depth(samples, discipline)
        
        # Attach depth
        pipe.avg_depth_ft = summary.avg_depth_ft
        pipe.extra = {
            "min_depth_ft": summary.min_depth_ft,
            "max_depth_ft": summary.max_depth_ft,
            "p95_depth_ft": summary.p95_depth_ft,
            "buckets_lf": summary.buckets_lf,
            "trench_volume_cy": summary.trench_volume_cy,
            "cover_ok": summary.cover_ok,
            "deep_excavation": summary.deep_excavation
        }
        
        pipe_dict = {
            "id": pipe.id,
            "from_id": pipe.from_id,
            "to_id": pipe.to_id,
            "length_ft": pipe.length_ft,
            "dia_in": pipe.dia_in,
            "mat": pipe.mat,
            "slope": None,
            "avg_depth_ft": pipe.avg_depth_ft,
            "extra": pipe.extra
        }
        
        pipe_qa_flags = validate_pipe_qa(pipe_dict, discipline)
        qa_flags.extend(pipe_qa_flags)
        pipe_dicts.append(pipe_dict)
    
    nodes = [{"id": f"inlet_{i}", "kind": "inlet", "x": 0.0, "y": 0.0, "attrs": {}} for i in range(len(pipes) + 1)]
    
    return {
        "nodes": nodes,
        "pipes": pipe_dicts,
        "qa_flags": qa_flags
    }
