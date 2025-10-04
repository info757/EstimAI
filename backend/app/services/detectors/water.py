"""
Water network detection and analysis.

This module provides functions to detect water network elements and
calculate depth-based trench analysis.
"""
from typing import List, Dict, Any, Optional
from backend.app.services.detectors.depth import (
    sample_depth_along_run, summarize_depth, init_depth_config
)


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


def detect_nodes(vectors: List[Dict], texts: List[Dict]) -> List[Dict]:
    """Detect water network nodes (hydrants, valves, etc.)."""
    # Placeholder implementation
    nodes = []
    for i, text in enumerate(texts[:3]):  # Simple example
        nodes.append({
            "id": f"hydrant_{i}",
            "kind": "hydrant",
            "x": text.get("x", 0.0),
            "y": text.get("y", 0.0),
            "attrs": {"label": text.get("text", "")}
        })
    return nodes


def trace_edges(vectors: List[Dict], nodes: List[Dict]) -> List[Pipe]:
    """Trace water network edges (pipes) between nodes."""
    pipes = []
    
    # Simple example: create pipes between detected nodes
    for i in range(len(nodes) - 1):
        pipe = Pipe(
            id=f"water_pipe_{i}",
            from_id=nodes[i]["id"],
            to_id=nodes[i + 1]["id"],
            length_ft=60.0 + (i * 30.0),  # Varying lengths
            dia_in=6.0 + (i * 1.0),  # Varying diameters
            mat="ductile_iron"
        )
        pipes.append(pipe)
    
    return pipes


def attach_labels(pipes: List[Pipe], texts: List[Dict]) -> List[Pipe]:
    """Attach labels and perform depth analysis to pipes."""
    # Initialize depth configuration
    init_depth_config()
    
    for pipe in pipes:
        # Create simple s-profile (station -> invert elevation)
        # In real implementation, this would come from survey data
        s_profile = [
            (0.0, 90.0),  # Start at elevation 90ft
            (1.0, 88.0)    # End at elevation 88ft (2ft drop)
        ]
        
        # Simple ground profile function
        # In real implementation, this would use TIN or survey data
        def ground_at_s(station: float) -> float:
            return 95.0 - (station * 0.3)  # Ground drops 0.3ft over run
        
        # Sample depth along pipe run
        samples = sample_depth_along_run(
            s_profile, ground_at_s, pipe.mat, pipe.dia_in, n_samples=20
        )
        
        # Calculate depth summary
        summary = summarize_depth(samples, "water")
        
        # Attach depth information to pipe
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
    
    return pipes


def detect_water_network(vectors: List[Dict], texts: List[Dict]) -> Dict[str, Any]:
    """Main function to detect and analyze water network."""
    # Detect nodes
    nodes = detect_nodes(vectors, texts)
    
    # Trace edges
    pipes = trace_edges(vectors, nodes)
    
    # Attach labels and perform depth analysis
    pipes_with_depth = attach_labels(pipes, texts)
    
    return {
        "nodes": nodes,
        "pipes": [
            {
                "id": p.id,
                "from_id": p.from_id,
                "to_id": p.to_id,
                "length_ft": p.length_ft,
                "dia_in": p.dia_in,
                "mat": p.mat,
                "avg_depth_ft": p.avg_depth_ft,
                "extra": p.extra
            }
            for p in pipes_with_depth
        ]
    }
