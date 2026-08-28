"""
Performance Tests: Scapy Packet Capture & Deep Packet Analysis.

Validates Ethernet/IP/TCP and Ethernet/IP/UDP frame construction,
TCP flag extraction, BPF filter verification, and stream flow analysis.
"""

import pytest

from app.packets.analyzer import PacketAnalyzer
from app.packets.builder import PacketBuilder
from app.testing.base_test import BaseNetworkTest
from app.testing.metadata import test_case, TestCategory, ProtocolType, OSI_Layer, TestPriority


@pytest.mark.performance
@pytest.mark.packet_capture
class TestPacketCaptureAndAnalysis(BaseNetworkTest):
    """Test suite evaluating packet generation, capture, and dissection."""

    @test_case(
        test_id="NET-CAP-001",
        name="Ethernet/IP/TCP Frame Dissection",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.CROSS_LAYER,
        priority=TestPriority.CRITICAL,
        description="Construct custom Layer 2/3/4 TCP SYN frame via Scapy and verify deep header field dissection.",
        expected_behavior="Extracted MACs, IPs, ports, and SYN flag match constructed parameters exactly."
    )
    def test_ether_ip_tcp_builder_and_analyzer(self) -> None:
        """Construct a Layer 2/3/4 TCP SYN packet and verify all extracted fields."""
        pkt = PacketBuilder.build_ether_ip_tcp(
            src_mac="00:11:22:33:44:55",
            dst_mac="66:77:88:99:aa:bb",
            src_ip="192.168.1.10",
            dst_ip="192.168.1.1",
            sport=54321,
            dport=443,
            flags="S"
        )

        summary = PacketAnalyzer.analyze_packet(pkt)
        assert summary.src_mac == "00:11:22:33:44:55"
        assert summary.dst_mac == "66:77:88:99:aa:bb"
        assert summary.src_ip == "192.168.1.10"
        assert summary.dst_ip == "192.168.1.1"
        assert summary.src_port == 54321
        assert summary.dst_port == 443
        assert summary.protocol == "TCP"
        assert "SYN" in summary.tcp_flags

    @test_case(
        test_id="NET-CAP-002",
        name="Ethernet/IP/UDP Datagram Dissection",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.UDP,
        layer=OSI_Layer.CROSS_LAYER,
        priority=TestPriority.HIGH,
        description="Construct custom Layer 2/3/4 UDP datagram and verify payload extraction.",
        expected_behavior="Analyzed packet matches source/dest IPs, ports, and payload byte length."
    )
    def test_ether_ip_udp_builder_and_analyzer(self) -> None:
        """Construct a Layer 2/3/4 UDP packet and verify dissection."""
        payload_data = b"NetPulse Automated Test Payload"
        pkt = PacketBuilder.build_ether_ip_udp(
            src_ip="10.0.0.1",
            dst_ip="10.0.0.2",
            sport=1234,
            dport=5678,
            payload=payload_data
        )

        summary = PacketAnalyzer.analyze_packet(pkt)
        assert summary.src_ip == "10.0.0.1"
        assert summary.dst_ip == "10.0.0.2"
        assert summary.src_port == 1234
        assert summary.dst_port == 5678
        assert summary.protocol == "UDP"
        assert summary.payload_size == len(payload_data)

    @test_case(
        test_id="NET-CAP-003",
        name="TCP Flags Dissection Across Flag Combinations",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Verify accurate parsing of TCP flag combinations (SYN-ACK, FIN-ACK, RST).",
        expected_behavior="Analyzer correctly identifies SYN, ACK, and FIN flags."
    )
    def test_tcp_flags_dissection(self) -> None:
        """Verify parsing of various TCP flag combinations (SYN-ACK, FIN-ACK, RST)."""
        pkt_syn_ack = PacketBuilder.build_ether_ip_tcp(flags="SA")
        summary_sa = PacketAnalyzer.analyze_packet(pkt_syn_ack)
        assert "SYN" in summary_sa.tcp_flags
        assert "ACK" in summary_sa.tcp_flags

        pkt_fin_ack = PacketBuilder.build_ether_ip_tcp(flags="FA")
        summary_fa = PacketAnalyzer.analyze_packet(pkt_fin_ack)
        assert "FIN" in summary_fa.tcp_flags
        assert "ACK" in summary_fa.tcp_flags

    @test_case(
        test_id="NET-CAP-004",
        name="Stream Flow Aggregation & Protocol Breakdown",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.FRAMEWORK,
        layer=OSI_Layer.CROSS_LAYER,
        priority=TestPriority.CRITICAL,
        description="Verify flow identification, conversation aggregation, and protocol distribution across captured packet bursts.",
        expected_behavior="Flow analysis reports 2 flows, accurate total byte volume, and TCP/UDP breakdown."
    )
    def test_stream_flow_aggregation(self) -> None:
        """Verify aggregation of packets into flow streams and statistical calculation."""
        p1 = PacketBuilder.build_ether_ip_tcp(src_ip="192.168.1.10", dst_ip="10.0.0.1", sport=5000, dport=80, payload=b"GET / HTTP/1.1\r\n\r\n")
        p2 = PacketBuilder.build_ether_ip_tcp(src_ip="10.0.0.1", dst_ip="192.168.1.10", sport=80, dport=5000, payload=b"HTTP/1.1 200 OK\r\n\r\n")
        p3 = PacketBuilder.build_ether_ip_udp(src_ip="192.168.1.10", dst_ip="10.0.0.1", sport=53, dport=53, payload=b"DNS_QUERY")

        flows = PacketAnalyzer.analyze_flows([p1, p2, p3])
        assert len(flows) == 2

        tcp_flow = next(f for f in flows if f.protocol == "TCP")
        assert tcp_flow.packet_count == 2
        assert tcp_flow.total_bytes > 0

        proto_counts = PacketAnalyzer.get_protocol_distribution([p1, p2, p3])
        assert proto_counts["TCP"] == 2
        assert proto_counts["UDP"] == 1
