"""
NetPulse Connection Abstraction.

Represents endpoints, connection states, and socket options.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class ConnectionState(str, Enum):
    """Lifecycle state of a network connection."""
    IDLE = "IDLE"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class Endpoint:
    """Represents a network host and port destination."""
    host: str
    port: int

    @property
    def address_tuple(self) -> Tuple[str, int]:
        return (self.host, self.port)

    def __str__(self) -> str:
        return f"{self.host}:{self.port}"


@dataclass
class SocketOptions:
    """Socket configuration options."""
    so_reuseaddr: bool = True
    tcp_nodelay: bool = True
    so_rcvbuf: Optional[int] = None
    so_sndbuf: Optional[int] = None
    timeout: Optional[float] = 5.0
    so_broadcast: bool = False
