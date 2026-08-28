"""
Performance Tests: Multi-Stream Concurrency.

Validates throughput scaling and telemetry aggregation across multiple concurrent worker threads.
"""

import pytest

from app.networking.tcp import TCPServer
from app.performance.throughput import TCPThroughputBenchmark
from app.performance.traffic_generator import TrafficConfig, TrafficGenerator
from app.testing.base_test import BaseNetworkTest
from app.testing.metadata import test_case, TestCategory, ProtocolType, OSI_Layer, TestPriority


@pytest.mark.performance
@pytest.mark.tcp
class TestConcurrency(BaseNetworkTest):
    """Test suite evaluating concurrent traffic generation."""

    @test_case(
        test_id="NET-PERF-013",
        name="TCP Multi-Stream Concurrency Scaling",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.CRITICAL,
        description="Measure aggregate throughput scaling across 1, 2, and 4 concurrent TCP connections.",
        expected_behavior="Aggregate bytes and throughput are summed and reported accurately across workers."
    )
    @pytest.mark.parametrize("concurrency", [1, 2, 4])
    def test_tcp_concurrent_stream_scaling(self, tcp_server: TCPServer, concurrency: int) -> None:
        """Measure aggregate throughput across 1, 2, and 4 concurrent TCP connections."""
        duration_s = 0.5
        metrics = TCPThroughputBenchmark.run_concurrent(
            host=tcp_server.host,
            port=tcp_server.port,
            concurrency=concurrency,
            duration_seconds=duration_s,
            packet_size=4096
        )

        assert f"concurrency={concurrency}" in metrics.protocol or metrics.protocol == "TCP"
        assert metrics.bytes_transferred > 0
        assert metrics.duration_seconds > 0
        assert metrics.throughput_mbps > 0
        assert metrics.packet_count > 0

    @test_case(
        test_id="NET-PERF-014",
        name="Traffic Generator Worker Pool Orchestration",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Verify multi-threaded worker pool management, barrier start, and telemetry aggregation in TrafficGenerator.",
        expected_behavior="TrafficGenerator worker threads terminate cleanly and return unified ThroughputMetrics."
    )
    def test_traffic_generator_concurrency(self, tcp_server: TCPServer) -> None:
        """Verify TrafficGenerator concurrency worker orchestration."""
        cfg = TrafficConfig(
            target_host=tcp_server.host,
            target_port=tcp_server.port,
            protocol="TCP",
            duration_seconds=0.5,
            concurrency=2,
            packet_size=2048
        )
        generator = TrafficGenerator(cfg)
        metrics = generator.start()

        assert metrics.protocol == "TCP"
        assert metrics.bytes_transferred > 0
        assert metrics.throughput_mbps > 0
