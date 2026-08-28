"""
Functional Tests: UDP Networking Engine.

Validates UDP datagram transmission, response verification, timeout handling,
payload integrity, simulated packet drops, and invalid destination behavior.
"""

import time
import pytest

from app.core.exceptions import (
    TimeoutError as NetPulseTimeoutError,
    PacketValidationError,
)
from app.networking.udp import UDPClient, UDPServer
from app.packets.builder import PayloadGenerator
from app.testing.assertions import assert_payload_integrity
from app.testing.base_test import BaseNetworkTest
from app.testing.metadata import test_case, TestCategory, ProtocolType, OSI_Layer, TestPriority


@pytest.mark.udp
@pytest.mark.functional
class TestUDPFunctional(BaseNetworkTest):
    """Test suite covering UDP datagram network operations."""

    @test_case(
        test_id="NET-UDP-001",
        name="UDP Unicast Datagram Transmission",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.UDP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.CRITICAL,
        description="Verify sending a single datagram and receiving the echo response.",
        expected_behavior="Datagram is delivered without corruption and sender endpoint is verified."
    )
    def test_udp_successful_transmission(self, udp_server: UDPServer) -> None:
        """Test sending a single UDP datagram and verifying server reception."""
        payload = b"NetPulse UDP Single Datagram Test"

        with UDPClient() as client:
            bytes_sent = client.send_datagram(payload, udp_server.host, udp_server.port)
            assert bytes_sent == len(payload)

            data, sender = client.receive_datagram(timeout=2.0)
            assert data == payload
            assert sender[0] == "127.0.0.1"

    @test_case(
        test_id="NET-UDP-002",
        name="UDP Strict Echo Validation",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.UDP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Verify send_and_receive with strict echo comparison enabled.",
        expected_behavior="Echo payload strictly matches original datagram."
    )
    def test_udp_response_validation_match(self, udp_server: UDPServer) -> None:
        """Test send_and_receive with strict echo validation enabled."""
        payload = b"Strict Validation Datagram Content"

        with UDPClient() as client:
            response = client.send_and_receive(
                payload,
                udp_server.host,
                udp_server.port,
                timeout=2.0,
                validate_echo=True
            )
            assert response == payload

    @test_case(
        test_id="NET-UDP-003",
        name="UDP Corrupted Response Detection",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.UDP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Verify detection of mutated/corrupted datagram payload.",
        expected_behavior="PacketValidationError raised when echoed bytes differ."
    )
    def test_udp_response_validation_mismatch(self) -> None:
        """Test that send_and_receive raises PacketValidationError on corrupted response."""
        def corrupting_handler(data: bytes, sender: tuple) -> bytes:
            return b"CORRUPTED_RESPONSE"

        server = UDPServer(host="127.0.0.1", port=0, handler=corrupting_handler)
        server.start()
        try:
            with UDPClient() as client:
                with pytest.raises(PacketValidationError) as exc_info:
                    client.send_and_receive(
                        b"ORIGINAL_PAYLOAD",
                        server.host,
                        server.port,
                        timeout=2.0,
                        validate_echo=True
                    )
                assert "mismatch" in str(exc_info.value)
        finally:
            server.stop()

    @test_case(
        test_id="NET-UDP-004",
        name="UDP Receive Datagram Timeout",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.UDP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.MEDIUM,
        description="Verify timeout raised when no UDP datagram is received.",
        expected_behavior="TimeoutError raised promptly within timeout window."
    )
    def test_udp_receive_timeout(self) -> None:
        """Test that receive_datagram raises TimeoutError when no datagram arrives."""
        with UDPClient() as client:
            start = time.perf_counter()
            with pytest.raises(NetPulseTimeoutError) as exc_info:
                client.receive_datagram(timeout=0.4)

            elapsed = time.perf_counter() - start
            assert elapsed < 2.0
            assert "timed out" in str(exc_info.value)

    @test_case(
        test_id="NET-UDP-005",
        name="UDP Sequenced Multi-Datagram Burst",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.UDP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Verify sending 15 sequential datagrams and validating arrival order.",
        expected_behavior="All 15 datagrams are received and echoed in exact sequence."
    )
    def test_udp_multiple_datagrams(self, udp_server: UDPServer, payload_factory: type[PayloadGenerator]) -> None:
        """Test sending multiple datagrams with sequence numbers and verifying order/content."""
        packet_count = 15
        sent_payloads = [
            f"SEQ-{i:04d}:".encode("utf-8") + payload_factory.generate_random(32, seed=i)
            for i in range(packet_count)
        ]

        with UDPClient() as client:
            for payload in sent_payloads:
                resp = client.send_and_receive(payload, udp_server.host, udp_server.port, timeout=1.0)
                assert resp == payload

        assert udp_server.received_packets_count == packet_count

    @test_case(
        test_id="NET-UDP-006",
        name="UDP Binary Payload CRC32 Integrity",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.UDP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.CRITICAL,
        description="Verify binary payload integrity via CRC32 checksum over UDP datagrams.",
        expected_behavior="CRC32 checksum of received payload matches sent checksum."
    )
    def test_udp_payload_integrity(self, udp_server: UDPServer, payload_factory: type[PayloadGenerator]) -> None:
        """Test transmitting binary payloads and verifying CRC32 / SHA-256 integrity."""
        payload = payload_factory.generate_medium(seed=555)
        checksum_expected = payload_factory.calculate_checksum(payload, algorithm="crc32")

        with UDPClient() as client:
            response = client.send_and_receive(payload, udp_server.host, udp_server.port, timeout=2.0)
            assert_payload_integrity(response, payload)

            checksum_actual = payload_factory.calculate_checksum(response, algorithm="crc32")
            assert checksum_actual == checksum_expected

    @test_case(
        test_id="NET-UDP-007",
        name="UDP Loss Simulation & Drop Tracking",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.UDP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Verify simulated 40% packet drop server tracks dropped vs received count.",
        expected_behavior="Server records exact received and dropped packet statistics."
    )
    def test_udp_simulated_packet_loss(self) -> None:
        """Test server with simulated 40% packet drop rate and verify drop statistics."""
        server = UDPServer(host="127.0.0.1", port=0, packet_drop_rate=0.4)
        server.start()

        total_sent = 30
        received = 0

        try:
            with UDPClient() as client:
                for i in range(total_sent):
                    client.send_datagram(f"Datagram-{i}".encode("utf-8"), server.host, server.port)
                    try:
                        data, _ = client.receive_datagram(timeout=0.1)
                        received += 1
                    except NetPulseTimeoutError:
                        pass

            assert server.received_packets_count == total_sent
            assert server.dropped_packets_count > 0
            assert received < total_sent
        finally:
            server.stop()
