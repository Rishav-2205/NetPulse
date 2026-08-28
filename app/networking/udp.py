"""
NetPulse UDP Networking Engine.

Provides UDPClient for datagram transmission, response validation, timeout handling,
and UDPServer for local testing with simulated packet drops and custom response handlers.
"""

import random
import socket
import threading
import time
from typing import Callable, Optional, Tuple

from app.core.exceptions import (
    ConnectionError as NetPulseConnectionError,
    TimeoutError as NetPulseTimeoutError,
    PacketValidationError,
    ServerLifecycleError,
)
from app.core.logging import get_logger
from app.networking.connection import SocketOptions
from app.networking.sockets import create_udp_socket, safe_close

logger = get_logger("udp")


class UDPClient:
    """
    UDP Client for sending datagrams, receiving responses, and validating packet integrity.
    """

    def __init__(self, options: Optional[SocketOptions] = None):
        self.options = options or SocketOptions()
        self.sock: Optional[socket.socket] = None
        self.bytes_sent = 0
        self.bytes_received = 0
        self.packets_sent = 0
        self.packets_received = 0
        self._init_socket()

    def _init_socket(self) -> None:
        """Initialize or recreate the UDP socket."""
        if self.sock is not None:
            safe_close(self.sock)
        self.sock = create_udp_socket(self.options)

    def send_datagram(self, data: bytes, host: str, port: int) -> int:
        """Send a single UDP datagram to host:port."""
        if self.sock is None:
            self._init_socket()
        assert self.sock is not None

        try:
            sent = self.sock.sendto(data, (host, port))
            self.bytes_sent += sent
            self.packets_sent += 1
            logger.debug(f"Sent {sent}B UDP datagram to {host}:{port}")
            return sent
        except socket.timeout as e:
            raise NetPulseTimeoutError(f"UDP send to {host}:{port} timed out") from e
        except OSError as e:
            raise NetPulseConnectionError(
                f"UDP send to {host}:{port} failed: {e}",
                host=host,
                port=port,
                details={"os_error": str(e)}
            ) from e

    def receive_datagram(self, buffer_size: int = 65535, timeout: Optional[float] = None) -> Tuple[bytes, Tuple[str, int]]:
        """Receive a datagram and return (data, (sender_host, sender_port))."""
        if self.sock is None:
            self._init_socket()
        assert self.sock is not None

        effective_timeout = timeout if timeout is not None else self.options.timeout
        self.sock.settimeout(effective_timeout)

        try:
            data, sender = self.sock.recvfrom(buffer_size)
            self.bytes_received += len(data)
            self.packets_received += 1
            return data, sender
        except socket.timeout as e:
            raise NetPulseTimeoutError(
                f"UDP receive timed out after {effective_timeout}s",
                timeout_seconds=effective_timeout
            ) from e
        except OSError as e:
            raise NetPulseConnectionError(f"UDP receive failed: {e}") from e

    def send_and_receive(
        self,
        data: bytes,
        host: str,
        port: int,
        timeout: Optional[float] = None,
        validate_echo: bool = False
    ) -> bytes:
        """Send a datagram and wait for a response, optionally verifying echo integrity."""
        self.send_datagram(data, host, port)
        response_data, _ = self.receive_datagram(timeout=timeout)

        if validate_echo and response_data != data:
            raise PacketValidationError(
                f"UDP response mismatch: expected {len(data)} bytes, received {len(response_data)} bytes",
                expected=data,
                actual=response_data
            )

        return response_data

    def close(self) -> None:
        """Close the UDP socket."""
        safe_close(self.sock)
        self.sock = None

    def __enter__(self) -> "UDPClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class UDPServer:
    """
    Lightweight, thread-safe UDP test server with echo support and simulated packet drop rate.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,  # 0 binds to ephemeral port
        handler: Optional[Callable[[bytes, Tuple[str, int]], Optional[bytes]]] = None,
        packet_drop_rate: float = 0.0,
        delay_seconds: float = 0.0
    ):
        self.host = host
        self.requested_port = port
        self.port: int = port
        self.handler = handler
        self.packet_drop_rate = packet_drop_rate  # Value between 0.0 and 1.0
        self.delay_seconds = delay_seconds

        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._is_running = threading.Event()
        self.received_packets_count = 0
        self.dropped_packets_count = 0
        self.sent_packets_count = 0
        self.total_bytes_received = 0
        self.total_bytes_sent = 0

    @property
    def is_running(self) -> bool:
        return self._is_running.is_set()

    def start(self) -> "UDPServer":
        """Start the UDP server in a background thread."""
        if self.is_running:
            return self

        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind((self.host, self.requested_port))
            self.port = self._sock.getsockname()[1]
            self._sock.settimeout(0.5)

            self._is_running.set()
            self._thread = threading.Thread(target=self._listen_loop, daemon=True, name=f"UDPServer-{self.port}")
            self._thread.start()
            logger.info(f"UDPServer started on {self.host}:{self.port}")
            return self
        except Exception as e:
            self.stop()
            raise ServerLifecycleError(f"Failed to start UDPServer on {self.host}:{self.requested_port}: {e}") from e

    def _listen_loop(self) -> None:
        while self._is_running.is_set() and self._sock:
            try:
                data, client_addr = self._sock.recvfrom(65535)
                self.received_packets_count += 1
                self.total_bytes_received += len(data)

                # Simulated packet drop
                if self.packet_drop_rate > 0.0 and random.random() < self.packet_drop_rate:
                    self.dropped_packets_count += 1
                    logger.debug(f"Simulating drop of UDP packet from {client_addr}")
                    continue

                if self.delay_seconds > 0:
                    time.sleep(self.delay_seconds)

                if self.handler:
                    response = self.handler(data, client_addr)
                    if response is not None and self._sock:
                        self._sock.sendto(response, client_addr)
                        self.sent_packets_count += 1
                        self.total_bytes_sent += len(response)
                else:
                    # Default Echo Mode
                    if self._sock:
                        self._sock.sendto(data, client_addr)
                        self.sent_packets_count += 1
                        self.total_bytes_sent += len(data)

            except socket.timeout:
                continue
            except OSError:
                break

    def stop(self) -> None:
        """Stop the UDP server and release resources."""
        self._is_running.clear()
        if self._sock:
            safe_close(self._sock)
            self._sock = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info(f"UDPServer on port {self.port} stopped cleanly")

    def __enter__(self) -> "UDPServer":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False
