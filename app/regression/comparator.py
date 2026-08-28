"""
NetPulse Intelligent Regression Comparator Engine.

Compares active test outcomes and performance metrics against historical baselines,
classifying results into PASS, REGRESSION, IMPROVEMENT, or NO_BASELINE with exact percentage deltas.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.regression.baseline import RegressionBaseline
from app.regression.thresholds import RegressionThresholds

logger = get_logger("regression.comparator")


class RegressionStatus(str, Enum):
    """Overall status of the regression comparison."""
    PASS = "PASS"
    REGRESSION = "REGRESSION"
    IMPROVEMENT = "IMPROVEMENT"
    NO_BASELINE = "NO_BASELINE"


@dataclass
class RegressionReport:
    """Detailed evaluation report comparing current execution against baseline."""
    status: RegressionStatus
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    baseline_timestamp: Optional[str] = None
    baseline_commit: Optional[str] = None
    thresholds: Dict[str, Any] = field(default_factory=dict)
    total_tests_compared: int = 0
    total_benchmarks_compared: int = 0
    status_regressions: List[Dict[str, Any]] = field(default_factory=list)
    status_improvements: List[Dict[str, Any]] = field(default_factory=list)
    duration_regressions: List[Dict[str, Any]] = field(default_factory=list)
    throughput_regressions: List[Dict[str, Any]] = field(default_factory=list)
    latency_regressions: List[Dict[str, Any]] = field(default_factory=list)
    packet_loss_regressions: List[Dict[str, Any]] = field(default_factory=list)
    new_tests: List[str] = field(default_factory=list)
    missing_tests: List[str] = field(default_factory=list)
    benchmark_deltas: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def has_regressions(self) -> bool:
        return self.status == RegressionStatus.REGRESSION

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


class RegressionComparator:
    """
    Evaluates test results and benchmarks against historical baselines.
    """

    @classmethod
    def compare(
        cls,
        current_tests: List[Any],
        current_benchmarks: Optional[List[Any]] = None,
        baseline: Optional[RegressionBaseline] = None,
        thresholds: Optional[RegressionThresholds] = None
    ) -> RegressionReport:
        """
        Compare current test run and benchmarks against the provided baseline.
        """
        thresh = thresholds or RegressionThresholds()

        if baseline is None:
            return RegressionReport(
                status=RegressionStatus.NO_BASELINE,
                thresholds=thresh.to_dict(),
                total_tests_compared=len(current_tests),
                total_benchmarks_compared=len(current_benchmarks or []),
                new_tests=[t.get("test_name", str(t)) if isinstance(t, dict) else getattr(t, "test_name", str(t)) for t in current_tests]
            )

        report = RegressionReport(
            status=RegressionStatus.PASS,
            baseline_timestamp=baseline.timestamp,
            baseline_commit=baseline.git_commit,
            thresholds=thresh.to_dict(),
            total_tests_compared=len(current_tests),
            total_benchmarks_compared=len(current_benchmarks or [])
        )

        curr_tests_dict = {}
        for t in current_tests:
            name = t.get("test_name") if isinstance(t, dict) else getattr(t, "test_name", None)
            if name:
                curr_tests_dict[name] = t.to_dict() if hasattr(t, "to_dict") else t

        # 1. Compare Functional Test Statuses and Durations
        for name, curr_t in curr_tests_dict.items():
            if name not in baseline.tests:
                report.new_tests.append(name)
                continue

            base_t = baseline.tests[name]
            base_status = base_t.get("status", "UNKNOWN")
            curr_status = curr_t.get("status", "UNKNOWN")

            # Status regression: PASS -> FAIL/ERROR
            if base_status == "PASS" and curr_status in ("FAIL", "ERROR"):
                report.status_regressions.append({
                    "test_name": name,
                    "baseline_status": base_status,
                    "current_status": curr_status,
                    "error": curr_t.get("error")
                })
            # Status improvement: FAIL/ERROR -> PASS
            elif base_status in ("FAIL", "ERROR") and curr_status == "PASS":
                report.status_improvements.append({
                    "test_name": name,
                    "baseline_status": base_status,
                    "current_status": curr_status
                })

            # Duration regression
            base_dur = float(base_t.get("duration_ms", 0.0))
            curr_dur = float(curr_t.get("duration_ms", 0.0))
            if base_dur >= thresh.min_duration_ms:
                dur_diff_pct = ((curr_dur - base_dur) / base_dur) * 100.0
                if dur_diff_pct > thresh.duration_increase_pct and (curr_dur - base_dur) > 10.0:
                    report.duration_regressions.append({
                        "test_name": name,
                        "baseline_duration_ms": round(base_dur, 2),
                        "current_duration_ms": round(curr_dur, 2),
                        "increase_pct": round(dur_diff_pct, 2)
                    })

        for name in baseline.tests:
            if name not in curr_tests_dict:
                report.missing_tests.append(name)

        # 2. Compare Performance Benchmarks
        if current_benchmarks and baseline.benchmarks:
            for b in current_benchmarks:
                b_dict = b.to_dict() if hasattr(b, "to_dict") else b
                key = f"{b_dict.get('test_name')}_{b_dict.get('protocol')}_{b_dict.get('packet_size', 0)}"

                if key in baseline.benchmarks:
                    base_b = baseline.benchmarks[key]
                    delta_record = {
                        "benchmark_key": key,
                        "benchmark_name": b_dict.get("test_name"),
                        "protocol": b_dict.get("protocol"),
                        "packet_size": b_dict.get("packet_size", 0)
                    }

                    # Throughput
                    if "throughput" in b_dict and "throughput" in base_b:
                        c_thpt = float(b_dict["throughput"].get("throughput_mbps", 0.0))
                        b_thpt = float(base_b["throughput"].get("throughput_mbps", 0.0))
                        delta_record["current_throughput_mbps"] = c_thpt
                        delta_record["baseline_throughput_mbps"] = b_thpt
                        if b_thpt > 0:
                            thpt_delta = ((c_thpt - b_thpt) / b_thpt) * 100.0
                            delta_record["throughput_delta_pct"] = round(thpt_delta, 2)
                            if thpt_delta < -thresh.throughput_drop_pct:
                                report.throughput_regressions.append({
                                    "benchmark": key,
                                    "baseline_mbps": b_thpt,
                                    "current_mbps": c_thpt,
                                    "drop_pct": round(abs(thpt_delta), 2)
                                })

                    # Latency
                    if "latency" in b_dict and "latency" in base_b:
                        c_lat = float(b_dict["latency"].get("avg_ms", 0.0))
                        b_lat = float(base_b["latency"].get("avg_ms", 0.0))
                        delta_record["current_latency_ms"] = c_lat
                        delta_record["baseline_latency_ms"] = b_lat
                        if b_lat > 0:
                            lat_delta = ((c_lat - b_lat) / b_lat) * 100.0
                            delta_record["latency_delta_pct"] = round(lat_delta, 2)
                            if lat_delta > thresh.latency_increase_pct:
                                report.latency_regressions.append({
                                    "benchmark": key,
                                    "baseline_ms": b_lat,
                                    "current_ms": c_lat,
                                    "increase_pct": round(lat_delta, 2)
                                })

                    # Packet Loss
                    if "packet_loss" in b_dict and "packet_loss" in base_b:
                        c_loss = float(b_dict["packet_loss"].get("packet_loss_percent", 0.0))
                        b_loss = float(base_b["packet_loss"].get("packet_loss_percent", 0.0))
                        loss_delta = c_loss - b_loss
                        delta_record["current_loss_pct"] = c_loss
                        delta_record["baseline_loss_pct"] = b_loss
                        delta_record["loss_delta_pct"] = round(loss_delta, 2)
                        if loss_delta > thresh.packet_loss_increase_pct:
                            report.packet_loss_regressions.append({
                                "benchmark": key,
                                "baseline_loss_pct": b_loss,
                                "current_loss_pct": c_loss,
                                "increase_pct": round(loss_delta, 2)
                            })

                    report.benchmark_deltas.append(delta_record)

        # 3. Compute Final Status
        if (
            report.status_regressions
            or report.throughput_regressions
            or report.latency_regressions
            or report.packet_loss_regressions
        ):
            report.status = RegressionStatus.REGRESSION
        elif report.status_improvements and not report.duration_regressions:
            report.status = RegressionStatus.IMPROVEMENT
        else:
            report.status = RegressionStatus.PASS

        return report

    @classmethod
    def export_json(cls, report: RegressionReport, filepath: str = "reports/regression.json") -> Path:
        """Export regression report to JSON."""
        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2)
        logger.info(f"Exported regression report (status: {report.status.value}) to {target}")
        return target
