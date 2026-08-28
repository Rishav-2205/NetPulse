"""
Performance Tests: UDP Round-Trip Latency.

Validates UDP RTT latency distribution across packet payload sizes.
"""

import pytest

from app.networking.udp import UDPServer
from app.performance.latency import LatencyBenchmark
from app.testing.base_test import BaseNetworkTest
from app.testing.metadata import test_case, TestCategory, ProtocolType, OSI_Layer, TestPriority


@pytest.mark.udp
@pytest.mark.performance
class TestUDPLatency(BaseNetworkTest):
    """Test suite evaluating UDP latency characteristics."""

    @test_case(
        test_id="NET-PERF-007",
        name="UDP Datagram Latency Distribution",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.UDP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.CRITICAL,
        description="Measure round-trip time latency distribution for UDP datagram echo across 64B, 512B, and 1KB payloads.",
        expected_behavior="Latency distribution maintains proper ordering: min <= median <= p95 <= max."
    )
    @pytest.mark.parametrize("packet_size", [64, 512, 1024])
    def test_udp_rtt_latency_distribution(self, udp_server: UDPServer, packet_size: int) -> None:
        """Measure round-trip time latency distribution for UDP datagram echo."""
        samples_count = 30
        metrics = LatencyBenchmark.measure_udp_rtt(
            host=udp_server.host,
            port=udp_server.port,
            samples_count=samples_count,
            packet_size=packet_size
        )

        assert metrics.samples_count == samples_count
        assert metrics.min_ms > 0
        assert metrics.max_ms >= metrics.min_ms
        assert metrics.min_ms <= metrics.avg_ms <= metrics.max_ms
        assert metrics.min_ms <= metrics.median_ms <= metrics.p95_ms <= metrics.max_ms
