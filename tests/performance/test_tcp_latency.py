"""
Performance Tests: TCP Round-Trip Latency & Connection Time.

Validates TCP RTT percentile calculations (min, max, avg, median, p95, p99)
and TCP 3-way handshake connection establishment latency.
"""

import pytest

from app.networking.tcp import TCPServer
from app.performance.latency import LatencyBenchmark
from app.testing.base_test import BaseNetworkTest
from app.testing.metadata import test_case, TestCategory, ProtocolType, OSI_Layer, TestPriority


@pytest.mark.tcp
@pytest.mark.performance
class TestTCPLatency(BaseNetworkTest):
    """Test suite evaluating TCP latency characteristics."""

    @test_case(
        test_id="NET-PERF-005",
        name="TCP RTT Percentile Distribution",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.CRITICAL,
        description="Measure round-trip time latency distribution (min, avg, median, p95, p99, max) using monotonic nanosecond clocks.",
        expected_behavior="Latency distribution maintains proper monotonic ordering: min <= median <= p95 <= p99 <= max."
    )
    def test_tcp_rtt_latency_distribution(self, tcp_server: TCPServer) -> None:
        """Measure round-trip time latency distribution for TCP request/response echo."""
        samples_count = 30
        metrics = LatencyBenchmark.measure_tcp_rtt(
            host=tcp_server.host,
            port=tcp_server.port,
            samples_count=samples_count,
            packet_size=64
        )

        assert metrics.samples_count == samples_count
        assert metrics.min_ms > 0
        assert metrics.max_ms >= metrics.min_ms
        assert metrics.min_ms <= metrics.avg_ms <= metrics.max_ms
        assert metrics.min_ms <= metrics.median_ms <= metrics.p95_ms <= metrics.p99_ms <= metrics.max_ms

    @test_case(
        test_id="NET-PERF-006",
        name="TCP Handshake Connection Setup Latency",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Measure connection establishment latency across 15 TCP 3-way handshakes.",
        expected_behavior="Connection setup times are calculated and percentiles reported."
    )
    def test_tcp_connection_establishment_time(self, tcp_server: TCPServer) -> None:
        """Measure TCP connection handshake setup latency across multiple probes."""
        samples_count = 15
        metrics = LatencyBenchmark.measure_connection_time(
            host=tcp_server.host,
            port=tcp_server.port,
            samples_count=samples_count
        )

        assert metrics.samples_count == samples_count
        assert metrics.min_ms > 0
        assert metrics.avg_ms > 0
        assert metrics.p95_ms >= metrics.median_ms
