"""
NetPulse Base Test Class.

Provides structured lifecycle hooks, per-test logging adapters, and execution timing.
"""

import time
from typing import Any

from app.core.logging import get_logger, TestContextAdapter


class BaseNetworkTest:
    """
    Base test class providing structured contextual logging and diagnostic timing.
    """

    logger: TestContextAdapter
    _start_time: float = 0.0

    def setup_method(self, method: Any) -> None:
        """Pytest test setup hook."""
        test_name = getattr(method, "__name__", "unknown_test")
        self.logger = get_logger(test_name, test_name=test_name)
        self._start_time = time.perf_counter()
        self.logger.debug(f"Starting test: {test_name}")

    def teardown_method(self, method: Any) -> None:
        """Pytest test teardown hook."""
        duration_ms = (time.perf_counter() - self._start_time) * 1000.0
        test_name = getattr(method, "__name__", "unknown_test")
        self.logger.debug(f"Finished test: {test_name} in {duration_ms:.2f}ms")

    def measure_duration_ms(self) -> float:
        """Return elapsed duration since setup in milliseconds."""
        return (time.perf_counter() - self._start_time) * 1000.0
