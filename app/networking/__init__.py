"""
NetPulse Networking Subsystem.

Provides TCP, UDP, and HTTP client wrappers, socket configuration,
and embedded local test servers.
"""

from app.networking.connection import (
    ConnectionState,
    Endpoint,
    SocketOptions,
)
from app.networking.sockets import (
    create_tcp_socket,
    create_udp_socket,
    configure_socket,
    safe_close,
    ManagedSocket,
)
from app.networking.tcp import (
    TCPClient,
    TCPServer,
)
from app.networking.udp import (
    UDPClient,
    UDPServer,
)
from app.networking.http import (
    HTTPClient,
    HTTPResponse,
    HTTPServer,
)

__all__ = [
    "ConnectionState",
    "Endpoint",
    "SocketOptions",
    "create_tcp_socket",
    "create_udp_socket",
    "configure_socket",
    "safe_close",
    "ManagedSocket",
    "TCPClient",
    "TCPServer",
    "UDPClient",
    "UDPServer",
    "HTTPClient",
    "HTTPResponse",
    "HTTPServer",
]
