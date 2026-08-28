"""
NetPulse Test Result Model.

Encapsulates individual test outcomes, metrics, protocol classifications,
serialization, and summary aggregation for baseline comparison and reporting.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any, Dict, List, Optional


class TestStatus(str, Enum):
    """Execution outcome status for a test case."""
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


@dataclass
class TestResult:
    """
    Standardized result representation for an executed network test.
    """
    test_name: str
    protocol: str  # TCP, UDP, HTTP, ICMP, L2, TOPOLOGY, etc.
    status: TestStatus
    duration_ms: float
    retries: int = 0
    error: Optional[str] = None
    source: Optional[str] = None
    destination: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metrics: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result to a plain dictionary."""
        data = asdict(self)
        data["status"] = self.status.value if isinstance(self.status, TestStatus) else str(self.status)
        return data

    def to_json(self, indent: Optional[int] = 2) -> str:
        """Serialize result to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestResult":
        """Deserialize a dictionary into a TestResult instance."""
        status_val = data.get("status", "PASS")
        if isinstance(status_val, str):
            status_enum = TestStatus(status_val.upper())
        else:
            status_enum = status_val

        return cls(
            test_name=data["test_name"],
            protocol=data.get("protocol", "UNKNOWN"),
            status=status_enum,
            duration_ms=float(data.get("duration_ms", 0.0)),
            retries=int(data.get("retries", 0)),
            error=data.get("error"),
            source=data.get("source"),
            destination=data.get("destination"),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            metrics=data.get("metrics", {}),
            details=data.get("details", {})
        )


@dataclass
class SuiteResult:
    """
    Container representing the aggregated outcomes of an entire test run.
    """
    suite_name: str = "NetPulse Test Suite"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    results: List[TestResult] = field(default_factory=list)
    performance_benchmarks: List[Dict[str, Any]] = field(default_factory=list)
    environment_info: Dict[str, Any] = field(default_factory=dict)

    def add_result(self, result: TestResult) -> None:
        """Append a test result to the suite."""
        self.results.append(result)

    def add_performance_benchmark(self, benchmark: Any) -> None:
        """Append a performance result dictionary or PerformanceResult model."""
        if hasattr(benchmark, "to_dict"):
            self.performance_benchmarks.append(benchmark.to_dict())
        elif isinstance(benchmark, dict):
            self.performance_benchmarks.append(benchmark)

    @property
    def total_tests(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.PASS)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.FAIL)

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.ERROR)

    @property
    def skipped_count(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.SKIPPED)

    @property
    def total_duration_ms(self) -> float:
        return sum(r.duration_ms for r in self.results)

    @property
    def pass_rate_pct(self) -> float:
        if not self.results:
            return 0.0
        return (self.passed_count / len(self.results)) * 100.0

    def get_summary(self) -> Dict[str, Any]:
        """Generate high-level summary metrics."""
        return {
            "suite_name": self.suite_name,
            "timestamp": self.timestamp,
            "total_tests": self.total_tests,
            "total_benchmarks": len(self.performance_benchmarks),
            "passed": self.passed_count,
            "failed": self.failed_count,
            "errors": self.error_count,
            "skipped": self.skipped_count,
            "pass_rate_pct": round(self.pass_rate_pct, 2),
            "total_duration_ms": round(self.total_duration_ms, 2),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert suite result and all child tests to a dictionary."""
        return {
            "summary": self.get_summary(),
            "environment": self.environment_info,
            "tests": [r.to_dict() for r in self.results],
            "benchmarks": self.performance_benchmarks
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert suite result to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save_to_file(self, filepath: str) -> None:
        """Write suite result JSON to file."""
        from pathlib import Path
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json(indent=2))
