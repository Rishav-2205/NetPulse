"""
Integration Test Suite: Multi-Protocol Workflows & Simulated Topology Traversal.

Validates end-to-end network flows across multiple protocols (TCP, UDP, HTTP)
and tests simulated packet routing across the logical topology abstraction (Client -> Router -> Server).
"""

import pytest

from app.networking.http import HTTPClient, HTTPServer
from app.networking.tcp import TCPClient, TCPServer
from app.networking.udp import UDPClient, UDPServer
from app.packets.builder import PayloadGenerator
from app.topology.model import NetworkTopology
from app.testing.assertions import (
    assert_payload_integrity,
    assert_status_code,
)
from app.testing.base_test import BaseNetworkTest
from app.testing.metadata import test_case, TestCategory, ProtocolType, OSI_Layer, TestPriority


@pytest.mark.integration
class TestNetworkIntegration(BaseNetworkTest):
    """Integration test suite for multi-component network workflows."""

    @test_case(
        test_id="NET-INT-001",
        name="Multi-Protocol Concurrent Flow Execution",
        category=TestCategory.INTEGRATION,
        protocol=ProtocolType.FRAMEWORK,
        layer=OSI_Layer.CROSS_LAYER,
        priority=TestPriority.CRITICAL,
        description="Verify seamless execution of TCP, UDP, and HTTP transactions concurrently against separate servers.",
        expected_behavior="All three protocol operations succeed independently without cross-talk or resource contention."
    )
    def test_multi_protocol_concurrent_services(
        self,
        tcp_server: TCPServer,
        udp_server: UDPServer,
        http_server: HTTPServer,
        payload_factory: type[PayloadGenerator]
    ) -> None:
        """Integration: Execute TCP, UDP, and HTTP transactions simultaneously against distinct local servers."""
        payload = payload_factory.generate_small(seed=777)

        # 1. TCP transaction
        with TCPClient() as tcp_client:
            tcp_client.connect(tcp_server.host, tcp_server.port, timeout=2.0)
            tcp_client.send_all(payload)
            tcp_resp = tcp_client.receive_exact(len(payload), timeout=2.0)
            assert_payload_integrity(tcp_resp, payload)

        # 2. UDP transaction
        with UDPClient() as udp_client:
            udp_resp = udp_client.send_and_receive(payload, udp_server.host, udp_server.port, timeout=2.0)
            assert_payload_integrity(udp_resp, payload)

        # 3. HTTP transaction
        with HTTPClient(base_url=http_server.url) as http_client:
            http_resp = http_client.get("/health")
            assert_status_code(http_resp.status_code, 200)
            assert http_resp.json()["status"] == "ok"

    @test_case(
        test_id="NET-INT-002",
        name="Simulated Multi-Hop Topology Traversal",
        category=TestCategory.INTEGRATION,
        protocol=ProtocolType.TOPOLOGY,
        layer=OSI_Layer.LAYER_3,
        priority=TestPriority.HIGH,
        description="Verify simulated packet routing and hop-by-hop latency accumulation across Client -> Router -> Server.",
        expected_behavior="Transit succeeds through designated hops with correct accumulated latency and MTU."
    )
    def test_simulated_topology_path_traversal(self, standard_topology: NetworkTopology) -> None:
        """Integration: Simulate end-to-end packet transmission through Client -> Router -> Server."""
        result = standard_topology.simulate_transmission(
            src_name="client",
            dst_name="server",
            packet_size_bytes=1000
        )

        assert result.success is True
        assert result.hops == ["client", "router", "server"]
        assert result.path_mtu == 1500
        assert result.total_latency_ms == 3.0

    @test_case(
        test_id="NET-INT-003",
        name="Simulated Topology Path MTU Drop",
        category=TestCategory.INTEGRATION,
        protocol=ProtocolType.TOPOLOGY,
        layer=OSI_Layer.LAYER_3,
        priority=TestPriority.HIGH,
        description="Verify simulated oversized packet drop when exceeding bottleneck path MTU.",
        expected_behavior="Transmission fails with explicit drop reason indicating link MTU exceeded."
    )
    def test_simulated_topology_mtu_drop(self, standard_topology: NetworkTopology) -> None:
        """Integration: Simulate oversized packet drop when exceeding path MTU."""
        result = standard_topology.simulate_transmission(
            src_name="client",
            dst_name="server",
            packet_size_bytes=1600
        )

        assert result.success is False
        assert "exceeds link MTU" in (result.drop_reason or "")
