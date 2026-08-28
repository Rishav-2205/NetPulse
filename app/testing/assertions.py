"""
NetPulse Custom Domain Assertions.

Provides expressive, informative network assertion helpers with detailed diagnostic failure messages.
"""

from typing import Dict, Optional

from app.core.exceptions import PacketValidationError
from app.networking.connection import ConnectionState


def assert_latency_within(
    actual_latency_ms: float,
    max_latency_ms: float,
    min_latency_ms: float = 0.0,
    msg: Optional[str] = None
) -> None:
    """Assert that measured network latency is within the acceptable lower and upper bounds."""
    if not (min_latency_ms <= actual_latency_ms <= max_latency_ms):
        detail = msg or f"Latency out of expected bounds: {actual_latency_ms:.2f}ms is not within [{min_latency_ms:.2f}ms, {max_latency_ms:.2f}ms]"
        raise AssertionError(detail)


def assert_payload_integrity(
    actual_data: bytes,
    expected_data: bytes,
    msg: Optional[str] = None
) -> None:
    """Assert byte-for-byte exact equality between sent and received payloads."""
    if actual_data != expected_data:
        err_msg = msg or (
            f"Payload integrity validation failed: "
            f"expected {len(expected_data)} bytes (prefix: {expected_data[:16]!r}), "
            f"got {len(actual_data)} bytes (prefix: {actual_data[:16]!r})"
        )
        raise PacketValidationError(err_msg, expected=expected_data, actual=actual_data)


def assert_tcp_state(
    actual_state: ConnectionState,
    expected_state: ConnectionState,
    msg: Optional[str] = None
) -> None:
    """Assert that a TCP connection is in the expected lifecycle state."""
    if actual_state != expected_state:
        raise AssertionError(
            msg or f"Expected TCP connection state '{expected_state.value}', but found '{actual_state.value}'"
        )


def assert_status_code(
    actual_status: int,
    expected_status: int,
    response_body: Optional[str] = None
) -> None:
    """Assert HTTP response status code matches expectation."""
    if actual_status != expected_status:
        body_snippet = f" Body: {response_body[:200]}" if response_body else ""
        raise AssertionError(
            f"Expected HTTP status code {expected_status}, but received {actual_status}.{body_snippet}"
        )


def assert_packet_loss_rate(
    sent_count: int,
    received_count: int,
    max_loss_pct: float,
    msg: Optional[str] = None
) -> None:
    """Assert that packet loss percentage does not exceed maximum allowable threshold."""
    if sent_count <= 0:
        raise ValueError("sent_count must be greater than zero")

    lost_count = sent_count - received_count
    actual_loss_pct = (lost_count / sent_count) * 100.0

    if actual_loss_pct > max_loss_pct:
        raise AssertionError(
            msg or f"Packet loss rate {actual_loss_pct:.2f}% ({lost_count}/{sent_count}) exceeded max limit {max_loss_pct:.2f}%"
        )


def assert_header_present(
    headers: Dict[str, str],
    header_name: str,
    expected_value: Optional[str] = None
) -> None:
    """Assert that an HTTP header exists (case-insensitively) and optionally matches a value."""
    normalized = {k.lower(): v for k, v in headers.items()}
    target = header_name.lower()

    if target not in normalized:
        raise AssertionError(f"Expected header '{header_name}' was not found in response headers: {list(headers.keys())}")

    if expected_value is not None and normalized[target] != expected_value:
        raise AssertionError(
            f"Header '{header_name}' value mismatch: expected '{expected_value}', got '{normalized[target]}'"
        )
