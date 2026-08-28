"""
Functional Tests: HTTP Networking Engine.

Validates HTTP verbs (GET, POST), status code validation, response time measurement,
headers inspection, JSON serialization, timeout enforcement, and 404 handling.
"""

import pytest

from app.core.exceptions import TimeoutError as NetPulseTimeoutError
from app.networking.http import HTTPClient
from app.testing.assertions import (
    assert_status_code,
    assert_latency_within,
    assert_header_present,
)
from app.testing.base_test import BaseNetworkTest
from app.testing.metadata import test_case, TestCategory, ProtocolType, OSI_Layer, TestPriority


@pytest.mark.http
@pytest.mark.functional
class TestHTTPFunctional(BaseNetworkTest):
    """Test suite covering HTTP protocol validation."""

    @test_case(
        test_id="NET-HTTP-001",
        name="HTTP GET Health Probe",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.HTTP,
        layer=OSI_Layer.LAYER_7,
        priority=TestPriority.CRITICAL,
        description="Verify HTTP GET request against /health returning 200 OK and JSON payload.",
        expected_behavior="Status code is 200, status is ok, and custom server header is present."
    )
    def test_http_get_request(self, http_session: HTTPClient) -> None:
        """Test sending a standard HTTP GET request."""
        resp = http_session.get("/health")
        assert_status_code(resp.status_code, 200)
        data = resp.json()
        assert data["status"] == "ok"
        assert_header_present(resp.headers, "X-Server", "NetPulse-Mock-HTTP")

    @test_case(
        test_id="NET-HTTP-002",
        name="HTTP Query Parameter Parsing",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.HTTP,
        layer=OSI_Layer.LAYER_7,
        priority=TestPriority.HIGH,
        description="Verify GET query parameter encoding and server reflection.",
        expected_behavior="Returned JSON structure reflects parsed query parameter dictionary."
    )
    def test_http_get_query_params(self, http_session: HTTPClient) -> None:
        """Test GET request with query parameters and verify response parsing."""
        resp = http_session.get("/get", params={"service": "network", "probe_id": "99"})
        assert_status_code(resp.status_code, 200)
        data = resp.json()
        assert data["args"]["service"] == ["network"]
        assert data["args"]["probe_id"] == ["99"]

    @test_case(
        test_id="NET-HTTP-003",
        name="HTTP POST JSON Transmission",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.HTTP,
        layer=OSI_Layer.LAYER_7,
        priority=TestPriority.CRITICAL,
        description="Verify HTTP POST with nested JSON payload serialization and response echo.",
        expected_behavior="Server deserializes JSON body and echoes identical payload structure."
    )
    def test_http_post_json_payload(self, http_session: HTTPClient) -> None:
        """Test HTTP POST with JSON body and verify deserialization."""
        request_body = {"node_id": 42, "status": "ONLINE", "metrics": {"loss": 0.0, "latency_ms": 1.2}}
        resp = http_session.post("/post", json_data=request_body)

        assert_status_code(resp.status_code, 200)
        resp_data = resp.json()
        assert resp_data["method"] == "POST"
        assert resp_data["json"] == request_body

    @test_case(
        test_id="NET-HTTP-004",
        name="HTTP Status Code Assertions",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.HTTP,
        layer=OSI_Layer.LAYER_7,
        priority=TestPriority.HIGH,
        description="Verify assertion engine across 200, 201, 400, 403, and 500 status codes.",
        expected_behavior="Each mock status endpoint returns its designated HTTP status code."
    )
    def test_http_status_code_validation(self, http_session: HTTPClient) -> None:
        """Test handling and asserting various HTTP status codes."""
        test_cases = [200, 201, 400, 403, 500]
        for expected_code in test_cases:
            resp = http_session.get(f"/status/{expected_code}")
            assert_status_code(resp.status_code, expected_code)

    @test_case(
        test_id="NET-HTTP-005",
        name="HTTP Response Latency Measurement",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.HTTP,
        layer=OSI_Layer.LAYER_7,
        priority=TestPriority.HIGH,
        description="Verify microsecond-level response duration measurement on HTTP client.",
        expected_behavior="Recorded duration_ms is positive and within acceptable threshold."
    )
    def test_http_response_time_measurement(self, http_session: HTTPClient) -> None:
        """Test that round-trip duration is measured accurately."""
        resp = http_session.get("/json")
        assert resp.duration_ms > 0.0
        assert_latency_within(resp.duration_ms, max_latency_ms=100.0)

    @test_case(
        test_id="NET-HTTP-006",
        name="HTTP Custom Headers Propagation",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.HTTP,
        layer=OSI_Layer.LAYER_7,
        priority=TestPriority.MEDIUM,
        description="Verify custom request headers are transmitted and echoed by server.",
        expected_behavior="Reflected header dictionary contains custom trace IDs."
    )
    def test_http_custom_headers_propagation(self, http_session: HTTPClient) -> None:
        """Test that custom request headers are sent and reflected by the server."""
        custom_headers = {"X-NetPulse-Trace": "trace-xyz-12345", "X-Custom-Client": "v1.0"}
        resp = http_session.get("/headers", headers=custom_headers)

        assert_status_code(resp.status_code, 200)
        reflected = resp.json()
        assert reflected.get("X-Netpulse-Trace") == "trace-xyz-12345" or reflected.get("X-NetPulse-Trace") == "trace-xyz-12345"

    @test_case(
        test_id="NET-HTTP-007",
        name="HTTP 404 Endpoint Not Found",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.HTTP,
        layer=OSI_Layer.LAYER_7,
        priority=TestPriority.MEDIUM,
        description="Verify request to undefined endpoint returns 404 Not Found.",
        expected_behavior="Status code 404 returned with structured JSON error."
    )
    def test_http_malformed_or_nonexistent_endpoint(self, http_session: HTTPClient) -> None:
        """Test requesting a non-existent URL endpoint returns 404."""
        resp = http_session.get("/api/v1/non_existent_route")
        assert_status_code(resp.status_code, 404)
        data = resp.json()
        assert data["error"] == "Not Found"

    @test_case(
        test_id="NET-HTTP-008",
        name="HTTP Client Timeout Enforcement",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.HTTP,
        layer=OSI_Layer.LAYER_7,
        priority=TestPriority.HIGH,
        description="Verify client-side timeout aborts when server delay exceeds configured threshold.",
        expected_behavior="TimeoutError raised promptly when server delay exceeds 0.3s."
    )
    def test_http_client_timeout(self, http_session: HTTPClient) -> None:
        """Test client-side timeout enforcement when server endpoint exceeds timeout limit."""
        with pytest.raises(NetPulseTimeoutError) as exc_info:
            http_session.get("/delay/1.5", timeout=0.3)

        assert "timed out" in str(exc_info.value)
