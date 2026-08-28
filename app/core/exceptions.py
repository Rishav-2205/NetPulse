"""
NetPulse Exception Hierarchy.

Custom exceptions for network socket operations, packet validation,
configuration errors, retry exhaustion, and test execution lifecycle.
"""

from typing import Optional, Any, Dict


class NetPulseError(Exception):
    """Base exception for all NetPulse framework errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


class ConnectionError(NetPulseError):
    """Raised when a network connection attempt fails or is dropped."""

    def __init__(self, message: str, host: Optional[str] = None, port: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        merged_details = details or {}
        if host:
            merged_details["host"] = host
        if port:
            merged_details["port"] = port
        super().__init__(message, merged_details)
        self.host = host
        self.port = port


class TimeoutError(NetPulseError):
    """Raised when a network socket or request operation times out."""

    def __init__(self, message: str, timeout_seconds: Optional[float] = None, details: Optional[Dict[str, Any]] = None):
        merged_details = details or {}
        if timeout_seconds is not None:
            merged_details["timeout_seconds"] = timeout_seconds
        super().__init__(message, merged_details)
        self.timeout_seconds = timeout_seconds


class SocketError(NetPulseError):
    """Raised when low-level socket creation, binding, or option tuning fails."""
    pass


# Convenience aliases to avoid shadowing standard library exceptions
NetPulseConnectionError = ConnectionError
NetPulseTimeoutError = TimeoutError
NetPulseSocketError = SocketError


class PacketValidationError(NetPulseError):
    """Raised when packet structure, checksum, or payload integrity fails validation."""

    def __init__(self, message: str, expected: Optional[Any] = None, actual: Optional[Any] = None, details: Optional[Dict[str, Any]] = None):
        merged_details = details or {}
        if expected is not None:
            merged_details["expected"] = expected
        if actual is not None:
            merged_details["actual"] = actual
        super().__init__(message, merged_details)
        self.expected = expected
        self.actual = actual


class ConfigurationError(NetPulseError):
    """Raised when configuration loading, schema validation, or profile resolution fails."""
    pass


class TestExecutionError(NetPulseError):
    """Raised when test execution lifecycle, setup, or teardown fails."""
    pass


class RetryExhaustedError(NetPulseError):
    """Raised when all retry attempts for a transient network operation are exhausted."""

    def __init__(self, message: str, attempts: int, last_exception: Optional[BaseException] = None):
        details = {"attempts": attempts, "last_exception": str(last_exception) if last_exception else None}
        super().__init__(message, details)
        self.attempts = attempts
        self.last_exception = last_exception


class TopologyError(NetPulseError):
    """Raised when a simulated network topology is invalid or route lookup fails."""
    pass


class ServerLifecycleError(NetPulseError):
    """Raised when a local test server fails to start, bind, or stop gracefully."""
    pass
