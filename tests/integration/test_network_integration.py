"""
Integration Test Suite: Multi-Protocol Workflows & Simulated Topology Traversal.

Validates end-to-end network flows across multiple protocols (TCP, UDP, HTTP)
and tests simulated packet routing across the logical topology abstraction (Client -> Router -> Server).
"""

import pytest

from app.core.exceptions import PacketValidationError
from app.networking.http import HTTPClient, HTTPServer
from app.networking.tcp import TCPClient, TCPServer
from app.networking.udp import UDPClient, UDPServer
from app.packets.builder import PayloadGenerator
from app.topology.model import NetworkTopology, Node, NodeType
from app.testing.assertions import (
    assert_payload_integrity,
    assert_status_code,
    assert_latency_within,
)
from app.testing.base_test import BaseNetworkTest


@pytest.mark.integration
class TestNetworkIntegration(BaseNetworkTest):
    """Integration test suite for multi-component network workflows."""

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

    def test_simulated_topology_path_traversal(self, standard_topology: NetworkTopology) -> None:
        """Integration: Simulate end-to-end packet transmission through Client -> Router -> Server."""
        # Packet fits inside standard MTU 1500
        result = standard_topology.simulate_transmission(
            src_name="client",
            dst_name="server",
            packet_size_bytes=1000
        )

        assert result.success is True
        assert result.hops == ["client", "router", "server"]
        assert result.path_mtu == 1500
        assert result.total_latency_ms == 3.0  # 1.0ms + 2.0ms

    def test_simulated_topology_mtu_drop(self, standard_topology: NetworkTopology) -> None:
        """Integration: Simulate oversized packet drop when exceeding path MTU."""
        # Packet is 1600 bytes, exceeding 1500 byte MTU
        result = standard_topology.simulate_transmission(
            src_name="client",
            dst_name="server",
            packet_size_bytes=1600
        )

        assert result.success is False
        assert "exceeds link MTU" in (result.drop_reason or "")
