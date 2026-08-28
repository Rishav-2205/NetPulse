"""
NetPulse Reusable Pytest Fixtures.

Provides clean setup, dependency injection, and teardown for network test servers,
HTTP sessions, configurations, and deterministic payload generators.
"""

from typing import Generator
import pytest

from app.core.config import AppConfig, ConfigManager
from app.networking.http import HTTPClient, HTTPServer
from app.networking.tcp import TCPServer
from app.networking.udp import UDPServer
from app.packets.builder import PayloadGenerator
from app.topology.model import NetworkTopology


@pytest.fixture(scope="session")
def network_config() -> AppConfig:
    """Fixture providing loaded NetPulse configuration."""
    return ConfigManager.get_config()


@pytest.fixture
def tcp_server() -> Generator[TCPServer, None, None]:
    """Fixture providing a running, thread-safe TCP echo server on an ephemeral port."""
    server = TCPServer(host="127.0.0.1", port=0)
    server.start()
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture
def udp_server() -> Generator[UDPServer, None, None]:
    """Fixture providing a running, thread-safe UDP echo server on an ephemeral port."""
    server = UDPServer(host="127.0.0.1", port=0)
    server.start()
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture
def http_server() -> Generator[HTTPServer, None, None]:
    """Fixture providing a running embedded HTTP test server on an ephemeral port."""
    server = HTTPServer(host="127.0.0.1", port=0)
    server.start()
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture
def http_session(http_server: HTTPServer) -> Generator[HTTPClient, None, None]:
    """Fixture providing an HTTP client connected to the local test HTTP server."""
    client = HTTPClient(base_url=http_server.url, timeout=5.0)
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
def payload_factory() -> type[PayloadGenerator]:
    """Fixture providing the deterministic payload generator class."""
    return PayloadGenerator


@pytest.fixture
def standard_topology() -> NetworkTopology:
    """Fixture providing a standard Client -> Router -> Server simulated topology."""
    return NetworkTopology.create_standard_three_node()
