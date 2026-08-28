"""
Performance Tests: Logical Topology Transit & Linux Namespace Simulation.

Validates multi-hop latency accumulation, MTU drop constraints, and fan-out path discovery.
"""

import pytest

from app.testing.base_test import BaseNetworkTest
from app.testing.metadata import test_case, TestCategory, ProtocolType, OSI_Layer, TestPriority
from app.topology.model import LinuxNamespaceTopology, NetworkTopology


@pytest.mark.performance
@pytest.mark.topology
class TestTopologyPerformance(BaseNetworkTest):
    """Test suite evaluating topology performance simulation."""

    @test_case(
        test_id="NET-TOPO-001",
        name="Direct Point-to-Point Topology Transit",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.TOPOLOGY,
        layer=OSI_Layer.LAYER_3,
        priority=TestPriority.HIGH,
        description="Verify simulated packet transmission along direct 2-node point-to-point topology.",
        expected_behavior="Transit succeeds with exact configured link latency and MTU."
    )
    def test_point_to_point_topology_transit(self) -> None:
        """Verify transmission along direct Client -> Server topology."""
        topo = NetworkTopology.create_point_to_point(latency_ms=0.75, mtu=1500)
        res = topo.simulate_transmission(src_name="client", dst_name="server", packet_size_bytes=1000)

        assert res.success is True
        assert res.total_latency_ms == pytest.approx(0.75)
        assert res.path_mtu == 1500
        assert len(res.hops) == 2

    @test_case(
        test_id="NET-TOPO-002",
        name="3-Node Hop-by-Hop Latency Accumulation",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.TOPOLOGY,
        layer=OSI_Layer.LAYER_3,
        priority=TestPriority.CRITICAL,
        description="Verify hop-by-hop latency accumulation across Client -> Router -> Server nodes.",
        expected_behavior="Cumulative latency equals sum of individual link latencies (1.5ms + 3.5ms = 5.0ms)."
    )
    def test_three_node_hop_by_hop_latency_accumulation(self) -> None:
        """Verify latency accumulation across Client -> Router -> Server hops."""
        topo = NetworkTopology.create_standard_three_node(
            client_to_router_latency=1.5,
            router_to_server_latency=3.5
        )
        res = topo.simulate_transmission(src_name="client", dst_name="server", packet_size_bytes=512)

        assert res.success is True
        assert res.total_latency_ms == pytest.approx(5.0)
        assert res.hops == ["client", "router", "server"]

    @test_case(
        test_id="NET-TOPO-003",
        name="Multi-Server Fan-Out Path Discovery",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.TOPOLOGY,
        layer=OSI_Layer.LAYER_3,
        priority=TestPriority.HIGH,
        description="Verify routing and path resolution to multiple distinct server destinations through a shared router.",
        expected_behavior="Calculates correct shortest-path routes and latencies to each target server."
    )
    def test_multi_server_fan_out_routing(self) -> None:
        """Verify routing and path resolution to multiple independent destination servers."""
        servers = ["10.0.2.10", "10.0.3.10", "10.0.4.10"]
        latencies = [1.0, 2.5, 4.0]
        topo = NetworkTopology.create_multi_server(server_ips=servers, link_latencies=latencies)

        res1 = topo.simulate_transmission(src_name="client", dst_name="server_1", packet_size_bytes=64)
        assert res1.success is True
        assert res1.total_latency_ms == pytest.approx(2.0)

        res3 = topo.simulate_transmission(src_name="client", dst_name="server_3", packet_size_bytes=64)
        assert res3.success is True
        assert res3.total_latency_ms == pytest.approx(5.0)

    @test_case(
        test_id="NET-TOPO-004",
        name="Linux Network Namespace Script Generation",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.TOPOLOGY,
        layer=OSI_Layer.LAYER_3,
        priority=TestPriority.MEDIUM,
        description="Verify Linux network namespace bash script generation for ip netns, veth pairs, and tc netem.",
        expected_behavior="Generates valid bash commands for creating namespaces and applying tc netem rules."
    )
    def test_linux_namespace_script_generator(self) -> None:
        """Verify Linux network namespace setup and teardown script generation."""
        setup_script = LinuxNamespaceTopology.generate_setup_script(
            ns_client="test_cli",
            ns_server="test_srv",
            veth_client="veth-c",
            veth_server="veth-s",
            client_ip="10.100.1.1/24",
            server_ip="10.100.1.2/24",
            latency_ms=12.5,
            loss_percent=0.5
        )

        assert "ip netns add test_cli" in setup_script
        assert "ip netns add test_srv" in setup_script
        assert "ip link add veth-c type veth peer name veth-s" in setup_script
        assert "tc qdisc add dev veth-c root netem delay 12.5ms loss 0.5%" in setup_script

        teardown_script = LinuxNamespaceTopology.generate_teardown_script("test_cli", "test_srv")
        assert "ip netns del test_cli" in teardown_script
        assert "ip netns del test_srv" in teardown_script
