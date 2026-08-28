"""
NetPulse TCP Networking Engine.

Provides high-level TCPClient with chunking, timeout management, and error translation,
along with a lightweight, multi-threaded local TCPServer for reproducible offline testing.
"""

import socket
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.exceptions import (
    ConnectionError as NetPulseConnectionError,
    TimeoutError as NetPulseTimeoutError,
    SocketError,
    ServerLifecycleError,
)
from app.core.logging import get_logger
from app.networking.connection import ConnectionState, Endpoint, SocketOptions
from app.networking.sockets import create_tcp_socket, safe_close

logger = get_logger("tcp")


class TCPClient:
    """
    Robust TCP Client supporting streaming, chunked transfers, and precise timeouts.
    """

    def __init__(self, options: Optional[SocketOptions] = None):
        self.options = options or SocketOptions()
        self.sock: Optional[socket.socket] = None
        self.state = ConnectionState.IDLE
        self.endpoint: Optional[Endpoint] = None
        self.bytes_sent = 0
        self.bytes_received = 0

    @property
    def is_connected(self) -> bool:
        return self.state == ConnectionState.CONNECTED and self.sock is not None

    def connect(self, host: str, port: int, timeout: Optional[float] = None) -> None:
        """Establish a TCP connection to the specified host and port."""
        self.endpoint = Endpoint(host, port)
        self.state = ConnectionState.CONNECTING
        effective_timeout = timeout if timeout is not None else self.options.timeout

        try:
            self.sock = create_tcp_socket(self.options)
            if effective_timeout is not None:
                self.sock.settimeout(effective_timeout)

            logger.debug(f"Connecting to {self.endpoint} (timeout={effective_timeout}s)...")
            self.sock.connect((host, port))
            self.state = ConnectionState.CONNECTED
            logger.info(f"Connected to {self.endpoint}", extra={"protocol": "TCP", "destination": str(self.endpoint), "status": "CONNECTED"})
        except socket.timeout as e:
            self.state = ConnectionState.FAILED
            safe_close(self.sock)
            self.sock = None
            raise NetPulseTimeoutError(
                f"Connection to {host}:{port} timed out after {effective_timeout}s",
                timeout_seconds=effective_timeout,
                details={"host": host, "port": port}
            ) from e
        except OSError as e:
            self.state = ConnectionState.FAILED
            safe_close(self.sock)
            self.sock = None
            raise NetPulseConnectionError(
                f"Failed to connect to {host}:{port}: {e}",
                host=host,
                port=port,
                details={"os_error": str(e), "errno": getattr(e, "errno", None)}
            ) from e

    def send(self, data: bytes) -> int:
        """Send data through the connected socket."""
        if not self.is_connected or self.sock is None:
            raise NetPulseConnectionError("Cannot send data: socket is not connected")

        try:
            sent = self.sock.send(data)
            self.bytes_sent += sent
            return sent
        except socket.timeout as e:
            raise NetPulseTimeoutError("Socket timed out during send operation") from e
        except OSError as e:
            self.state = ConnectionState.FAILED
            raise NetPulseConnectionError(f"Socket send failed: {e}") from e

    def send_all(self, data: bytes) -> None:
        """Send all data through the connected socket."""
        if not self.is_connected or self.sock is None:
            raise NetPulseConnectionError("Cannot send data: socket is not connected")

        try:
            self.sock.sendall(data)
            self.bytes_sent += len(data)
        except socket.timeout as e:
            raise NetPulseTimeoutError("Socket timed out during sendall operation") from e
        except OSError as e:
            self.state = ConnectionState.FAILED
            raise NetPulseConnectionError(f"Socket sendall failed: {e}") from e

    def receive(self, buffer_size: int = 4096, timeout: Optional[float] = None) -> bytes:
        """Receive up to buffer_size bytes from the socket."""
        if not self.is_connected or self.sock is None:
            raise NetPulseConnectionError("Cannot receive data: socket is not connected")

        try:
            if timeout is not None:
                self.sock.settimeout(timeout)
            data = self.sock.recv(buffer_size)
            if not data:
                # Remote end closed connection
                self.state = ConnectionState.CLOSED
            self.bytes_received += len(data)
            return data
        except socket.timeout as e:
            raise NetPulseTimeoutError(f"Socket receive timed out after {timeout or self.options.timeout}s") from e
        except OSError as e:
            self.state = ConnectionState.FAILED
            raise NetPulseConnectionError(f"Socket receive failed: {e}") from e

    def receive_exact(self, length: int, timeout: Optional[float] = None) -> bytes:
        """Receive exactly length bytes from the stream, buffering chunks."""
        chunks: List[bytes] = []
        bytes_left = length
        start_time = time.monotonic()

        while bytes_left > 0:
            if timeout is not None:
                elapsed = time.monotonic() - start_time
                remaining_timeout = timeout - elapsed
                if remaining_timeout <= 0:
                    raise NetPulseTimeoutError(f"receive_exact timed out waiting for {length} bytes")
            else:
                remaining_timeout = None

            chunk = self.receive(buffer_size=min(bytes_left, 4096), timeout=remaining_timeout)
            if not chunk:
                break
            chunks.append(chunk)
            bytes_left -= len(chunk)

        result = b"".join(chunks)
        if len(result) < length:
            raise NetPulseConnectionError(f"Connection closed prematurely: expected {length} bytes, got {len(result)}")
        return result

    def close(self) -> None:
        """Close the active connection gracefully."""
        self.state = ConnectionState.CLOSING
        safe_close(self.sock)
        self.sock = None
        self.state = ConnectionState.CLOSED

    def __enter__(self) -> "TCPClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class TCPServer:
    """
    Lightweight, thread-safe TCP test server with echo support and custom handlers.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,  # 0 binds to an ephemeral OS port
        handler: Optional[Callable[[bytes, socket.socket], Optional[bytes]]] = None,
        delay_seconds: float = 0.0
    ):
        self.host = host
        self.requested_port = port
        self.port: int = port
        self.handler = handler
        self.delay_seconds = delay_seconds

        self._server_sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._is_running = threading.Event()
        self._client_threads: List[threading.Thread] = []
        self.total_connections = 0
        self.total_bytes_received = 0
        self.total_bytes_sent = 0

    @property
    def is_running(self) -> bool:
        return self._is_running.is_set()

    def start(self) -> "TCPServer":
        """Start the TCP server in a background thread."""
        if self.is_running:
            return self

        try:
            self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_sock.bind((self.host, self.requested_port))
            self.port = self._server_sock.getsockname()[1]
            self._server_sock.listen(128)
            self._server_sock.settimeout(0.5)

            self._is_running.set()
            self._thread = threading.Thread(target=self._accept_loop, daemon=True, name=f"TCPServer-{self.port}")
            self._thread.start()
            logger.info(f"TCPServer started on {self.host}:{self.port}")
            return self
        except Exception as e:
            self.stop()
            raise ServerLifecycleError(f"Failed to start TCPServer on {self.host}:{self.requested_port}: {e}") from e

    def _accept_loop(self) -> None:
        while self._is_running.is_set() and self._server_sock:
            try:
                client_sock, client_addr = self._server_sock.accept()
                self.total_connections += 1
                t = threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, client_addr),
                    daemon=True,
                    name=f"TCPClientHandler-{client_addr}"
                )
                self._client_threads.append(t)
                t.start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _handle_client(self, client_sock: socket.socket, client_addr: Tuple[str, int]) -> None:
        with client_sock:
            client_sock.settimeout(1.0)
            while self._is_running.is_set():
                try:
                    data = client_sock.recv(4096)
                    if not data:
                        break

                    self.total_bytes_received += len(data)

                    if self.delay_seconds > 0:
                        time.sleep(self.delay_seconds)

                    if self.handler:
                        response = self.handler(data, client_sock)
                        if response is not None:
                            client_sock.sendall(response)
                            self.total_bytes_sent += len(response)
                    else:
                        # Default Echo Mode
                        client_sock.sendall(data)
                        self.total_bytes_sent += len(data)
                except socket.timeout:
                    continue
                except (OSError, ConnectionError):
                    break

    def stop(self) -> None:
        """Stop the TCP server and release all resources."""
        self._is_running.clear()
        if self._server_sock:
            safe_close(self._server_sock)
            self._server_sock = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        for t in self._client_threads:
            if t.is_alive():
                t.join(timeout=0.5)
        self._client_threads.clear()
        logger.info(f"TCPServer on port {self.port} stopped cleanly")

    def __enter__(self) -> "TCPServer":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False
