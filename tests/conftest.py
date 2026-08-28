"""
NetPulse Global Pytest Configuration and Test Result Aggregator.
"""

from pathlib import Path
import pytest
from typing import Any, Generator

from app.core.config import AppConfig, ConfigManager
from app.core.logging import setup_logging, get_logger
from app.core.result import SuiteResult, TestResult, TestStatus
from app.networking.http import HTTPClient, HTTPServer
from app.networking.tcp import TCPServer
from app.networking.udp import UDPServer
from app.packets.builder import PayloadGenerator
from app.reporting.defects import DefectManager, TestDefect
from app.reporting.flaky import FlakyTracker
from app.reporting.results import PerformanceTrendTracker, TestReportGenerator
from app.testing.metadata import TestCatalog
from app.topology.model import NetworkTopology

logger = get_logger("conftest")

# Global in-memory test suite collector
_suite_result = SuiteResult(suite_name="NetPulse Automated Network Test Suite")


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom CLI options to pytest."""
    parser.addoption(
        "--profile",
        action="store",
        default="quick",
        help="Configuration profile for test execution (e.g., quick, standard, stress, ci)"
    )


def pytest_configure(config: pytest.Config) -> None:
    """Configure markers and initialize structured logging."""
    setup_logging(level="INFO")
    profile = config.getoption("--profile", default="quick")
    logger.info(f"Initializing NetPulse Test Session with profile: '{profile}'")
    ConfigManager.load(profile=profile)

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
            outcome_str = "PASS"
        elif report.skipped:
            status = TestStatus.SKIPPED
            error_msg = str(report.longrepr) if report.longrepr else "Skipped"
            outcome_str = "SKIPPED"
        elif report.failed:
            status = TestStatus.FAIL if report.when == "call" else TestStatus.ERROR
            error_msg = str(report.longrepr) if report.longrepr else "Assertion / Execution Failure"
            outcome_str = "FAIL"
        else:
            status = TestStatus.ERROR
            error_msg = "Unknown execution status"
            outcome_str = "ERROR"

        # Check for test case metadata
        meta = getattr(getattr(item, "obj", None), "__netpulse_test_case__", None)
        test_id = meta.test_id if meta else f"NET-GEN-{abs(hash(item.nodeid)) % 10000:04d}"

        # Track flaky behavior
        FlakyTracker.record_attempt(
            test_name=item.nodeid,
            outcome=outcome_str,
            duration_ms=duration_ms,
            test_id=test_id
        )

        # Record defect if failed
        if status in (TestStatus.FAIL, TestStatus.ERROR):
            exc_type = call.excinfo.typename if call.excinfo else "AssertionError"
            exc_msg = str(call.excinfo.value) if call.excinfo else error_msg
            defect = TestDefect(
                defect_id=f"DEF-{abs(hash(item.nodeid)) % 100000:05d}",
                test_id=test_id,
                test_name=item.nodeid,
                category=meta.category if meta else "Automated",
                protocol=protocol,
                layer=meta.layer if meta else "Layer 4",
                severity="High" if status == TestStatus.FAIL else "Critical",
                exception_type=exc_type,
                exception_message=str(exc_msg)[:500] if exc_msg else None,
                stack_trace=str(report.longrepr)[:2000] if report.longrepr else None
            )
            DefectManager.record_defect(defect)

        test_res = TestResult(
            test_name=item.nodeid,
            protocol=protocol,
            status=status,
            duration_ms=duration_ms,
            error=error_msg[:1000] if error_msg else None,
            details={
                "test_id": test_id,
                "keywords": list(item.keywords.keys()),
                "location": item.location[0]
            }
        )
        _suite_result.add_result(test_res)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Write collected results in all formats on session completion."""
    Path("reports").mkdir(exist_ok=True)

    # 1. JSON result
    output_path = Path("reports/results.json")
    _suite_result.save_to_file(str(output_path))

    # 2. CSV exports
    TestReportGenerator.export_csv_reports(_suite_result)

    # 3. Defect & Flaky Reports
    DefectManager.export_json("reports/defects.json")
    DefectManager.export_csv("reports/defects.csv")
    FlakyTracker.export_json("reports/flaky.json", total_tests_executed=_suite_result.total_tests)

    # 4. Test Catalog export
    TestCatalog.export_json("reports/test_cases.json")
    TestCatalog.export_csv("reports/test_cases.csv")

    # 5. Executive HTML Dashboard
    TestReportGenerator.generate_executive_dashboard(_suite_result, output_path="reports/dashboard.html")

    # 6. Benchmark history tracking
    if _suite_result.performance_benchmarks:
        PerformanceTrendTracker.record_benchmarks(_suite_result.performance_benchmarks, filepath="reports/history.json")

    flaky_summary = FlakyTracker.get_summary(total_tests_executed=_suite_result.total_tests)
    logger.info(
        f"Test session completed: {_suite_result.passed_count} passed, "
        f"{_suite_result.failed_count} failed, {_suite_result.error_count} errors, "
        f"{_suite_result.skipped_count} skipped, {flaky_summary['flaky_count']} flaky (Saved to {output_path})"
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
