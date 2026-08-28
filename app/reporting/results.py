"""
NetPulse Reporting & Baseline Regression Engine.

Handles test report generation, JSON/XML artifact serialization,
and regression comparison against historical test baselines.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.result import SuiteResult, TestResult, TestStatus
from app.core.logging import get_logger

logger = get_logger("reporting")


@dataclass
class BaselineComparisonDiff:
    """Detailed diff outcome comparing current test run against baseline."""
    baseline_timestamp: Optional[str]
    current_timestamp: str
    total_baseline_tests: int
    total_current_tests: int
    new_tests: List[str] = field(default_factory=list)
    missing_tests: List[str] = field(default_factory=list)
    status_regressions: List[Dict[str, Any]] = field(default_factory=list)  # PASS -> FAIL
    status_improvements: List[Dict[str, Any]] = field(default_factory=list)  # FAIL -> PASS
    performance_regressions: List[Dict[str, Any]] = field(default_factory=list)  # > 50% slower
    has_regressions: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaselineManager:
    """
    Manages saving and comparing test baselines for regression detection.
    """

    @staticmethod
    def save_baseline(suite_result: SuiteResult, filepath: str = "reports/baseline.json") -> Path:
        """Save the given suite result as the official regression baseline."""
        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        suite_result.save_to_file(str(target))
        logger.info(f"Saved baseline with {suite_result.total_tests} tests to {target}")
        return target

    @staticmethod
    def load_baseline(filepath: str = "reports/baseline.json") -> Optional[Dict[str, Any]]:
        """Load historical baseline from JSON file."""
        target = Path(filepath)
        if not target.exists():
            return None
        try:
            with open(target, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read baseline file at {filepath}: {e}")
            return None

    @staticmethod
    def compare_against_baseline(
        current_suite: SuiteResult,
        baseline_filepath: str = "reports/baseline.json",
        perf_threshold_pct: float = 50.0
    ) -> BaselineComparisonDiff:
        """
        Compare current suite results against baseline and flag regressions.
        """
        baseline_data = BaselineManager.load_baseline(baseline_filepath)
        current_dict = {r.test_name: r for r in current_suite.results}

        if not baseline_data or "tests" not in baseline_data:
            logger.warning("No valid baseline found for comparison.")
            return BaselineComparisonDiff(
                baseline_timestamp=None,
                current_timestamp=current_suite.timestamp,
                total_baseline_tests=0,
                total_current_tests=len(current_dict),
                new_tests=list(current_dict.keys()),
                has_regressions=False
            )

        baseline_tests = {t["test_name"]: t for t in baseline_data.get("tests", [])}
        diff = BaselineComparisonDiff(
            baseline_timestamp=baseline_data.get("summary", {}).get("timestamp"),
            current_timestamp=current_suite.timestamp,
            total_baseline_tests=len(baseline_tests),
            total_current_tests=len(current_dict)
        )

        # 1. Identify New & Missing Tests
        for name in current_dict:
            if name not in baseline_tests:
                diff.new_tests.append(name)

        for name in baseline_tests:
            if name not in current_dict:
                diff.missing_tests.append(name)

        # 2. Check Status and Performance Changes
        for name, current_res in current_dict.items():
            if name in baseline_tests:
                base_t = baseline_tests[name]
                base_status = base_t.get("status", "UNKNOWN")
                curr_status = current_res.status.value

                # Status Regressions
                if base_status == "PASS" and curr_status in ("FAIL", "ERROR"):
                    diff.status_regressions.append({
                        "test_name": name,
                        "protocol": current_res.protocol,
                        "baseline_status": base_status,
                        "current_status": curr_status,
                        "error": current_res.error
                    })
                    diff.has_regressions = True

                elif base_status in ("FAIL", "ERROR") and curr_status == "PASS":
                    diff.status_improvements.append({
                        "test_name": name,
                        "protocol": current_res.protocol,
                        "baseline_status": base_status,
                        "current_status": curr_status
                    })

                # Performance Regressions
                base_duration = float(base_t.get("duration_ms", 0.0))
                curr_duration = current_res.duration_ms
                if base_duration > 1.0:  # Only evaluate if baseline duration was non-negligible
                    pct_increase = ((curr_duration - base_duration) / base_duration) * 100.0
                    if pct_increase > perf_threshold_pct and (curr_duration - base_duration) > 5.0:
                        diff.performance_regressions.append({
                            "test_name": name,
                            "protocol": current_res.protocol,
                            "baseline_duration_ms": round(base_duration, 2),
                            "current_duration_ms": round(curr_duration, 2),
                            "increase_pct": round(pct_increase, 2)
                        })

        if diff.status_regressions:
            diff.has_regressions = True

        return diff


class TestReportGenerator:
    """
    Utility for exporting test execution reports in JSON and Markdown console summaries.
    """

    @staticmethod
    def generate_markdown_summary(suite_result: SuiteResult, diff: Optional[BaselineComparisonDiff] = None) -> str:
        """Generate a clean markdown report summary."""
        summary = suite_result.get_summary()

        lines = [
            f"# NetPulse Test Execution Report",
            f"",
            f"- **Timestamp**: `{summary['timestamp']}`",
            f"- **Total Tests**: `{summary['total_tests']}`",
            f"- **Passed**: `{summary['passed']}` | **Failed**: `{summary['failed']}` | **Errors**: `{summary['errors']}` | **Skipped**: `{summary['skipped']}`",
            f"- **Pass Rate**: `{summary['pass_rate_pct']}%`",
            f"- **Total Duration**: `{summary['total_duration_ms']:.2f} ms`",
            f"",
            f"## Test Results Breakdown",
            f"",
            f"| Protocol | Test Name | Status | Duration (ms) | Retries |",
            f"| :--- | :--- | :--- | :--- | :--- |"
        ]

        for r in suite_result.results:
            status_icon = "PASS" if r.status == TestStatus.PASS else ("FAIL" if r.status == TestStatus.FAIL else r.status.value)
            lines.append(f"| `{r.protocol}` | `{r.test_name}` | **{status_icon}** | `{r.duration_ms:.2f}` | `{r.retries}` |")

        if diff:
            lines.extend([
                f"",
                f"## Baseline Regression Analysis",
                f"",
                f"- **Baseline Timestamp**: `{diff.baseline_timestamp or 'N/A'}`",
                f"- **Status Regressions**: `{len(diff.status_regressions)}`",
                f"- **Status Improvements**: `{len(diff.status_improvements)}`",
                f"- **Performance Regressions**: `{len(diff.performance_regressions)}`",
                f"- **New Tests**: `{len(diff.new_tests)}` | **Missing Tests**: `{len(diff.missing_tests)}`"
            ])

            if diff.status_regressions:
                lines.extend([
                    f"",
                    f"### Regressed Tests",
                    f"| Test Name | Baseline | Current | Error |",
                    f"| :--- | :--- | :--- | :--- |"
                ])
                for reg in diff.status_regressions:
                    lines.append(f"| `{reg['test_name']}` | `{reg['baseline_status']}` | `{reg['current_status']}` | `{reg.get('error', '')}` |")

        return "\n".join(lines)
