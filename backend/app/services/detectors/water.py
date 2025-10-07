"""
Water network detection and analysis using Apryse + LLM.

This module provides functions to detect water distribution network elements using:
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
logger.info(f"Water detector: MIN_CONFIDENCE threshold = {MIN_CONFIDENCE}")


class Pipe:
    """Simple pipe representation for water network."""
    def __init__(self, id: str, from_id: str, to_id: str, length_ft: float, 
                 dia_in: float, mat: str = "ductile_iron"):
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
            "id": f"hydrant_{i}",
            "kind": "hydrant",
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
            id=f"water_pipe_{i}",
            from_id=nodes[i]["id"],
            to_id=nodes[i + 1]["id"],
            length_ft=60.0 + (i * 30.0),
            dia_in=6.0 + (i * 1.0),
            mat="ductile_iron"
        )
        pipes.append(pipe)
    return pipes


def _find_nearby_text(polyline, text_runs: List, search_radius_ft: float = 40.0) -> List[str]:
    """
    Find text runs near a polyline using simple bbox expansion.
    
    Args:
        polyline: Polyline object with bbox in world feet
        text_runs: List of TextRun objects with coordinates in world feet
        search_radius_ft: Search radius in feet (default 40.0)
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
        if (expanded_bbox[0] <= run.x <= expanded_bbox[2] and
            expanded_bbox[1] <= run.y <= expanded_bbox[3]):
            if run.text and run.text.strip():
                nearby.append(run.text)
                if len(nearby) >= 3:
                    break
    
    return nearby


