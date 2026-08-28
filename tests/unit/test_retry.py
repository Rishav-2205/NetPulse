"""
Unit Tests: Retry Engine & Error Classification.
"""

import pytest

from app.core.exceptions import (
    TimeoutError as NetPulseTimeoutError,
    PacketValidationError,
    RetryExhaustedError,
)
from app.core.retry import (
    retry,
    is_transient_network_error,
    calculate_backoff,
)


@pytest.mark.unit
class TestRetryEngine:
    """Test suite covering transient retry logic and deterministic exception handling."""

    def test_transient_error_classification(self) -> None:
        """Test accurate classification of transient vs deterministic exceptions."""
        assert is_transient_network_error(NetPulseTimeoutError("timeout")) is True
        assert is_transient_network_error(ConnectionRefusedError("refused")) is True
        assert is_transient_network_error(PacketValidationError("corrupted")) is False
        assert is_transient_network_error(ValueError("bad value")) is False

    def test_backoff_calculation(self) -> None:
        """Test exponential backoff progression."""
        d1 = calculate_backoff(attempt=1, initial_delay=0.1, backoff_factor=2.0, jitter=False)
        d2 = calculate_backoff(attempt=2, initial_delay=0.1, backoff_factor=2.0, jitter=False)
        d3 = calculate_backoff(attempt=3, initial_delay=0.1, backoff_factor=2.0, jitter=False)

        assert round(d1, 2) == 0.1
        assert round(d2, 2) == 0.2
        assert round(d3, 2) == 0.4

    def test_retry_successful_after_transient_failures(self) -> None:
        """Test function succeeds after failing twice with transient errors."""
        attempts = 0

        @retry(max_retries=3, initial_delay=0.01, backoff_factor=1.0, jitter=False)
        def flakey_network_call() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise NetPulseTimeoutError("Simulated temporary timeout")
            return "SUCCESS"

        result = flakey_network_call()
        assert result == "SUCCESS"
        assert attempts == 3

    def test_retry_does_not_retry_deterministic_failure(self) -> None:
        """Test function immediately fails without retrying on PacketValidationError."""
        attempts = 0

        @retry(max_retries=3, initial_delay=0.01)
        def deterministic_failure_call() -> None:
            nonlocal attempts
            attempts += 1
            raise PacketValidationError("Deterministic corruption error")

        with pytest.raises(PacketValidationError):
            deterministic_failure_call()

        assert attempts == 1  # No retries attempted

    def test_retry_exhaustion_preserves_root_cause(self) -> None:
        """Test that exhausting all retries preserves the original root cause."""
        attempts = 0

        @retry(max_retries=2, initial_delay=0.01, reraise_original=False)
        def persistent_failing_call() -> None:
            nonlocal attempts
            attempts += 1
            raise NetPulseTimeoutError("Always fails")

        with pytest.raises(RetryExhaustedError) as exc_info:
            persistent_failing_call()

        assert attempts == 3  # Initial attempt + 2 retries
        assert exc_info.value.attempts == 2
        assert isinstance(exc_info.value.last_exception, NetPulseTimeoutError)
