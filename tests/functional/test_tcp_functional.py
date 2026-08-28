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
    SocketError,
)
from app.networking.connection import ConnectionState, SocketOptions
from app.networking.tcp import TCPClient, TCPServer
from app.packets.builder import PayloadGenerator
from app.testing.assertions import (
    assert_payload_integrity,
    assert_tcp_state,
    assert_latency_within,
)
from app.testing.base_test import BaseNetworkTest


@pytest.mark.tcp
@pytest.mark.functional
class TestTCPFunctional(BaseNetworkTest):
    """Test suite covering TCP functional network operations."""

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

    def test_tcp_send_and_receive_data(self, tcp_server: TCPServer, payload_factory: type[PayloadGenerator]) -> None:
        """Test sending and receiving deterministic payload over TCP echo server."""
        payload = payload_factory.generate_medium(seed=101)

        with TCPClient() as client:
            client.connect(tcp_server.host, tcp_server.port, timeout=2.0)
            sent_bytes = client.send(payload)
            assert sent_bytes == len(payload)

            received = client.receive_exact(len(payload), timeout=2.0)
            assert_payload_integrity(received, payload)

    def test_tcp_multiple_consecutive_messages(self, tcp_server: TCPServer) -> None:
        """Test sending multiple distinct messages across a single TCP session."""
        messages = [f"Message-{i:03d}".encode("utf-8") for i in range(10)]

        with TCPClient() as client:
            client.connect(tcp_server.host, tcp_server.port, timeout=2.0)
            for msg in messages:
                client.send_all(msg)
                received = client.receive_exact(len(msg), timeout=2.0)
                assert received == msg

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

    def test_tcp_failed_connection_refused(self) -> None:
        """Test connection failure when target port is closed."""
        # Pick an unused local port
        temp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        temp_sock.bind(("127.0.0.1", 0))
        unused_port = temp_sock.getsockname()[1]
        temp_sock.close()

        client = TCPClient()
        with pytest.raises((NetPulseConnectionError, NetPulseTimeoutError)) as exc_info:
            client.connect("127.0.0.1", unused_port, timeout=1.0)

        assert not client.is_connected

    def test_tcp_connection_timeout(self) -> None:
        """Test timeout handling when connecting to a non-routable IP address."""
        client = TCPClient()
        # 192.0.2.1 is TEST-NET-1 (RFC 5737), which blackholes packets
        start = time.perf_counter()
        with pytest.raises((NetPulseTimeoutError, NetPulseConnectionError)):
            client.connect("192.0.2.1", 54321, timeout=0.5)

        elapsed = time.perf_counter() - start
        assert elapsed < 3.0  # Must fail fast according to configured timeout
        assert not client.is_connected

    def test_tcp_receive_timeout_on_silent_server(self) -> None:
        """Test timeout handling when server connects but sends no data."""
        # Handler that accepts connection but never responds
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

    def test_tcp_connection_close_state(self, tcp_server: TCPServer) -> None:
        """Test that closing client transitions state and prevents further sends."""
        client = TCPClient()
        client.connect(tcp_server.host, tcp_server.port, timeout=2.0)
        assert client.is_connected

        client.close()
        assert not client.is_connected
        assert_tcp_state(client.state, ConnectionState.CLOSED)

        # Attempting to send after close must raise ConnectionError
        with pytest.raises(NetPulseConnectionError):
            client.send(b"data after close")

    def test_tcp_server_unavailable(self) -> None:
        """Test connecting to a server that has been shut down."""
        server = TCPServer(host="127.0.0.1", port=0)
        server.start()
        port = server.port
        server.stop()  # Shut down immediately

        client = TCPClient()
        with pytest.raises((NetPulseConnectionError, NetPulseTimeoutError)):
            client.connect("127.0.0.1", port, timeout=1.0)

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
