"""
Performance Tests: UDP Inter-Packet Delay Variation (Jitter).

Validates average and maximum jitter calculations based on RFC 3393 / RFC 3550 IPDV.
"""

import pytest

from app.networking.udp import UDPServer
from app.performance.metrics import JitterMetrics
from app.performance.packet_loss import UDPPacketLossBenchmark
from app.testing.base_test import BaseNetworkTest
from app.testing.metadata import test_case, TestCategory, ProtocolType, OSI_Layer, TestPriority


@pytest.mark.udp
@pytest.mark.performance
class TestUDPJitter(BaseNetworkTest):
    """Test suite evaluating UDP inter-packet delay variation."""

    @test_case(
        test_id="NET-PERF-011",
        name="UDP Live Inter-Packet Jitter Measurement",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.UDP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.CRITICAL,
        description="Measure average and maximum UDP jitter over a burst of 40 datagrams using RFC 3393 methodology.",
        expected_behavior="Average and max jitter metrics are computed from monotonic inter-arrival deltas."
    )
    def test_udp_jitter_calculation(self, udp_server: UDPServer) -> None:
        """Measure UDP jitter over a burst of datagrams and assert non-negative metrics."""
        packet_count = 40
        _, jitter_metrics = UDPPacketLossBenchmark.run_echo_loss_test(
            host=udp_server.host,
            port=udp_server.port,
            packet_count=packet_count,
            packet_size=512,
            inter_packet_interval_seconds=0.001
        )

        assert jitter_metrics.protocol == "UDP"
        assert jitter_metrics.average_jitter_ms >= 0.0
        assert jitter_metrics.max_jitter_ms >= jitter_metrics.average_jitter_ms
        assert "RFC 3393" in jitter_metrics.methodology or "RFC 3550" in jitter_metrics.methodology

    @test_case(
        test_id="NET-PERF-012",
        name="UDP Synthetic Delay Variation Verification",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.UDP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Verify statistical jitter computation with known synthetic inter-arrival variations.",
        expected_behavior="Calculated average and max jitter strictly match mathematical expectations."
    )
    def test_jitter_metrics_from_synthetic_delays(self) -> None:
        """Verify statistical jitter computation with known inter-arrival delay variations."""
        synthetic_variations = [0.1, -0.2, 0.4, -0.3, 0.5]
        metrics = JitterMetrics.from_delays(synthetic_variations)

        assert metrics.average_jitter_ms == pytest.approx(0.3, abs=0.001)
        assert metrics.max_jitter_ms == pytest.approx(0.5, abs=0.001)
