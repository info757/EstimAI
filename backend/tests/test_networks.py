"""Tests for network domain models."""
import pytest
from app.domain.networks import (
    Node, Edge, Network, NodeType, EdgeType, Material,
    Network as NetworkModel
)


class TestNode:
    """Test Node model."""
    
    def test_node_creation(self):
        """Test node creation."""
        node = Node(
            id="test-node-1",
            node_type=NodeType.MANHOLE,
            x_ft=100.0,
            y_ft=200.0,
            z_ft=105.0,
            diameter_in=24.0,
            material=Material.CONCRETE,
            invert_ft=100.0,
            rim_ft=105.0
        )
        
        assert node.id == "test-node-1"
        assert node.node_type == NodeType.MANHOLE
        assert node.x_ft == 100.0
        assert node.y_ft == 200.0
        assert node.z_ft == 105.0
        assert node.diameter_in == 24.0
        assert node.material == Material.CONCRETE
        assert node.invert_ft == 100.0
        assert node.rim_ft == 105.0
    
    def test_node_with_attributes(self):
        """Test node with additional attributes."""
        node = Node(
            id="test-node-2",
            node_type=NodeType.HYDRANT,
            x_ft=150.0,
            y_ft=250.0,
            attributes={"pressure_psi": 150.0, "flow_gpm": 1000.0}
        )
        
        assert node.attributes["pressure_psi"] == 150.0
        assert node.attributes["flow_gpm"] == 1000.0


class TestEdge:
    """Test Edge model."""
    
    def test_edge_creation(self):
        """Test edge creation."""
        edge = Edge(
            id="test-edge-1",
            edge_type=EdgeType.PIPE,
            from_node_id="node-1",
            to_node_id="node-2",
            points_ft=[(0.0, 0.0), (100.0, 0.0), (200.0, 0.0)],
            diameter_in=12.0,
            material=Material.PVC,
            slope_percent=2.0,
            length_ft=200.0
        )
        
        assert edge.id == "test-edge-1"
        assert edge.edge_type == EdgeType.PIPE
        assert edge.from_node_id == "node-1"
        assert edge.to_node_id == "node-2"
        assert edge.points_ft == [(0.0, 0.0), (100.0, 0.0), (200.0, 0.0)]
        assert edge.diameter_in == 12.0
        assert edge.material == Material.PVC
        assert edge.slope_percent == 2.0
        assert edge.length_ft == 200.0
    
    def test_edge_with_attributes(self):
        """Test edge with additional attributes."""
        edge = Edge(
            id="test-edge-2",
            edge_type=EdgeType.PIPE,
            from_node_id="node-1",
            to_node_id="node-2",
            points_ft=[(0.0, 0.0), (100.0, 0.0)],
            attributes={"pressure_psi": 150.0, "flow_gpm": 500.0}
        )
        
        assert edge.attributes["pressure_psi"] == 150.0
        assert edge.attributes["flow_gpm"] == 500.0


