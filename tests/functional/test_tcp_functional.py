"""
Functional Tests: TCP Networking Engine.

Validates TCP connection lifecycle, data transmission, stream integrity,
timeout handling, error states, and edge conditions.
"""

import socket
import threading
import time
import pytest

from app.core.exceptions import (
    ConnectionError as NetPulseConnectionError,
    TimeoutError as NetPulseTimeoutError,
)
from app.networking.connection import ConnectionState
from app.networking.tcp import TCPClient, TCPServer
from app.packets.builder import PayloadGenerator
from app.testing.assertions import (
    assert_payload_integrity,
    assert_tcp_state,
)
from app.testing.base_test import BaseNetworkTest
from app.testing.metadata import test_case, TestCategory, ProtocolType, OSI_Layer, TestPriority


@pytest.mark.tcp
@pytest.mark.functional
class TestTCPFunctional(BaseNetworkTest):
    """Test suite covering TCP functional network operations."""

    @test_case(
        test_id="NET-TCP-001",
        name="TCP Connection Establishment",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.CRITICAL,
        description="Verify full TCP 3-way handshake and state transition to CONNECTED.",
        expected_behavior="Client socket transitions to CONNECTED state and closes cleanly."
    )
    def test_tcp_successful_connection(self, tcp_server: TCPServer) -> None:
        """Test establishing a successful TCP connection."""
        client = TCPClient()
        try:
            client.connect(tcp_server.host, tcp_server.port, timeout=2.0)
            assert client.is_connected
            assert_tcp_state(client.state, ConnectionState.CONNECTED)
        finally:
            client.close()
        assert_tcp_state(client.state, ConnectionState.CLOSED)

    @test_case(
        test_id="NET-TCP-002",
        name="TCP Data Echo Transmission",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.CRITICAL,
        description="Verify bidirectional TCP send and receive with byte exactness.",
        expected_behavior="Received payload matches sent payload byte-for-byte."
    )
    def test_tcp_send_and_receive_data(self, tcp_server: TCPServer, payload_factory: type[PayloadGenerator]) -> None:
        """Test sending and receiving deterministic payload over TCP echo server."""
        payload = payload_factory.generate_medium(seed=101)

        with TCPClient() as client:
            client.connect(tcp_server.host, tcp_server.port, timeout=2.0)
            sent_bytes = client.send(payload)
            assert sent_bytes == len(payload)

            received = client.receive_exact(len(payload), timeout=2.0)
            assert_payload_integrity(received, payload)

    @test_case(
        test_id="NET-TCP-003",
        name="TCP Consecutive Framing",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Verify stream framing across multiple consecutive messages on a single session.",
        expected_behavior="Each discrete message is echoed with intact boundary and ordering."
    )
    def test_tcp_multiple_consecutive_messages(self, tcp_server: TCPServer) -> None:
        """Test sending multiple distinct messages across a single TCP session."""
        messages = [f"Message-{i:03d}".encode("utf-8") for i in range(10)]

        with TCPClient() as client:
            client.connect(tcp_server.host, tcp_server.port, timeout=2.0)
            for msg in messages:
                client.send_all(msg)
                received = client.receive_exact(len(msg), timeout=2.0)
                assert received == msg

    @test_case(
        test_id="NET-TCP-004",
        name="TCP Large Payload SHA-256 Integrity",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.CRITICAL,
        description="Verify 64KB chunked transmission and SHA-256 integrity verification.",
        expected_behavior="SHA-256 digest of received stream strictly matches expected digest."
    )
    def test_tcp_large_payload_stream_integrity(self, tcp_server: TCPServer, payload_factory: type[PayloadGenerator]) -> None:
        """Test streaming a 64KB large payload and verifying checksum integrity."""
        payload = payload_factory.generate_large(seed=202)
        expected_checksum = payload_factory.calculate_checksum(payload, algorithm="sha256")

        with TCPClient() as client:
            client.connect(tcp_server.host, tcp_server.port, timeout=5.0)
            client.send_all(payload)
            received = client.receive_exact(len(payload), timeout=5.0)

            actual_checksum = payload_factory.calculate_checksum(received, algorithm="sha256")
            assert actual_checksum == expected_checksum
            payload_factory.verify_checksum(received, expected_checksum, algorithm="sha256")

    @test_case(
        test_id="NET-TCP-005",
        name="TCP Connection Refused Handling",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Verify handling when connecting to a closed/unbound local port.",
        expected_behavior="ConnectionError raised promptly without hanging."
    )
    def test_tcp_failed_connection_refused(self) -> None:
        """Test connection failure when target port is closed."""
        temp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        temp_sock.bind(("127.0.0.1", 0))
        unused_port = temp_sock.getsockname()[1]
        temp_sock.close()

        client = TCPClient()
        with pytest.raises((NetPulseConnectionError, NetPulseTimeoutError)):
            client.connect("127.0.0.1", unused_port, timeout=1.0)

        assert not client.is_connected

    @test_case(
        test_id="NET-TCP-006",
        name="TCP Non-Routable Timeout",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Verify timeout trigger when connecting to unroutable blackhole IP.",
        expected_behavior="TimeoutError raised within configured timeout window."
    )
    def test_tcp_connection_timeout(self) -> None:
        """Test timeout handling when connecting to a non-routable IP address."""
        client = TCPClient()
        start = time.perf_counter()
        with pytest.raises((NetPulseTimeoutError, NetPulseConnectionError)):
            client.connect("192.0.2.1", 54321, timeout=0.5)

        elapsed = time.perf_counter() - start
        assert elapsed < 3.0
        assert not client.is_connected

    @test_case(
        test_id="NET-TCP-007",
        name="TCP Read Timeout on Silent Server",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.MEDIUM,
        description="Verify receive timeout when server accepts connection but halts sending.",
        expected_behavior="TimeoutError raised upon exceeding receive timeout."
    )
    def test_tcp_receive_timeout_on_silent_server(self) -> None:
        """Test timeout handling when server connects but sends no data."""
        def silent_handler(data: bytes, sock: socket.socket) -> None:
            time.sleep(2.0)
            return None

        server = TCPServer(host="127.0.0.1", port=0, handler=silent_handler)
        server.start()
        try:
            with TCPClient() as client:
                client.connect(server.host, server.port, timeout=2.0)
                client.send(b"hello")
                with pytest.raises(NetPulseTimeoutError) as exc_info:
                    client.receive(buffer_size=1024, timeout=0.5)
                assert "timed out" in str(exc_info.value)
        finally:
            server.stop()

    @test_case(
        test_id="NET-TCP-008",
        name="TCP Post-Close State Protection",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.MEDIUM,
        description="Verify state transitions to CLOSED and prevents post-close transmission.",
        expected_behavior="ConnectionError raised on send attempt after client close."
    )
    def test_tcp_connection_close_state(self, tcp_server: TCPServer) -> None:
        """Test that closing client transitions state and prevents further sends."""
        client = TCPClient()
        client.connect(tcp_server.host, tcp_server.port, timeout=2.0)
        assert client.is_connected

        client.close()
        assert not client.is_connected
        assert_tcp_state(client.state, ConnectionState.CLOSED)

        with pytest.raises(NetPulseConnectionError):
            client.send(b"data after close")

    @test_case(
        test_id="NET-TCP-009",
        name="TCP Server Shutdown Handling",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Verify connection failure handling when target server is stopped.",
        expected_behavior="ConnectionError raised immediately."
    )
    def test_tcp_server_unavailable(self) -> None:
        """Test connecting to a server that has been shut down."""
        server = TCPServer(host="127.0.0.1", port=0)
        server.start()
        port = server.port
        server.stop()

        client = TCPClient()
        with pytest.raises((NetPulseConnectionError, NetPulseTimeoutError)):
            client.connect("127.0.0.1", port, timeout=1.0)

    @test_case(
        test_id="NET-TCP-010",
        name="TCP Concurrent Multi-Client Sessions",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.CRITICAL,
        description="Verify server handles 8 simultaneous client connections without data collision.",
        expected_behavior="All 8 clients receive uncorrupted echo responses concurrently."
    )
    def test_tcp_concurrent_clients(self, tcp_server: TCPServer) -> None:
        """Test handling multiple concurrent client connections simultaneously."""
        errors: list[Exception] = []

        def client_worker(idx: int) -> None:
            try:
                with TCPClient() as client:
                    client.connect(tcp_server.host, tcp_server.port, timeout=3.0)
                    msg = f"Client-{idx}-Payload".encode("utf-8")
                    client.send_all(msg)
                    resp = client.receive_exact(len(msg), timeout=3.0)
                    assert resp == msg
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=client_worker, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent clients encountered errors: {errors}"
        assert tcp_server.total_connections >= 8
