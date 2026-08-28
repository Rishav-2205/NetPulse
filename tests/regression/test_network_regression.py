"""
Regression Test Suite: Baseline Invariants & Cross-Protocol Network Guarantees.

Validates that critical networking invariants remain intact across code revisions:
1. TCP multi-message ordering and stream boundary guarantees
2. UDP datagram boundary preservation and payload integrity
3. HTTP idempotent method correctness and header guarantees
4. Dynamic baseline comparisons for regression detection
"""

import pytest

from app.core.result import SuiteResult, TestResult, TestStatus
from app.networking.http import HTTPClient
from app.networking.tcp import TCPClient, TCPServer
from app.networking.udp import UDPClient, UDPServer
from app.packets.builder import PayloadGenerator
from app.reporting.results import BaselineManager
from app.testing.assertions import (
    assert_payload_integrity,
    assert_status_code,
)
from app.testing.base_test import BaseNetworkTest
from app.testing.metadata import test_case, TestCategory, ProtocolType, OSI_Layer, TestPriority


@pytest.mark.regression
class TestNetworkRegression(BaseNetworkTest):
    """Regression test suite validating core network behaviors."""

    @test_case(
        test_id="NET-REG-001",
        name="TCP Stream Byte Ordering Invariant",
        category=TestCategory.REGRESSION,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.CRITICAL,
        description="Verify that 20 sequential TCP stream chunks arrive without byte reordering or corruption.",
        expected_behavior="Received concatenated stream matches exact expected chunk order."
    )
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

    @test_case(
        test_id="NET-REG-002",
        name="UDP Datagram Boundary Preservation Invariant",
        category=TestCategory.REGRESSION,
        protocol=ProtocolType.UDP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.CRITICAL,
        description="Verify UDP datagram boundaries are strictly preserved without stream merging or truncation.",
        expected_behavior="Each datagram is delivered as an independent message with exact byte length."
    )
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

    @test_case(
        test_id="NET-REG-003",
        name="HTTP Status Code & Header Invariant",
        category=TestCategory.REGRESSION,
        protocol=ProtocolType.HTTP,
        layer=OSI_Layer.LAYER_7,
        priority=TestPriority.HIGH,
        description="Verify standard HTTP headers, content-type, and status codes remain compliant across runs.",
        expected_behavior="GET /health returns 200 OK and application/json Content-Type."
    )
    def test_regression_http_status_codes_and_headers(self, http_session: HTTPClient) -> None:
        """Regression: Verify HTTP headers and status codes remain compliant."""
        resp = http_session.get("/health")
        assert_status_code(resp.status_code, 200)
        assert resp.headers.get("content-type") == "application/json"
        assert resp.json()["status"] == "ok"

    @test_case(
        test_id="NET-REG-004",
        name="Regression Baseline Diff Engine Invariant",
        category=TestCategory.REGRESSION,
        protocol=ProtocolType.FRAMEWORK,
        layer=OSI_Layer.CROSS_LAYER,
        priority=TestPriority.CRITICAL,
        description="Verify that BaselineManager detects status regressions (PASS -> FAIL) and missing tests.",
        expected_behavior="Regression diff identifies regressions, new tests, and missing tests accurately."
    )
    def test_regression_baseline_diff_engine(self) -> None:
        """Regression: Verify BaselineManager accurately flags regressions against previous runs."""
        baseline_suite = SuiteResult(suite_name="Historical Baseline")
        baseline_suite.add_result(TestResult("test_alpha", "TCP", TestStatus.PASS, 12.0))
        baseline_suite.add_result(TestResult("test_beta", "UDP", TestStatus.PASS, 5.0))
        baseline_suite.add_result(TestResult("test_gamma", "HTTP", TestStatus.PASS, 20.0))

        temp_baseline_path = "reports/temp_test_baseline.json"
        BaselineManager.save_baseline(baseline_suite, filepath=temp_baseline_path)

        current_results = [
            TestResult("test_alpha", "TCP", TestStatus.PASS, 14.0),
            TestResult("test_beta", "UDP", TestStatus.FAIL, 5.0, error="Simulated Regression"),
            TestResult("test_delta", "HTTP", TestStatus.PASS, 8.0)
        ]

        diff = BaselineManager.compare_with_baseline(current_results, baseline_filepath=temp_baseline_path)

        assert diff.has_regressions is True
        assert len(diff.status_regressions) == 1
        assert diff.status_regressions[0]["test_name"] == "test_beta"
        assert "test_delta" in diff.new_tests
        assert "test_gamma" in diff.missing_tests