def detect_water_network(vectors: List[Dict], texts: List[Dict], pdf_path: str | None = None) -> Dict[str, Any]:
    """
    Detect water network using Apryse + LLM pipeline.
    
    Args:
        vectors: Vector geometry from Apryse (deprecated)
        texts: Text annotations from Apryse (deprecated)
        pdf_path: Path to PDF file for direct extraction
        
    Returns:
        Dictionary with nodes, pipes, and qa_flags
    """
    # Feature flag: Use demo data
    if USE_DEMO:
        logger.info("ESTIMAI_USE_DEMO=1: Using demo data for water network")
        nodes = _demo_detect_nodes(texts)
        pipes = _demo_trace_edges(nodes)
        return _attach_labels_and_qa(pipes, texts, "water")
    
    # Real pipeline
    logger.info("Detecting water network using Takeoff AI Agent")
    
    if not pdf_path:
        if USE_DEMO:
            logger.warning("No pdf_path provided, using demo data (ESTIMAI_USE_DEMO=1)")
            nodes = _demo_detect_nodes(texts)
            pipes = _demo_trace_edges(nodes)
            return _attach_labels_and_qa(pipes, texts, "water")
        else:
            logger.error("No pdf_path provided and ESTIMAI_USE_DEMO=0 - cannot proceed")
            return {"nodes": [], "pipes": [], "qa_flags": []}
    
    try:
        from backend.app.services.extract.apryse_vectors import VectorExtractor, ApryseUnavailable
        from backend.app.services.ai.pipe_classifier import PipeClassifier
        
        extractor = VectorExtractor(pdf_path)
        scale = extractor.load_scale(page_num=0)
        logger.info(f"Loaded scale: {scale.scale_text} ({scale.points_per_foot:.2f} pts/ft)")
        
        # Layer hints for water
        layer_hints = ["WATER", "WM", "WATER MAIN", "DOMESTIC WATER", "C-WAT"]
        polylines = extractor.extract_layer_lines(layer_hints, page_num=0)
        logger.info(f"Extracted {len(polylines)} candidate polylines from water layers")
        
        # Extract text using unified API and build spatial index
        text_runs = extractor.build_text_index(page_num=0)
        text_stats = extractor.get_text_stats(page_num=0)
        text_index = extractor.get_text_index(page_num=0)
        logger.info(f"📝 Text extraction: {text_stats['runs_count']} runs, {text_stats['chars_total']} chars")
        
        # Parse legend from full page text
        from backend.app.services.extract.legend_parser import parse_legend_from_text
        full_page_text = " ".join(run.text for run in text_runs)
        legend_tokens = parse_legend_from_text(full_page_text)
        logger.info(f"📋 Water legend_tokens: {legend_tokens[:5]}")
        
        # Build patches
        patches = []
        for polyline in polylines:
            # Use spatial index for efficient nearby text queries
            nearby_text = []
            if text_index:
                nearby_text = text_index.query_expand(
                    polyline.bbox,
                    expand_ft=40.0,
                    limit=20,
                    adaptive=True
                )
            
            # Add legend tokens for context
            enriched_nearby = nearby_text.copy() if nearby_text else []
            enriched_nearby.extend(legend_tokens[:5])
            
            patches.append({
                "polyline_id": polyline.id,
                "length_ft": polyline.length_ft,
                "bbox": polyline.bbox,
                "layer": polyline.layer,
                "color": polyline.stride,
                "nearby_text": enriched_nearby
            })
        
        # Classify
        classifier = PipeClassifier()
        detections = classifier.classify(patches)
        
        # Log raw LLM results
        logger.info(f"Water LLM: {len(patches)} patches → {len(detections)} detections")
        for i, det in enumerate(detections[:3]):
            logger.info(f"  [{i+1}] discipline={det.attrs.discipline}, conf={det.attrs.confidence:.2f}, reason={det.reason[:50]}")
        
        water_detections = []
        assignment_stats = {"llm": 0, "heuristic": 0, "rule_material": 0, "rule_legend": 0, "rule_layer": 0, "unknown": 0}
        
        for i, d in enumerate(detections):
            patch_data = patches[i] if i < len(patches) else {}
            assignment_method = None
            
            should_include, reason = should_include_in_network(d, "water", patch_data)
            
            # Try post-classification rules if no match
            if not should_include and (d.attrs.discipline is None or d.attrs.discipline != "water"):
                assigned_discipline, rule_method = assign_discipline_by_rules(
                    material=d.attrs.material,
                    legend_tokens=legend_tokens,
                    layer_hint=patch_data.get("layer")
                )
                if assigned_discipline == "water":
                    d.attrs.discipline = "water"
                    should_include = True
                    reason = f"Rule-based: {rule_method}"
                    assignment_method = rule_method
                    
                    # Boost confidence for rule-based assignments
                    if d.attrs.confidence is not None and d.attrs.confidence < 0.50:
                        original_conf = d.attrs.confidence
                        d.attrs.confidence = 0.50
                        logger.debug(f"Boosted confidence for {d.polyline_id}: {original_conf:.2f} → 0.50 (rule-based)")
                else:
                    assignment_method = rule_method if assigned_discipline else "unknown"
            else:
                assignment_method = "llm" if "LLM:" in reason else "heuristic"
            
            if not should_include:
                logger.debug(f"Excluding {d.polyline_id}: {reason}")
                if assignment_method:
                    assignment_stats[assignment_method] = assignment_stats.get(assignment_method, 0) + 1
                continue
            
            if d.attrs.confidence is not None and d.attrs.confidence < MIN_CONFIDENCE:
                logger.debug(f"Excluding {d.polyline_id}: confidence {d.attrs.confidence:.2f} < {MIN_CONFIDENCE}")
                continue
            
            logger.debug(f"Including {d.polyline_id} in water network: {reason}")
            if assignment_method:
                assignment_stats[assignment_method] = assignment_stats.get(assignment_method, 0) + 1
            water_detections.append(d)
        
        logger.info(
            f"AFTER filter (discipline='water', conf>={MIN_CONFIDENCE}): {len(water_detections)} pipes "
            f"(avg confidence: {sum(d.attrs.confidence for d in water_detections) / len(water_detections) if water_detections else 0:.2f})"
        )
        logger.info(
            f"📊 Water assignment breakdown: "
            f"llm={assignment_stats.get('llm', 0)}, heuristic={assignment_stats.get('heuristic', 0)}, "
            f"rule_material={assignment_stats.get('rule_material', 0)}, rule_legend={assignment_stats.get('rule_legend', 0)}, "
            f"rule_layer={assignment_stats.get('rule_layer', 0)}, unknown={assignment_stats.get('unknown', 0)}"
        )
        
        # Explicit warning if zero pipes after classification
        if len(water_detections) == 0:
            logger.warning(
                f"⚠️ 0 water pipes after classification (from {len(patches)} candidates, {len(detections)} detections). "
                f"Reasons: {assignment_stats.get('unknown', 0)} unclassifiable. "
                f"Check: (1) confidence threshold (current: {MIN_CONFIDENCE}), "
                f"(2) discipline assignment (material/legend/layer hints), "
                f"(3) text/layer extraction quality."
            )
            if not USE_DEMO:
                logger.info("ℹ️ ESTIMAI_USE_DEMO=0, no fallback data will be injected.")
        
        # Build network
        nodes = []
        pipe_dicts = []
        node_ids = set()
        
        for i, detection in enumerate(water_detections):
            polyline = next((p for p in polylines if p.id == detection.polyline_id), None)
            if not polyline:
                continue
            
            from_id = f"hydrant_{len(nodes)}"
            to_id = f"hydrant_{len(nodes) + 1}"
            
            if polyline.points and len(polyline.points) >= 2:
                from_pt = polyline.points[0]
                to_pt = polyline.points[-1]
                
                if from_id not in node_ids:
                    nodes.append({"id": from_id, "kind": "hydrant", "x": from_pt[0], "y": from_pt[1], "attrs": {}})
                    node_ids.add(from_id)
                
                if to_id not in node_ids:
                    nodes.append({"id": to_id, "kind": "hydrant", "x": to_pt[0], "y": to_pt[1], "attrs": {}})
                    node_ids.add(to_id)
            
            pipe_dict = {
                "id": f"water_pipe_{i}",
                "from_id": from_id,
                "to_id": to_id,
                "length_ft": polyline.length_ft,
                "dia_in": detection.attrs.dia_in or 6.0,
                "mat": detection.attrs.material or "ductile_iron",
                "slope": None,
                "avg_depth_ft": None,
                "extra": {
                    "confidence": detection.attrs.confidence,
                    "classification_reason": detection.reason,
                    "layer": polyline.layer,
                    "scale_used": scale.scale_text
                }
            }
            
            pipe_dicts.append(pipe_dict)
        
        # Step 6.5: Extract elevations and calculate depths
        logger.info(f"Extracting elevations for {len(pipe_dicts)} water pipes...")
        
        text_runs = extractor.get_text_runs_all(page_num=0)
        logger.info(f"  Retrieved {len(text_runs)} text runs for elevation extraction")
        
        elev_stats = {"both": 0, "one": 0, "none": 0, "depth_calculated": 0}
        
        for i, pipe_dict in enumerate(pipe_dicts):
            detection = water_detections[i] if i < len(water_detections) else None
            polyline = None
            if detection:
                polyline = next((p for p in polylines if p.id == detection.polyline_id), None)
            
            if not polyline or not polyline.points or len(polyline.points) < 2:
                logger.debug(f"Skipping elevation for {pipe_dict['id']}: no geometry")
                elev_stats["none"] += 1
                continue
            
            from backend.app.services.ingest.elevation_extractor import (
                extract_pipe_elevations,
                create_s_profile_from_inverts,
                estimate_ground_elevation
            )
            
            poly_dict = {
                "id": polyline.id,
                "vertices": polyline.points,
                "bbox": polyline.bbox
            }
            
            invert_in, invert_out = extract_pipe_elevations(poly_dict, text_runs, search_radius_ft=10.0)
            
            if invert_in and invert_out:
                elev_stats["both"] += 1
            elif invert_in or invert_out:
                elev_stats["one"] += 1
            else:
                elev_stats["none"] += 1
            
            s_profile = create_s_profile_from_inverts(invert_in, invert_out, pipe_dict["length_ft"])
            ground_elev = estimate_ground_elevation(list(polyline.bbox), surface_sampler=None, default_elevation=100.0)
            
            if s_profile:
                def ground_at_s(station: float) -> float:
                    return ground_elev
                
                samples = sample_depth_along_run(s_profile, ground_at_s, pipe_dict["mat"], pipe_dict["dia_in"], n_samples=20)
                summary = summarize_depth(samples, "water")
                
                pipe_dict["avg_depth_ft"] = summary.avg_depth_ft
                pipe_dict["extra"]["min_depth_ft"] = summary.min_depth_ft
                pipe_dict["extra"]["max_depth_ft"] = summary.max_depth_ft
                pipe_dict["extra"]["p95_depth_ft"] = summary.p95_depth_ft
                pipe_dict["extra"]["trench_volume_cy"] = summary.trench_volume_cy
                pipe_dict["extra"]["invert_in_ft"] = invert_in
                pipe_dict["extra"]["invert_out_ft"] = invert_out
                pipe_dict["extra"]["ground_elev_ft"] = ground_elev
                
                elev_stats["depth_calculated"] += 1
                
                ie_in_str = f"{invert_in:.1f}" if invert_in is not None else "N/A"
                ie_out_str = f"{invert_out:.1f}" if invert_out is not None else "N/A"
                logger.debug(
                    f"{pipe_dict['id']}: depth={summary.avg_depth_ft:.1f}ft "
                    f"(IE_IN={ie_in_str}, IE_OUT={ie_out_str}, GL={ground_elev:.1f})"
                )
            else:
                pipe_dict["avg_depth_ft"] = None
                pipe_dict["extra"]["depth_unavailable"] = True
                pipe_dict["extra"]["depth_unavailable_reason"] = "Missing invert elevations"
                logger.debug(f"{pipe_dict['id']}: Cannot calculate depth (no inverts found)")
        
        logger.info(f"📏 Elevation extraction complete:")
        logger.info(f"  Both inverts: {elev_stats['both']}, One invert: {elev_stats['one']}, None: {elev_stats['none']}")
        logger.info(f"  Depths calculated: {elev_stats['depth_calculated']} / {len(pipe_dicts)} pipes")
        
        extractor.close()
        
        # QA flags
        qa_flags = []
        for pipe_dict in pipe_dicts:
            qa_flags.extend(validate_pipe_qa(pipe_dict, "water"))
        
        logger.info(f"Water network: {len(nodes)} nodes, {len(pipe_dicts)} pipes, {len(qa_flags)} QA flags")
        
        return {
            "nodes": nodes,
            "pipes": pipe_dicts,
            "qa_flags": qa_flags,
            "all_detections": detections,  # Include ALL detections (for unknown tracking)
            "classified_ids": {p["id"] for p in pipe_dicts}  # IDs that made it into this network
        }
    
    except Exception as e:
        if USE_DEMO:
            logger.error(f"Real water detection failed: {e}", exc_info=True)
            logger.warning("Falling back to demo data (ESTIMAI_USE_DEMO=1)")
            nodes = _demo_detect_nodes(texts)
            pipes = _demo_trace_edges(nodes)
            return _attach_labels_and_qa(pipes, texts, "water")
        else:
            logger.error(f"❌ Real water detection failed and ESTIMAI_USE_DEMO=0: {e}", exc_info=True)
            logger.error("No vector candidates found - check PDF has vector geometry")
            return {"nodes": [], "pipes": [], "qa_flags": []}


def _attach_labels_and_qa(pipes: List[Pipe], texts: List[Dict], discipline: str) -> Dict[str, Any]:
    """DEMO: Attach labels and QA flags to demo pipes."""
    init_depth_config()
    
    pipe_dicts = []
    qa_flags = []
    
    for pipe in pipes:
        s_profile = [(0.0, 100.0), (1.0, 98.0)]
        def ground_at_s(station: float) -> float:
            return 102.0 - (station * 1.0)
        
        samples = sample_depth_along_run(s_profile, ground_at_s, pipe.mat, pipe.dia_in, n_samples=20)
        summary = summarize_depth(samples, discipline)
        
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
    
    nodes = [{"id": f"hydrant_{i}", "kind": "hydrant", "x": 0.0, "y": 0.0, "attrs": {}} for i in range(len(pipes) + 1)]
    
    return {
        "nodes": nodes,
        "pipes": pipe_dicts,
        "qa_flags": qa_flags
    }
