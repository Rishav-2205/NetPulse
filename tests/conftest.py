"""
NetPulse Global Pytest Configuration and Test Result Aggregator.
"""

from datetime import datetime, timezone
import os
from pathlib import Path
import pytest
from typing import Any, Dict, Generator, List

from app.core.config import AppConfig, ConfigManager
from app.core.logging import setup_logging, get_logger
from app.core.result import SuiteResult, TestResult, TestStatus
from app.networking.http import HTTPClient, HTTPServer
from app.networking.tcp import TCPServer
from app.networking.udp import UDPServer
from app.packets.builder import PayloadGenerator
from app.topology.model import NetworkTopology

logger = get_logger("conftest")

# Global in-memory test suite collector
_suite_result = SuiteResult(suite_name="NetPulse Automated Network Test Suite")


def pytest_configure(config: pytest.Config) -> None:
    """Configure markers and initialize structured logging."""
    setup_logging(level="INFO")
    logger.info("Initializing NetPulse Test Session")

    # Ensure reports and logs directories exist
    Path("reports").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[Any]) -> Generator[None, pytest.TestReport, None]:
    """Capture test execution outcome, duration, protocol marker, and store in SuiteResult."""
    outcome = yield
    report = outcome.get_result()

    # Only record at the 'call' phase (or setup phase if it failed with ERROR)
    if report.when == "call" or (report.when == "setup" and report.failed):
        duration_ms = report.duration * 1000.0

        # Determine protocol from markers or test path
        protocol = "NETWORK"
        for mark in ("tcp", "udp", "http", "performance", "topology", "unit", "regression", "integration"):
            if item.get_closest_marker(mark):
                protocol = mark.upper()
                break

        # Map pytest outcome to TestStatus
        if report.passed:
            status = TestStatus.PASS
            error_msg = None
        elif report.skipped:
            status = TestStatus.SKIPPED
            error_msg = str(report.longrepr) if report.longrepr else "Skipped"
        elif report.failed:
            status = TestStatus.FAIL if report.when == "call" else TestStatus.ERROR
            error_msg = str(report.longrepr) if report.longrepr else "Assertion / Execution Failure"
        else:
            status = TestStatus.ERROR
            error_msg = "Unknown execution status"

        test_res = TestResult(
            test_name=item.nodeid,
            protocol=protocol,
            status=status,
            duration_ms=duration_ms,
            error=error_msg[:1000] if error_msg else None,
            details={"keywords": list(item.keywords.keys()), "location": item.location[0]}
        )
        _suite_result.add_result(test_res)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Write collected results to JSON and generate summary on session completion."""
    output_path = Path("reports/results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _suite_result.save_to_file(str(output_path))
    logger.info(
        f"Test session completed: {_suite_result.passed_count} passed, "
        f"{_suite_result.failed_count} failed, {_suite_result.error_count} errors, "
        f"{_suite_result.skipped_count} skipped (Saved to {output_path})"
    )


# Fixtures injection for all tests
@pytest.fixture(scope="session")
def network_config() -> AppConfig:
    return ConfigManager.get_config()


@pytest.fixture
def tcp_server() -> Generator[TCPServer, None, None]:
    server = TCPServer(host="127.0.0.1", port=0)
    server.start()
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture
def udp_server() -> Generator[UDPServer, None, None]:
    server = UDPServer(host="127.0.0.1", port=0)
    server.start()
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture
def http_server() -> Generator[HTTPServer, None, None]:
    server = HTTPServer(host="127.0.0.1", port=0)
    server.start()
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture
def http_session(http_server: HTTPServer) -> Generator[HTTPClient, None, None]:
    client = HTTPClient(base_url=http_server.url, timeout=5.0)
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
def payload_factory() -> type[PayloadGenerator]:
    return PayloadGenerator


@pytest.fixture
def standard_topology() -> NetworkTopology:
    return NetworkTopology.create_standard_three_node()


@pytest.fixture
def test_suite_collector() -> SuiteResult:
    return _suite_result