class TestNetwork:
    """Test Network model."""
    
    def test_network_creation(self):
        """Test network creation."""
        network = Network(
            id="test-network-1",
            name="Test Network",
            network_type="storm"
        )
        
        assert network.id == "test-network-1"
        assert network.name == "Test Network"
        assert network.network_type == "storm"
        assert len(network.nodes) == 0
        assert len(network.edges) == 0
    
    def test_add_node(self):
        """Test adding nodes to network."""
        network = Network(
            id="test-network-1",
            name="Test Network",
            network_type="storm"
        )
        
        node = Node(
            id="node-1",
            node_type=NodeType.MANHOLE,
            x_ft=0.0,
            y_ft=0.0
        )
        
        network.add_node(node)
        assert len(network.nodes) == 1
        assert network.nodes[0] == node
    
    def test_add_edge(self):
        """Test adding edges to network."""
        network = Network(
            id="test-network-1",
            name="Test Network",
            network_type="storm"
        )
        
        edge = Edge(
            id="edge-1",
            edge_type=EdgeType.PIPE,
            from_node_id="node-1",
            to_node_id="node-2",
            points_ft=[(0.0, 0.0), (100.0, 0.0)]
        )
        
        network.add_edge(edge)
        assert len(network.edges) == 1
        assert network.edges[0] == edge
    
    def test_get_node(self):
        """Test getting node by ID."""
        network = Network(
            id="test-network-1",
            name="Test Network",
            network_type="storm"
        )
        
        node = Node(
            id="node-1",
            node_type=NodeType.MANHOLE,
            x_ft=0.0,
            y_ft=0.0
        )
        
        network.add_node(node)
        
        retrieved_node = network.get_node("node-1")
        assert retrieved_node == node
        
        non_existent = network.get_node("non-existent")
        assert non_existent is None
    
    def test_get_edge(self):
        """Test getting edge by ID."""
        network = Network(
            id="test-network-1",
            name="Test Network",
            network_type="storm"
        )
        
        edge = Edge(
            id="edge-1",
            edge_type=EdgeType.PIPE,
            from_node_id="node-1",
            to_node_id="node-2",
            points_ft=[(0.0, 0.0), (100.0, 0.0)]
        )
        
        network.add_edge(edge)
        
        retrieved_edge = network.get_edge("edge-1")
        assert retrieved_edge == edge
        
        non_existent = network.get_edge("non-existent")
        assert non_existent is None
    
    def test_get_edges_from_node(self):
        """Test getting edges from a node."""
        network = Network(
            id="test-network-1",
            name="Test Network",
            network_type="storm"
        )
        
        # Add nodes
        node1 = Node(id="node-1", node_type=NodeType.MANHOLE, x_ft=0.0, y_ft=0.0)
        node2 = Node(id="node-2", node_type=NodeType.MANHOLE, x_ft=100.0, y_ft=0.0)
        node3 = Node(id="node-3", node_type=NodeType.MANHOLE, x_ft=200.0, y_ft=0.0)
        
        network.add_node(node1)
        network.add_node(node2)
        network.add_node(node3)
        
        # Add edges
        edge1 = Edge(id="edge-1", edge_type=EdgeType.PIPE, from_node_id="node-1", to_node_id="node-2", points_ft=[(0.0, 0.0), (100.0, 0.0)])
        edge2 = Edge(id="edge-2", edge_type=EdgeType.PIPE, from_node_id="node-1", to_node_id="node-3", points_ft=[(0.0, 0.0), (200.0, 0.0)])
        edge3 = Edge(id="edge-3", edge_type=EdgeType.PIPE, from_node_id="node-2", to_node_id="node-3", points_ft=[(100.0, 0.0), (200.0, 0.0)])
        
        network.add_edge(edge1)
        network.add_edge(edge2)
        network.add_edge(edge3)
        
        # Test getting edges from node-1
        edges_from_node1 = network.get_edges_from_node("node-1")
        assert len(edges_from_node1) == 2
        assert edge1 in edges_from_node1
        assert edge2 in edges_from_node1
        
        # Test getting edges from node-2
        edges_from_node2 = network.get_edges_from_node("node-2")
        assert len(edges_from_node2) == 2
        assert edge1 in edges_from_node2
        assert edge3 in edges_from_node2
    
    def test_get_edges_to_node(self):
        """Test getting edges to a node."""
        network = Network(
            id="test-network-1",
            name="Test Network",
            network_type="storm"
        )
        
        # Add nodes
        node1 = Node(id="node-1", node_type=NodeType.MANHOLE, x_ft=0.0, y_ft=0.0)
        node2 = Node(id="node-2", node_type=NodeType.MANHOLE, x_ft=100.0, y_ft=0.0)
        node3 = Node(id="node-3", node_type=NodeType.MANHOLE, x_ft=200.0, y_ft=0.0)
        
        network.add_node(node1)
        network.add_node(node2)
        network.add_node(node3)
        
        # Add edges
        edge1 = Edge(id="edge-1", edge_type=EdgeType.PIPE, from_node_id="node-1", to_node_id="node-2", points_ft=[(0.0, 0.0), (100.0, 0.0)])
        edge2 = Edge(id="edge-2", edge_type=EdgeType.PIPE, from_node_id="node-1", to_node_id="node-3", points_ft=[(0.0, 0.0), (200.0, 0.0)])
        edge3 = Edge(id="edge-3", edge_type=EdgeType.PIPE, from_node_id="node-2", to_node_id="node-3", points_ft=[(100.0, 0.0), (200.0, 0.0)])
        
        network.add_edge(edge1)
        network.add_edge(edge2)
        network.add_edge(edge3)
        
        # Test getting edges to node-2
        edges_to_node2 = network.get_edges_to_node("node-2")
        assert len(edges_to_node2) == 1
        assert edge1 in edges_to_node2
        
        # Test getting edges to node-3
        edges_to_node3 = network.get_edges_to_node("node-3")
        assert len(edges_to_node3) == 2
        assert edge2 in edges_to_node3
        assert edge3 in edges_to_node3
    
    def test_to_dict(self):
        """Test converting network to dictionary."""
        network = Network(
            id="test-network-1",
            name="Test Network",
            network_type="storm"
        )
        
        node = Node(id="node-1", node_type=NodeType.MANHOLE, x_ft=0.0, y_ft=0.0)
        edge = Edge(id="edge-1", edge_type=EdgeType.PIPE, from_node_id="node-1", to_node_id="node-2", points_ft=[(0.0, 0.0), (100.0, 0.0)])
        
        network.add_node(node)
        network.add_edge(edge)
        
        network_dict = network.to_dict()
        
        assert network_dict["id"] == "test-network-1"
        assert network_dict["name"] == "Test Network"
        assert network_dict["network_type"] == "storm"
        assert len(network_dict["nodes"]) == 1
        assert len(network_dict["edges"]) == 1
    
    def test_from_dict(self):
        """Test creating network from dictionary."""
        network_dict = {
            "id": "test-network-1",
            "name": "Test Network",
            "network_type": "storm",
            "nodes": [
                {
                    "id": "node-1",
                    "node_type": "manhole",
                    "x_ft": 0.0,
                    "y_ft": 0.0
                }
            ],
            "edges": [
                {
                    "id": "edge-1",
                    "edge_type": "pipe",
                    "from_node_id": "node-1",
                    "to_node_id": "node-2",
                    "points_ft": [(0.0, 0.0), (100.0, 0.0)]
                }
            ]
        }
        
        network = Network.from_dict(network_dict)
        
        assert network.id == "test-network-1"
        assert network.name == "Test Network"
        assert network.network_type == "storm"
        assert len(network.nodes) == 1
        assert len(network.edges) == 1
        assert network.nodes[0].id == "node-1"
        assert network.edges[0].id == "edge-1"


class TestEnums:
    """Test enum types."""
    
    def test_node_type_enum(self):
        """Test NodeType enum."""
        assert NodeType.MANHOLE == "manhole"
        assert NodeType.CATCH_BASIN == "catch_basin"
        assert NodeType.INLET == "inlet"
        assert NodeType.VALVE == "valve"
        assert NodeType.HYDRANT == "hydrant"
        assert NodeType.METER == "meter"
        assert NodeType.JUNCTION == "junction"
        assert NodeType.TERMINAL == "terminal"
    
    def test_edge_type_enum(self):
        """Test EdgeType enum."""
        assert EdgeType.PIPE == "pipe"
        assert EdgeType.CONDUIT == "conduit"
        assert EdgeType.CABLE == "cable"
        assert EdgeType.DUCT == "duct"
    
    def test_material_enum(self):
        """Test Material enum."""
        assert Material.PVC == "pvc"
        assert Material.CONCRETE == "concrete"
        assert Material.DUCTILE_IRON == "ductile_iron"
        assert Material.CAST_IRON == "cast_iron"
        assert Material.HDPE == "hdpe"
        assert Material.STEEL == "steel"
        assert Material.CLAY == "clay"
        assert Material.VITRIFIED_CLAY == "vitrified_clay"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
