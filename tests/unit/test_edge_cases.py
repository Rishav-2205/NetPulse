"""
Unit Tests: Edge Cases, Idempotency & Resiliency.

Validates server lifecycle idempotency, disconnected socket behaviors,
deep config merging, cyclic topology routing, and corrupted baseline recovery.
"""

import os
from pathlib import Path
import socket
import pytest

from app.core.config import ConfigManager, AppConfig
from app.core.exceptions import (
    ConnectionError as NetPulseConnectionError,
    TimeoutError as NetPulseTimeoutError,
    PacketValidationError,
    TopologyError,
)
from app.core.logging import JSONLogFormatter, get_logger
from app.core.result import SuiteResult, TestResult, TestStatus
from app.core.retry import retry, retry_call, calculate_backoff
from app.networking.http import HTTPServer
from app.networking.tcp import TCPClient, TCPServer
from app.networking.udp import UDPServer
from app.packets.builder import PayloadGenerator, PacketBuilder
from app.reporting.results import BaselineManager, BaselineComparisonDiff
from app.topology.model import NetworkTopology, Node, NodeType


@pytest.mark.unit
class TestEdgeCases:
    """Test suite covering critical framework boundary conditions and failure modes."""

    def test_tcp_server_double_start_and_stop_idempotency(self) -> None:
        """Verify that starting or stopping TCPServer multiple times is safe and idempotent."""
        server = TCPServer(host="127.0.0.1", port=0)
        server.start()
        assert server.is_running
        port_first = server.port

        # Second start should be a no-op
        server.start()
        assert server.port == port_first

        # Stop and double stop
        server.stop()
        assert not server.is_running
        server.stop()  # Should not raise
        assert not server.is_running

    def test_udp_server_double_start_and_stop_idempotency(self) -> None:
        """Verify that starting or stopping UDPServer multiple times is safe and idempotent."""
        server = UDPServer(host="127.0.0.1", port=0)
        server.start()
        assert server.is_running

        server.start()  # No-op
        server.stop()
        assert not server.is_running
        server.stop()  # No-op

    def test_http_server_double_start_and_stop_idempotency(self) -> None:
        """Verify that starting or stopping HTTPServer multiple times is safe and idempotent."""
        server = HTTPServer(host="127.0.0.1", port=0)
        server.start()
        assert server.is_running

        server.start()  # No-op
        server.stop()
        assert not server.is_running
        server.stop()  # No-op

    def test_tcp_client_operations_when_disconnected(self) -> None:
        """Verify that attempting send/recv operations on disconnected TCPClient raises ConnectionError."""
        client = TCPClient()
        assert not client.is_connected

        with pytest.raises(NetPulseConnectionError) as exc_send:
            client.send(b"test")
        assert "not connected" in str(exc_send.value)

        with pytest.raises(NetPulseConnectionError) as exc_recv:
            client.receive(1024)
        assert "not connected" in str(exc_recv.value)

    def test_tcp_client_receive_exact_premature_remote_close(self) -> None:
        """Verify receive_exact raises ConnectionError if remote closes connection early."""
        # Handler that sends only 5 bytes then explicitly closes socket
        def short_handler(data: bytes, sock: socket.socket) -> None:
            sock.sendall(b"12345")
            sock.close()
            return None

        server = TCPServer(host="127.0.0.1", port=0, handler=short_handler)
        server.start()
        try:
            with TCPClient() as client:
                client.connect(server.host, server.port, timeout=2.0)
                client.send(b"request")
                with pytest.raises(NetPulseConnectionError) as exc_info:
                    # Expecting 20 bytes but server only sent 5 and closed
                    client.receive_exact(20, timeout=1.0)
                assert "Connection closed prematurely" in str(exc_info.value)
        finally:
            server.stop()

    def test_retry_metadata_preservation(self) -> None:
        """Verify that @retry decorator preserves function docstrings, __name__, and annotations."""
        @retry(max_retries=2)
        def documented_function(x: int) -> int:
            """This is a test docstring."""
            return x * 2

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is a test docstring."
        assert documented_function(5) == 10

    def test_retry_call_helper_with_custom_predicate(self) -> None:
        """Verify retry_call helper works directly with custom predicate."""
        call_count = 0

        def flaky_custom_action() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise CustomTestException("retry me")
            return "DONE"

        class CustomTestException(Exception):
            pass

        result = retry_call(
            flaky_custom_action,
            max_retries=2,
            initial_delay=0.01,
            retry_predicate=lambda e: isinstance(e, CustomTestException)
        )
        assert result == "DONE"
        assert call_count == 2

    def test_topology_cyclic_graph_pathfinding(self) -> None:
        """Verify that BFS pathfinding in a cyclic graph finds the shortest path without looping."""
        topo = NetworkTopology(name="Cyclic Topology")
        # Nodes A - B - C - D, with cross link A - D
        topo.add_node(Node("A", NodeType.CLIENT, "10.0.0.1"))
        topo.add_node(Node("B", NodeType.SWITCH, "10.0.0.2"))
        topo.add_node(Node("C", NodeType.SWITCH, "10.0.0.3"))
        topo.add_node(Node("D", NodeType.SERVER, "10.0.0.4"))

        topo.add_link("A", "B", latency_ms=1.0)
        topo.add_link("B", "C", latency_ms=1.0)
        topo.add_link("C", "D", latency_ms=1.0)
        topo.add_link("A", "D", latency_ms=5.0)  # Direct link (1 hop) vs 3 hops

        path = topo.find_path("A", "D")
        assert len(path) == 1  # Direct 1-hop path chosen by BFS
        assert path[0].node_a.name == "A" or path[0].node_b.name == "A"

    def test_baseline_manager_corrupted_json_recovery(self) -> None:
        """Verify that BaselineManager gracefully handles non-existent or corrupted baseline JSON files."""
        corrupted_file = "reports/corrupted_test_baseline.json"
        Path(corrupted_file).parent.mkdir(parents=True, exist_ok=True)
        with open(corrupted_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json syntax ...")

        try:
            loaded = BaselineManager.load_baseline(corrupted_file)
            assert loaded is None

            suite = SuiteResult()
            diff = BaselineManager.compare_against_baseline(suite, corrupted_file)
            assert isinstance(diff, BaselineComparisonDiff)
            assert not diff.has_regressions
        finally:
            if os.path.exists(corrupted_file):
                os.remove(corrupted_file)

    def test_json_log_formatter_output(self) -> None:
        """Verify that JSONLogFormatter outputs valid JSON with structured contextual fields."""
        import logging
        import json

        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="netpulse.test",
            level=logging.INFO,
            pathname="test_edge_cases.py",
            lineno=100,
            msg="Custom diagnostic log message",
            args=(),
            exc_info=None
        )
        record.protocol = "TCP"
        record.destination = "127.0.0.1:80"
        record.duration_ms = 45.67

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Custom diagnostic log message"
        assert parsed["protocol"] == "TCP"
        assert parsed["destination"] == "127.0.0.1:80"
        assert parsed["duration_ms"] == 45.67
