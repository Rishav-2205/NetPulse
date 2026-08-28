"""
Functional Tests: HTTP Networking Engine.

Validates HTTP verbs (GET, POST), status code validation, response time measurement,
headers inspection, JSON serialization, timeout enforcement, and 404 handling.
"""

import time
import pytest

from app.core.exceptions import (
    ConnectionError as NetPulseConnectionError,
    TimeoutError as NetPulseTimeoutError,
    PacketValidationError,
)
from app.networking.http import HTTPClient, HTTPServer, HTTPResponse
from app.testing.assertions import (
    assert_status_code,
    assert_latency_within,
    assert_header_present,
)
from app.testing.base_test import BaseNetworkTest


@pytest.mark.http
@pytest.mark.functional
class TestHTTPFunctional(BaseNetworkTest):
    """Test suite covering HTTP protocol validation."""

    def test_http_get_request(self, http_session: HTTPClient) -> None:
        """Test sending a standard HTTP GET request."""
        resp = http_session.get("/health")
        assert_status_code(resp.status_code, 200)
        data = resp.json()
        assert data["status"] == "ok"
        assert_header_present(resp.headers, "X-Server", "NetPulse-Mock-HTTP")

    def test_http_get_query_params(self, http_session: HTTPClient) -> None:
        """Test GET request with query parameters and verify response parsing."""
        resp = http_session.get("/get", params={"service": "network", "probe_id": "99"})
        assert_status_code(resp.status_code, 200)
        data = resp.json()
        assert data["args"]["service"] == ["network"]
        assert data["args"]["probe_id"] == ["99"]

    def test_http_post_json_payload(self, http_session: HTTPClient) -> None:
        """Test HTTP POST with JSON body and verify deserialization."""
        request_body = {"node_id": 42, "status": "ONLINE", "metrics": {"loss": 0.0, "latency_ms": 1.2}}
        resp = http_session.post("/post", json_data=request_body)

        assert_status_code(resp.status_code, 200)
        resp_data = resp.json()
        assert resp_data["method"] == "POST"
        assert resp_data["json"] == request_body

    def test_http_status_code_validation(self, http_session: HTTPClient) -> None:
        """Test handling and asserting various HTTP status codes."""
        test_cases = [200, 201, 400, 403, 500]
        for expected_code in test_cases:
            resp = http_session.get(f"/status/{expected_code}")
            assert_status_code(resp.status_code, expected_code)

    def test_http_response_time_measurement(self, http_session: HTTPClient) -> None:
        """Test that round-trip duration is measured accurately."""
        resp = http_session.get("/json")
        assert resp.duration_ms > 0.0
        assert_latency_within(resp.duration_ms, max_latency_ms=100.0)

    def test_http_custom_headers_propagation(self, http_session: HTTPClient) -> None:
        """Test that custom request headers are sent and reflected by the server."""
        custom_headers = {"X-NetPulse-Trace": "trace-xyz-12345", "X-Custom-Client": "v1.0"}
        resp = http_session.get("/headers", headers=custom_headers)

        assert_status_code(resp.status_code, 200)
        reflected = resp.json()
        assert reflected.get("X-Netpulse-Trace") == "trace-xyz-12345" or reflected.get("X-NetPulse-Trace") == "trace-xyz-12345"

    def test_http_malformed_or_nonexistent_endpoint(self, http_session: HTTPClient) -> None:
        """Test requesting a non-existent URL endpoint returns 404."""
        resp = http_session.get("/api/v1/non_existent_route")
        assert_status_code(resp.status_code, 404)
        data = resp.json()
        assert data["error"] == "Not Found"

    def test_http_client_timeout(self, http_session: HTTPClient) -> None:
        """Test client-side timeout enforcement when server endpoint exceeds timeout limit."""
        # Endpoint delays 1.5 seconds, client times out at 0.3 seconds
        with pytest.raises(NetPulseTimeoutError) as exc_info:
            http_session.get("/delay/1.5", timeout=0.3)

        assert "timed out" in str(exc_info.value)
