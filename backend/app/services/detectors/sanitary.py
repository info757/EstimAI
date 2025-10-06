"""
Sanitary network detection and analysis.

This module provides functions to detect sanitary network elements and
calculate depth-based trench analysis with robust ground elevation sampling.
"""
from typing import List, Dict, Any, Optional, Tuple, Callable
from backend.app.services.detectors.depth import (
    sample_depth_along_run, summarize_depth, init_depth_config
)
from backend.app.services.detectors.qa_rules import validate_pipe_qa
from backend.app.services.earthwork_surface import (
    load_surface_from_pdf, make_ground_sampler, sample_ground_along_centerline
)
from backend.app.services.profiles.parser import parse_profile_gl
from shapely.geometry import LineString


class Pipe:
    """Simple pipe representation for sanitary network."""
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


def detect_nodes(vectors: List[Dict], texts: List[Dict]) -> List[Dict]:
    """Detect sanitary network nodes (manholes, cleanouts, etc.)."""
    # Placeholder implementation
    nodes = []
    for i, text in enumerate(texts[:3]):  # Simple example
        nodes.append({
            "id": f"manhole_{i}",
            "kind": "manhole",
            "x": text.get("x", 0.0),
            "y": text.get("y", 0.0),
            "attrs": {"label": text.get("text", "")}
        })
    return nodes


def trace_edges(vectors: List[Dict], nodes: List[Dict]) -> List[Pipe]:
    """Trace sanitary network edges (pipes) between nodes."""
    pipes = []
    
    # Simple example: create pipes between detected nodes
    for i in range(len(nodes) - 1):
        pipe = Pipe(
            id=f"sanitary_pipe_{i}",
            from_id=nodes[i]["id"],
            to_id=nodes[i + 1]["id"],
            length_ft=40.0 + (i * 20.0),  # Varying lengths
            dia_in=8.0 + (i * 1.0),  # Varying diameters
            mat="pvc"
        )
        pipes.append(pipe)
    
    return pipes


def attach_labels(pipes: List[Pipe], texts: List[Dict], 
                 file_ref: str = None, sheet_data: Dict[str, Any] = None) -> List[Pipe]:
    """Attach labels and perform depth analysis to pipes with robust ground elevation."""
    # Initialize depth configuration
    init_depth_config()
    
    # Try to load surface data from PDF
    surface = None
    if file_ref:
        surface = load_surface_from_pdf(file_ref)
    
    # Try to parse profile GL data from sheet
    profile_gl = None
    if sheet_data:
        profile_gl = parse_profile_gl(sheet_data)
    
    # Calculate constant fallback from node elevations
    node_elevations = [100.0, 99.5, 99.0]  # Mock node elevations
    constant_elevation = min(node_elevations) if node_elevations else 100.0
    
    for pipe in pipes:
        # Create s-profile (station -> invert elevation)
        # In real implementation, this would come from survey data
        s_profile = [
            (0.0, 95.0),  # Start at elevation 95ft
            (1.0, 93.0)    # End at elevation 93ft (2ft drop)
        ]
        
        # Create ground elevation sampler with fallback strategy
        ground_sampler, ground_source = make_ground_sampler(
            profile_gl=profile_gl,
            surface=surface,
            constant=constant_elevation
        )
        
        # Sample depth along pipe run
        samples = sample_depth_along_run(
            s_profile, ground_sampler, pipe.mat, pipe.dia_in, n_samples=20
        )
        
        # Calculate depth summary
        summary = summarize_depth(samples, "sewer")
        
        # Attach depth information to pipe with ground source tracking
        pipe.avg_depth_ft = summary.avg_depth_ft
        pipe.extra = {
            "min_depth_ft": summary.min_depth_ft,
            "max_depth_ft": summary.max_depth_ft,
            "p95_depth_ft": summary.p95_depth_ft,
            "buckets_lf": summary.buckets_lf,
            "trench_volume_cy": summary.trench_volume_cy,
            "cover_ok": summary.cover_ok,
            "deep_excavation": summary.deep_excavation,
            "_ground_source": ground_source  # Track ground elevation source
        }
    
    return pipes


def detect_sanitary_network(vectors: List[Dict], texts: List[Dict], 
                           file_ref: str = None, sheet_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Main function to detect and analyze sanitary network."""
    # Detect nodes
    nodes = detect_nodes(vectors, texts)
    
    # Trace edges
    pipes = trace_edges(vectors, nodes)
    
    # Attach labels and perform depth analysis with ground elevation data
    pipes_with_depth = attach_labels(pipes, texts, file_ref=file_ref, sheet_data=sheet_data)
    
    # Convert pipes to dict format and add QA flags
    pipe_dicts = []
    qa_flags = []
    
    for p in pipes_with_depth:
        pipe_dict = {
            "id": p.id,
            "from_id": p.from_id,
            "to_id": p.to_id,
            "length_ft": p.length_ft,
            "dia_in": p.dia_in,
            "mat": p.mat,
            "avg_depth_ft": p.avg_depth_ft,
            "extra": p.extra
        }
        
        # Validate pipe for QA issues
        pipe_qa_flags = validate_pipe_qa(pipe_dict, "sewer")
        qa_flags.extend(pipe_qa_flags)
        
        pipe_dicts.append(pipe_dict)
    
    return {
        "nodes": nodes,
        "pipes": pipe_dicts,
        "qa_flags": qa_flags
    }
