"""
Unit Tests: Packet Builders, Parsers & Dissection.
"""

import pytest

from app.packets.builder import PacketBuilder
from app.packets.parser import PacketParser
from app.packets.capture import has_raw_socket_capability, PacketCaptureSession


@pytest.mark.unit
class TestPackets:
    """Test suite covering Scapy packet construction, dissection, and capture capabilities."""

    def test_build_and_parse_tcp_packet(self) -> None:
        """Test building an IP/TCP packet and parsing it back with PacketParser."""
        pkt = PacketBuilder.build_tcp_packet(
            src_ip="192.168.1.50",
            dst_ip="192.168.1.1",
            sport=44332,
            dport=8080,
            flags="SA",  # SYN-ACK
            payload=b"SYN_ACK_PAYLOAD"
        )

        parsed = PacketParser.parse(pkt)
        assert parsed.has_ip is True
        assert parsed.has_tcp is True
        assert parsed.ip is not None
        assert parsed.tcp is not None

        assert parsed.ip.src == "192.168.1.50"
        assert parsed.ip.dst == "192.168.1.1"
        assert parsed.tcp.sport == 44332
        assert parsed.tcp.dport == 8080
        assert "S" in parsed.tcp.flags
        assert "A" in parsed.tcp.flags
        assert parsed.payload == b"SYN_ACK_PAYLOAD"

    def test_build_and_parse_udp_packet(self) -> None:
        """Test building an IP/UDP packet and parsing header fields."""
        pkt = PacketBuilder.build_udp_packet(
            src_ip="10.0.0.5",
            dst_ip="10.0.0.1",
            sport=5000,
            dport=5001,
            payload=b"UDP Payload Test"
        )

        parsed = PacketParser.parse(pkt)
        assert parsed.has_udp is True
        assert parsed.udp is not None
        assert parsed.udp.sport == 5000
        assert parsed.udp.dport == 5001
        assert parsed.payload == b"UDP Payload Test"

    def test_raw_socket_capability_check(self) -> None:
        """Test checking raw socket capability without raising exceptions."""
        cap = has_raw_socket_capability()
        assert isinstance(cap, bool)

    def test_packet_capture_session_simulated(self) -> None:
        """Test packet capture session in simulated / unprivileged mode."""
        session = PacketCaptureSession()
        session.start()

        # Inject simulated packet
        test_pkt = PacketBuilder.build_tcp_packet(payload=b"Simulated Packet")
        session.record_simulated_packet(test_pkt)

        captured = session.stop()
        assert len(captured) == 1
        parsed = PacketParser.parse(captured[0])
        assert parsed.payload == b"Simulated Packet"
