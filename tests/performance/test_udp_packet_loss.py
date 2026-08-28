"""
Performance Tests: UDP Packet Loss & Sequence Number Tracking.

Validates sequence-level packet tracking, missing packet detection,
and packet loss percentage calculation under lossless and lossy network conditions.
"""

import pytest

from app.networking.udp import UDPServer
from app.performance.packet_loss import UDPPacketLossBenchmark
from app.testing.base_test import BaseNetworkTest
from app.testing.metadata import test_case, TestCategory, ProtocolType, OSI_Layer, TestPriority


@pytest.mark.udp
@pytest.mark.performance
class TestUDPPacketLoss(BaseNetworkTest):
    """Test suite evaluating UDP sequence tracking and loss calculation."""

    @test_case(
        test_id="NET-PERF-008",
        name="UDP Lossless Delivery Verification",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.UDP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.CRITICAL,
        description="Verify 0% packet loss and 0 missing packets when communicating with an unthrottled lossless UDP server.",
        expected_behavior="All 50 sequenced packets are received intact with packet_loss_percent equal to 0.0."
    )
    def test_udp_loss_on_lossless_server(self, udp_server: UDPServer) -> None:
        """Verify 0% packet loss when communicating with an unthrottled lossless UDP server."""
        packet_count = 50
        loss_metrics, _ = UDPPacketLossBenchmark.run_echo_loss_test(
            host=udp_server.host,
            port=udp_server.port,
            packet_count=packet_count,
            packet_size=512,
            inter_packet_interval_seconds=0.001
        )

        assert loss_metrics.protocol == "UDP"
        assert loss_metrics.packets_sent == packet_count
        assert loss_metrics.packets_received == packet_count
        assert loss_metrics.packets_missing == 0
        assert loss_metrics.packet_loss_percent == 0.0

    @test_case(
        test_id="NET-PERF-009",
        name="UDP Lossy Channel Drop Detection",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.UDP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Verify packet loss percentage calculation on a simulated 20% drop UDP channel.",
        expected_behavior="Packet loss percentage accurately reflects the difference between sent and received datagrams."
    )
    def test_udp_loss_on_simulated_lossy_server(self) -> None:
        """Verify that packet loss is detected and calculated accurately on a server simulating drops."""
        simulated_drop_rate = 0.20
        server = UDPServer(host="127.0.0.1", port=0, packet_drop_rate=simulated_drop_rate)
        server.start()

        try:
            packet_count = 60
            loss_metrics, _ = UDPPacketLossBenchmark.run_echo_loss_test(
                host=server.host,
                port=server.port,
                packet_count=packet_count,
                packet_size=256,
                inter_packet_interval_seconds=0.001
            )

            assert loss_metrics.packets_sent == packet_count
            expected_loss = ((loss_metrics.packets_sent - loss_metrics.packets_received) / loss_metrics.packets_sent) * 100.0
            assert loss_metrics.packet_loss_percent == pytest.approx(expected_loss, abs=0.01)
            assert loss_metrics.packets_received <= loss_metrics.packets_sent
        finally:
            server.stop()

    @test_case(
        test_id="NET-PERF-010",
        name="UDP Binary Header Roundtrip Encoding",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.UDP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Verify 16-byte binary sequence header encoding and decoding.",
        expected_behavior="Decoded sequence number and timestamp match original encoded values."
    )
    def test_udp_packet_encoding_roundtrip(self) -> None:
        """Test binary encoding and decoding of sequence header."""
        seq_in = 12345
        t_in = 9876543210123
        payload_data = b"ArbitraryPayloadBytes123"

        encoded = UDPPacketLossBenchmark.encode_sequence_packet(seq_in, t_in, payload_data)
        assert len(encoded) == 16 + len(payload_data)

        seq_out, t_out, raw_data = UDPPacketLossBenchmark.decode_sequence_packet(encoded)
        assert seq_out == seq_in
        assert t_out == t_in
        assert raw_data == payload_data
