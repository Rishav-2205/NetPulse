"""
Regression Test Suite: Baseline Invariants & Cross-Protocol Network Guarantees.

Validates that critical networking invariants remain intact across code revisions:
1. TCP multi-message ordering and stream boundary guarantees
2. UDP datagram boundary preservation and payload integrity
3. HTTP idempotent method correctness and header guarantees
4. Dynamic baseline comparisons for regression detection
"""

import pytest

from app.core.exceptions import ConnectionError as NetPulseConnectionError
from app.core.result import SuiteResult, TestResult, TestStatus
from app.networking.http import HTTPClient, HTTPServer
from app.networking.tcp import TCPClient, TCPServer
from app.networking.udp import UDPClient, UDPServer
from app.packets.builder import PayloadGenerator
from app.reporting.results import BaselineManager
from app.testing.assertions import (
    assert_payload_integrity,
    assert_status_code,
    assert_tcp_state,
)
from app.testing.base_test import BaseNetworkTest


@pytest.mark.regression
class TestNetworkRegression(BaseNetworkTest):
    """Regression test suite validating core network behaviors."""

    def test_regression_tcp_stream_ordering(self, tcp_server: TCPServer) -> None:
        """Regression: Verify that TCP sequence order and boundary integrity are preserved."""
        payload_chunks = [f"CHUNK_{i:04d}_DATA_".encode("utf-8") * 4 for i in range(20)]
        expected_full_stream = b"".join(payload_chunks)

        with TCPClient() as client:
            client.connect(tcp_server.host, tcp_server.port, timeout=3.0)
            for chunk in payload_chunks:
                client.send_all(chunk)

            received = client.receive_exact(len(expected_full_stream), timeout=3.0)
            assert_payload_integrity(received, expected_full_stream)

    def test_regression_udp_datagram_boundary(self, udp_server: UDPServer, payload_factory: type[PayloadGenerator]) -> None:
        """Regression: Verify UDP datagram boundaries are preserved (no concatenation)."""
        payload_1 = payload_factory.generate_random(64, seed=10)
        payload_2 = payload_factory.generate_random(128, seed=20)

        with UDPClient() as client:
            resp_1 = client.send_and_receive(payload_1, udp_server.host, udp_server.port, timeout=2.0)
            resp_2 = client.send_and_receive(payload_2, udp_server.host, udp_server.port, timeout=2.0)

            assert len(resp_1) == 64
            assert len(resp_2) == 128
            assert resp_1 == payload_1
            assert resp_2 == payload_2

    def test_regression_http_status_codes_and_headers(self, http_session: HTTPClient) -> None:
        """Regression: Verify HTTP headers and status codes remain compliant."""
        resp = http_session.get("/get", params={"reg_test": "true"})
        assert_status_code(resp.status_code, 200)
        assert resp.headers.get("content-type") == "application/json"
        data = resp.json()
        assert data["args"]["reg_test"] == ["true"]

    def test_regression_baseline_diff_engine(self) -> None:
        """Regression: Validate the baseline diff calculation engine."""
        suite = SuiteResult(suite_name="Regression Test Baseline Check")
        suite.add_result(TestResult("test_tcp_ok", "TCP", TestStatus.PASS, duration_ms=10.0))
        suite.add_result(TestResult("test_udp_ok", "UDP", TestStatus.PASS, duration_ms=5.0))

        # Check self-diff has zero regressions
        temp_baseline = "reports/temp_test_baseline.json"
        try:
            BaselineManager.save_baseline(suite, temp_baseline)
            diff = BaselineManager.compare_against_baseline(suite, temp_baseline)

            assert not diff.has_regressions
            assert len(diff.status_regressions) == 0
            assert len(diff.missing_tests) == 0
            assert len(diff.new_tests) == 0
        finally:
            import os
            if os.path.exists(temp_baseline):
                os.remove(temp_baseline)
