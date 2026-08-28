"""
NetPulse Flaky Test Detection & Stability Intelligence.

Identifies tests with intermittent outcomes across retries, volatile latency distributions,
and non-deterministic failures to distinguish true regressions from environment flakiness.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
from typing import Any, Dict, List, Optional


@dataclass
class FlakyTestRecord:
    """Record of test executions across retries and runs."""
    test_id: Optional[str]
    test_name: str
    attempts: int = 1
    outcomes: List[str] = field(default_factory=list)
    durations_ms: List[float] = field(default_factory=list)
    is_flaky: bool = False
    flakiness_reason: Optional[str] = None

    def evaluate(self) -> bool:
        """Determine if the test exhibited flaky behavior."""
        # 1. Failed at least once but eventually passed (transition from FAIL/ERROR -> PASS)
        if len(self.outcomes) > 1:
            has_failure = any(o in ("FAIL", "ERROR") for o in self.outcomes)
            has_pass = any(o == "PASS" for o in self.outcomes)
            if has_failure and has_pass:
                self.is_flaky = True
                self.flakiness_reason = f"Passed on attempt {self.attempts} after prior failure"
                return True

        # 2. Extreme latency volatility (>300% variance across >= 3 samples)
        if len(self.durations_ms) >= 3:
            mean_d = statistics.mean(self.durations_ms)
            if mean_d > 5.0:  # Only for non-trivial durations
                stdev_d = statistics.stdev(self.durations_ms)
                if (stdev_d / mean_d) > 3.0:
                    self.is_flaky = True
                    self.flakiness_reason = f"High execution time volatility (std dev {stdev_d:.1f}ms on mean {mean_d:.1f}ms)"
                    return True

        return self.is_flaky

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FlakyTracker:
    """
    Global tracker for test stability and retry transitions.
    """
    _records: Dict[str, FlakyTestRecord] = {}

    @classmethod
    def record_attempt(
        cls,
        test_name: str,
        outcome: str,
        duration_ms: float,
        test_id: Optional[str] = None
    ) -> FlakyTestRecord:
        """Record an individual test execution or retry attempt."""
        if test_name not in cls._records:
            cls._records[test_name] = FlakyTestRecord(test_id=test_id, test_name=test_name)

        rec = cls._records[test_name]
        rec.outcomes.append(outcome)
        rec.durations_ms.append(duration_ms)
        rec.attempts = len(rec.outcomes)
        rec.evaluate()
        return rec

    @classmethod
    def all_records(cls) -> List[FlakyTestRecord]:
        return list(cls._records.values())

    @classmethod
    def flaky_tests(cls) -> List[FlakyTestRecord]:
        return [r for r in cls._records.values() if r.is_flaky]

    @classmethod
    def get_summary(cls, total_tests_executed: int = 0) -> Dict[str, Any]:
        """Compute stability and flaky summary statistics."""
        flaky_list = cls.flaky_tests()
        flaky_count = len(flaky_list)
        failed_count = sum(1 for r in cls._records.values() if r.outcomes and r.outcomes[-1] in ("FAIL", "ERROR") and not r.is_flaky)
        total = total_tests_executed or len(cls._records)
        stable_count = max(0, total - flaky_count - failed_count)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_tests": total,
            "stable_count": stable_count,
            "flaky_count": flaky_count,
            "failed_count": failed_count,
            "flaky_tests": [r.to_dict() for r in flaky_list]
        }

    @classmethod
    def clear(cls) -> None:
        cls._records.clear()

    @classmethod
    def export_json(cls, filepath: str = "reports/flaky.json", total_tests_executed: int = 0) -> Path:
        """Export flaky analysis summary to JSON."""
        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        summary = cls.get_summary(total_tests_executed=total_tests_executed)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        return target
