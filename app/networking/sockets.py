"""
NetPulse Socket Factory and Low-Level Socket Management.

Provides resilient socket lifecycle helpers, socket option tuning,
and clean context management.
"""

import socket
import sys
from typing import Optional, Tuple

from app.core.exceptions import SocketError
from app.core.logging import get_logger
from app.networking.connection import SocketOptions

logger = get_logger("sockets")


def create_tcp_socket(options: Optional[SocketOptions] = None) -> socket.socket:
    """Create and configure a TCP streaming socket."""
    opts = options or SocketOptions()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        configure_socket(sock, opts, is_tcp=True)
        return sock
    except Exception as e:
        raise SocketError(f"Failed to create TCP socket: {e}") from e


def create_udp_socket(options: Optional[SocketOptions] = None) -> socket.socket:
    """Create and configure a UDP datagram socket."""
    opts = options or SocketOptions()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        configure_socket(sock, opts, is_tcp=False)
        return sock
    except Exception as e:
        raise SocketError(f"Failed to create UDP socket: {e}") from e


def configure_socket(sock: socket.socket, options: SocketOptions, is_tcp: bool = True) -> None:
    """Apply socket options such as timeouts, buffers, and reuse flags."""
    try:
        if options.so_reuseaddr:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # SO_REUSEPORT if available on POSIX
        if hasattr(socket, "SO_REUSEPORT") and options.so_reuseaddr:
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except (AttributeError, OSError):
                pass

        if is_tcp and options.tcp_nodelay:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        if options.so_rcvbuf is not None:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, options.so_rcvbuf)

        if options.so_sndbuf is not None:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, options.so_sndbuf)

        if options.so_broadcast and not is_tcp:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        if options.timeout is not None:
            sock.settimeout(options.timeout)

    except Exception as e:
        raise SocketError(f"Failed to configure socket options: {e}") from e


def safe_close(sock: Optional[socket.socket]) -> None:
    """Safely shut down and close a socket without throwing exceptions."""
    if sock is None:
        return
    try:
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        sock.close()
    except Exception as e:
        logger.debug(f"Error while closing socket: {e}")


class ManagedSocket:
    """
    Context manager that guarantees clean socket closure and error mapping.
    """

    def __init__(self, sock: socket.socket):
        self.sock = sock

    def __enter__(self) -> socket.socket:
        return self.sock

    def __exit__(self, exc_type, exc_val, exc_tb):
        safe_close(self.sock)
        return False
