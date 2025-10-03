"""Network domain models for infrastructure networks."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class NodeType(str, Enum):
    """Types of network nodes."""
    MANHOLE = "manhole"
    CATCH_BASIN = "catch_basin"
    INLET = "inlet"
    VALVE = "valve"
    HYDRANT = "hydrant"
    METER = "meter"
    JUNCTION = "junction"
    TERMINAL = "terminal"


class EdgeType(str, Enum):
    """Types of network edges."""
    PIPE = "pipe"
    CONDUIT = "conduit"
    CABLE = "cable"
    DUCT = "duct"


class Material(str, Enum):
    """Common pipe materials."""
    PVC = "pvc"
    CONCRETE = "concrete"
    DUCTILE_IRON = "ductile_iron"
    CAST_IRON = "cast_iron"
    HDPE = "hdpe"
    STEEL = "steel"
    CLAY = "clay"
    VITRIFIED_CLAY = "vitrified_clay"


class Node(BaseModel):
    """Network node representing a junction, manhole, valve, etc."""
    
    id: str = Field(..., description="Unique node identifier")
    node_type: NodeType = Field(..., description="Type of node")
    
    # World coordinates in feet
    x_ft: float = Field(..., description="X coordinate in feet")
    y_ft: float = Field(..., description="Y coordinate in feet")
    z_ft: Optional[float] = Field(None, description="Z coordinate (elevation) in feet")
    
    # Attributes
    diameter_in: Optional[float] = Field(None, description="Diameter in inches")
    material: Optional[Material] = Field(None, description="Material type")
    invert_ft: Optional[float] = Field(None, description="Invert elevation in feet")
    rim_ft: Optional[float] = Field(None, description="Rim elevation in feet")
    
    # Additional attributes
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional node attributes")
    
    class Config:
        use_enum_values = True


class Edge(BaseModel):
    """Network edge representing a pipe, conduit, cable, etc."""
    
    id: str = Field(..., description="Unique edge identifier")
    edge_type: EdgeType = Field(..., description="Type of edge")
    
    # Connected nodes
    from_node_id: str = Field(..., description="Source node ID")
    to_node_id: str = Field(..., description="Target node ID")
    
    # World coordinates in feet (polyline points)
    points_ft: List[tuple[float, float]] = Field(..., description="Edge points in feet (x, y)")
    
    # Attributes
    diameter_in: Optional[float] = Field(None, description="Diameter in inches")
    material: Optional[Material] = Field(None, description="Material type")
    slope_percent: Optional[float] = Field(None, description="Slope as percentage")
    slope_ratio: Optional[float] = Field(None, description="Slope as ratio (rise/run)")
    length_ft: Optional[float] = Field(None, description="Calculated length in feet")
    
    # Additional attributes
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional edge attributes")
    
    class Config:
        use_enum_values = True


class Network(BaseModel):
    """Complete network representation."""
    
    id: str = Field(..., description="Network identifier")
    name: str = Field(..., description="Network name")
    network_type: str = Field(..., description="Type of network (storm, sanitary, water, etc.)")
    
    # Network components
    nodes: List[Node] = Field(default_factory=list, description="Network nodes")
    edges: List[Edge] = Field(default_factory=list, description="Network edges")
    
    # Network metadata
    bounds_ft: Optional[tuple[float, float, float, float]] = Field(
        None, 
        description="Network bounds (min_x, min_y, max_x, max_y) in feet"
    )
    total_length_ft: Optional[float] = Field(None, description="Total network length in feet")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional network metadata")
    
    def add_node(self, node: Node) -> None:
        """Add a node to the network."""
        self.nodes.append(node)
        self._update_bounds()
    
    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the network."""
        self.edges.append(edge)
        self._update_bounds()
        self._update_total_length()
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_edge(self, edge_id: str) -> Optional[Edge]:
        """Get an edge by ID."""
        for edge in self.edges:
            if edge.id == edge_id:
                return edge
        return None
    
    def get_edges_from_node(self, node_id: str) -> List[Edge]:
        """Get all edges connected to a node."""
        edges = []
        for edge in self.edges:
            if edge.from_node_id == node_id or edge.to_node_id == node_id:
                edges.append(edge)
        return edges
    
    def get_edges_to_node(self, node_id: str) -> List[Edge]:
        """Get all edges connected to a node."""
        edges = []
        for edge in self.edges:
            if edge.to_node_id == node_id:
                edges.append(edge)
        return edges
    
    def _update_bounds(self) -> None:
        """Update network bounds."""
        if not self.nodes and not self.edges:
            self.bounds_ft = None
            return
        
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')
        
        # Include node coordinates
        for node in self.nodes:
            min_x = min(min_x, node.x_ft)
            min_y = min(min_y, node.y_ft)
            max_x = max(max_x, node.x_ft)
            max_y = max(max_y, node.y_ft)
        
        # Include edge coordinates
        for edge in self.edges:
            for x, y in edge.points_ft:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
        
        self.bounds_ft = (min_x, min_y, max_x, max_y)
    
    def _update_total_length(self) -> None:
        """Update total network length."""
        total_length = 0.0
        
        for edge in self.edges:
            if edge.length_ft:
                total_length += edge.length_ft
            else:
                # Calculate length from points
                length = 0.0
                for i in range(len(edge.points_ft) - 1):
                    x1, y1 = edge.points_ft[i]
                    x2, y2 = edge.points_ft[i + 1]
                    length += ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                total_length += length
        
        self.total_length_ft = total_length
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert network to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "network_type": self.network_type,
            "nodes": [node.dict() for node in self.nodes],
            "edges": [edge.dict() for edge in self.edges],
            "bounds_ft": self.bounds_ft,
            "total_length_ft": self.total_length_ft,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Network':
        """Create network from dictionary."""
        nodes = [Node(**node_data) for node_data in data.get("nodes", [])]
        edges = [Edge(**edge_data) for edge_data in data.get("edges", [])]
        
        return cls(
            id=data["id"],
            name=data["name"],
            network_type=data["network_type"],
            nodes=nodes,
            edges=edges,
            bounds_ft=data.get("bounds_ft"),
            total_length_ft=data.get("total_length_ft"),
            metadata=data.get("metadata", {})
        )
