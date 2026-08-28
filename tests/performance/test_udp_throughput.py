"""
Performance Tests: UDP Datagram Throughput.

Validates UDP transmission throughput, datagram rates, and bandwidth utilization.
"""

import pytest

from app.networking.udp import UDPServer
from app.performance.throughput import UDPThroughputBenchmark
from app.testing.base_test import BaseNetworkTest
from app.testing.metadata import test_case, TestCategory, ProtocolType, OSI_Layer, TestPriority


@pytest.mark.udp
@pytest.mark.performance
class TestUDPThroughput(BaseNetworkTest):
    """Test suite evaluating UDP datagram throughput."""

    @test_case(
        test_id="NET-PERF-003",
        name="UDP Datagram Throughput Across Sizes",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.UDP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.CRITICAL,
        description="Measure UDP throughput (Mbps) and datagram rate across 128B, 512B, 1KB, and 4KB packet sizes.",
        expected_behavior="Throughput and packet rates are calculated from actual transmitted datagrams."
    )
    @pytest.mark.parametrize("packet_size", [128, 512, 1024, 4096])
    def test_udp_throughput_across_packet_sizes(self, udp_server: UDPServer, packet_size: int) -> None:
        """Measure UDP datagram throughput across different datagram sizes."""
        duration_s = 0.5
        metrics = UDPThroughputBenchmark.run_single_stream(
            host=udp_server.host,
            port=udp_server.port,
            duration_seconds=duration_s,
            packet_size=packet_size
        )

        assert metrics.protocol == "UDP"
        assert metrics.bytes_transferred > 0
        assert metrics.duration_seconds > 0
        assert metrics.throughput_mbps > 0
        assert metrics.packet_count > 0

    @test_case(
        test_id="NET-PERF-004",
        name="UDP Fixed Datagram Burst Throughput",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.UDP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Measure UDP burst transmission performance on fixed 200 packet count target.",
        expected_behavior="Transfers all 200 datagrams and records throughput."
    )
    def test_udp_throughput_fixed_packet_count(self, udp_server: UDPServer) -> None:
        """Measure UDP throughput when sending a fixed number of datagrams."""
        target_packets = 200
        metrics = UDPThroughputBenchmark.run_single_stream(
            host=udp_server.host,
            port=udp_server.port,
            duration_seconds=None,
            packet_count=target_packets,
            packet_size=1024
        )

        assert metrics.packet_count == target_packets
        assert metrics.bytes_transferred == target_packets * 1024
        assert metrics.throughput_mbps > 0
