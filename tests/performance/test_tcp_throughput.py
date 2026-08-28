"""
Performance Tests: TCP Stream Throughput.

Validates TCP throughput calculation, byte transfer rates, and duration tracking
across parameterized packet payload sizes.
"""

import pytest

from app.networking.tcp import TCPServer
from app.performance.throughput import TCPThroughputBenchmark
from app.testing.base_test import BaseNetworkTest
from app.testing.metadata import test_case, TestCategory, ProtocolType, OSI_Layer, TestPriority


@pytest.mark.tcp
@pytest.mark.performance
class TestTCPThroughput(BaseNetworkTest):
    """Test suite evaluating TCP stream throughput."""

    @test_case(
        test_id="NET-PERF-001",
        name="TCP Stream Throughput Across Packet Sizes",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.CRITICAL,
        description="Measure real TCP streaming throughput (Mbps) and packet rates across 64B, 1KB, and 8KB chunks.",
        expected_behavior="Real throughput (Mbps) is calculated dynamically from byte counts and monotonic clocks."
    )
    @pytest.mark.parametrize("packet_size", [64, 1024, 8192])
    def test_tcp_throughput_across_packet_sizes(self, tcp_server: TCPServer, packet_size: int) -> None:
        """Measure TCP throughput against local echo server for varied packet chunk sizes."""
        duration_s = 0.5
        metrics = TCPThroughputBenchmark.run_single_stream(
            host=tcp_server.host,
            port=tcp_server.port,
            duration_seconds=duration_s,
            packet_size=packet_size
        )

        assert metrics.protocol == "TCP"
        assert metrics.bytes_transferred > 0
        assert metrics.duration_seconds > 0
        assert metrics.throughput_mbps > 0
        assert metrics.packet_count > 0
        assert metrics.rate_pps > 0

    @test_case(
        test_id="NET-PERF-002",
        name="TCP Throughput on Fixed Byte Target",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Measure TCP throughput and rate when delivering a fixed 100KB payload target.",
        expected_behavior="Target bytes are delivered completely and throughput is reported."
    )
    def test_tcp_throughput_total_bytes_target(self, tcp_server: TCPServer) -> None:
        """Measure TCP throughput when transferring a fixed total byte target."""
        target_bytes = 100_000
        metrics = TCPThroughputBenchmark.run_single_stream(
            host=tcp_server.host,
            port=tcp_server.port,
            duration_seconds=None,
            total_bytes=target_bytes,
            packet_size=4096
        )

        assert metrics.bytes_transferred >= target_bytes
        assert metrics.duration_seconds > 0
        assert metrics.throughput_mbps > 0
