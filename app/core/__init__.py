"""
NetPulse Core Module.

Contains configuration management, custom exception hierarchy, structured logging,
retry mechanisms, and standardized test result models.
"""

from app.core.exceptions import (
    NetPulseError,
    ConnectionError,
    TimeoutError,
    SocketError,
    PacketValidationError,
    ConfigurationError,
    TestExecutionError,
    RetryExhaustedError,
    TopologyError,
    ServerLifecycleError,
)
from app.core.config import (
    AppConfig,
    ConfigManager,
    NetworkConfig,
    TestingConfig,
    LoggingConfig,
    TopologyConfig,
)
from app.core.logging import (
    get_logger,
    setup_logging,
    TestContextAdapter,
)
from app.core.retry import (
    retry,
    retry_call,
    is_transient_network_error,
)
from app.core.result import (
    TestResult,
    TestStatus,
    SuiteResult,
)

__all__ = [
    "NetPulseError",
    "ConnectionError",
    "TimeoutError",
    "SocketError",
    "PacketValidationError",
    "ConfigurationError",
    "TestExecutionError",
    "RetryExhaustedError",
    "TopologyError",
    "ServerLifecycleError",
    "AppConfig",
    "ConfigManager",
    "NetworkConfig",
    "TestingConfig",
    "LoggingConfig",
    "TopologyConfig",
    "get_logger",
    "setup_logging",
    "TestContextAdapter",
    "retry",
    "retry_call",
    "is_transient_network_error",
    "TestResult",
    "TestStatus",
    "SuiteResult",
]
