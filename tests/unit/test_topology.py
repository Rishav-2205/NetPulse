"""
Unit Tests: Network Topology Modeling.
"""

import pytest

from app.core.exceptions import TopologyError
from app.topology.model import NetworkTopology, Node, NodeType, Link


@pytest.mark.unit
class TestTopologyModel:
    """Test suite covering logical network topology abstraction."""

    def test_topology_creation_and_node_registration(self) -> None:
        """Test building nodes and links in a network topology."""
        topo = NetworkTopology(name="Test Topo")
        n1 = topo.add_node(Node("host1", NodeType.CLIENT, "10.0.0.1"))
        n2 = topo.add_node(Node("switch1", NodeType.SWITCH, "10.0.0.254"))
        n3 = topo.add_node(Node("host2", NodeType.SERVER, "10.0.0.2"))

        topo.add_link("host1", "switch1", latency_ms=0.5, mtu=1500)
        topo.add_link("switch1", "host2", latency_ms=0.5, mtu=1500)

        assert len(topo.nodes) == 3
        assert len(topo.links) == 2

    def test_duplicate_node_raises_error(self) -> None:
        """Test that registering duplicate node names raises TopologyError."""
        topo = NetworkTopology()
        topo.add_node(Node("n1", NodeType.CLIENT, "1.1.1.1"))
        with pytest.raises(TopologyError) as exc_info:
            topo.add_node(Node("n1", NodeType.CLIENT, "1.1.1.1"))
        assert "already exists" in str(exc_info.value)

    def test_path_finding_and_latency_accumulation(self) -> None:
        """Test shortest path resolution and end-to-end latency calculation."""
        topo = NetworkTopology.create_standard_three_node(
            client_to_router_latency=2.5,
            router_to_server_latency=4.0
        )

        res = topo.simulate_transmission("client", "server", packet_size_bytes=500)
        assert res.success is True
        assert res.total_latency_ms == 6.5
        assert res.hops == ["client", "router", "server"]

    def test_disconnected_nodes_path_failure(self) -> None:
        """Test path calculation on disconnected network partition."""
        topo = NetworkTopology()
        topo.add_node(Node("a", NodeType.CLIENT, "1.1.1.1"))
        topo.add_node(Node("b", NodeType.SERVER, "2.2.2.2"))

        with pytest.raises(TopologyError) as exc_info:
            topo.find_path("a", "b")
        assert "No path found" in str(exc_info.value)
