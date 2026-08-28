"""
NetPulse Production-Grade Reporting & Baseline Regression Engine.

Handles multi-format test reports (JSON, JUnit XML, CSV, HTML Executive Dashboard),
baseline diff regression tracking, defect capture, and performance historical trending.
"""

import csv
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from app.core.result import SuiteResult, TestStatus
from app.core.logging import get_logger
from app.performance.metrics import EnvironmentMetadata
from app.reporting.defects import DefectManager
from app.reporting.flaky import FlakyTracker

logger = get_logger("reporting")


@dataclass
class PerformanceComparisonDiff:
    """Detailed diff outcome comparing performance metrics against baseline."""
    baseline_timestamp: Optional[str]
    current_timestamp: str
    benchmark_name: str
    protocol: str
    throughput_baseline_mbps: Optional[float] = None
    throughput_current_mbps: Optional[float] = None
    throughput_delta_pct: Optional[float] = None
    latency_baseline_ms: Optional[float] = None
    latency_current_ms: Optional[float] = None
    latency_delta_pct: Optional[float] = None
    loss_baseline_pct: Optional[float] = None
    loss_current_pct: Optional[float] = None
    loss_delta_pct: Optional[float] = None
    jitter_baseline_ms: Optional[float] = None
    jitter_current_ms: Optional[float] = None
    jitter_delta_pct: Optional[float] = None
    is_regression: bool = False
    regression_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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
    performance_regressions: List[Dict[str, Any]] = field(default_factory=list)  # > 50% slower duration
    benchmark_diffs: List[PerformanceComparisonDiff] = field(default_factory=list)
    has_regressions: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["benchmark_diffs"] = [b.to_dict() for b in self.benchmark_diffs]
        return data


class BaselineManager:
    """
    Manages saving and comparing test baselines and performance benchmarks for regression detection.
    """

    @staticmethod
    def save_baseline(data: Union[SuiteResult, Dict[str, Any], List[Any]], filepath: str = "reports/baseline.json") -> Path:
        """Save the given result data as the official regression baseline."""
        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)

        if hasattr(data, "save_to_file"):
            data.save_to_file(str(target))
        elif hasattr(data, "to_dict"):
            with open(target, "w", encoding="utf-8") as f:
                json.dump(data.to_dict(), f, indent=2)
        elif isinstance(data, list):
            serialized = [item.to_dict() if hasattr(item, "to_dict") else item for item in data]
            with open(target, "w", encoding="utf-8") as f:
                json.dump({"benchmarks": serialized, "timestamp": datetime.now(timezone.utc).isoformat()}, f, indent=2)
        else:
            with open(target, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        logger.info(f"Saved baseline to {target}")
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

    @classmethod
    def compare_against_baseline(
        cls,
        current_data: Any,
        baseline_filepath: str = "reports/baseline.json"
    ) -> BaselineComparisonDiff:
        """Compare current test run and benchmarks against a saved baseline."""
        baseline_data = cls.load_baseline(baseline_filepath)
        curr_ts = datetime.now(timezone.utc).isoformat()

        if hasattr(current_data, "results"):
            curr_results = current_data.results
            curr_benchmarks = getattr(current_data, "performance_benchmarks", [])
        elif isinstance(current_data, list):
            curr_results = current_data
            curr_benchmarks = []
        else:
            curr_results = []
            curr_benchmarks = []

        curr_dict = {
            r.test_name if hasattr(r, "test_name") else r.get("test_name"): r
            for r in curr_results
        }

        if not baseline_data:
            return BaselineComparisonDiff(
                baseline_timestamp=None,
                current_timestamp=curr_ts,
                total_baseline_tests=0,
                total_current_tests=len(curr_results),
                new_tests=list(curr_dict.keys()),
                has_regressions=False
            )

        base_tests_list = baseline_data.get("tests", [])
        if isinstance(base_tests_list, dict):
            base_tests = base_tests_list
        else:
            base_tests = {t.get("test_name"): t for t in base_tests_list}

        base_ts = baseline_data.get("timestamp") or baseline_data.get("summary", {}).get("timestamp")

        new_tests: List[str] = []
        missing_tests: List[str] = []
        status_regressions: List[Dict[str, Any]] = []
        status_improvements: List[Dict[str, Any]] = []
        perf_regressions: List[Dict[str, Any]] = []

        for name, curr in curr_dict.items():
            if hasattr(curr, "status"):
                c_status = curr.status.value if hasattr(curr.status, "value") else str(curr.status)
            else:
                c_status = curr.get("status")

            c_dur = curr.duration_ms if hasattr(curr, "duration_ms") else curr.get("duration_ms", 0.0)

            if name not in base_tests:
                new_tests.append(name)
            else:
                base = base_tests[name]
                b_status = base.get("status") if isinstance(base, dict) else (base.status.value if hasattr(base.status, "value") else str(base.status))
                b_dur = base.get("duration_ms", 0.0) if isinstance(base, dict) else getattr(base, "duration_ms", 0.0)

                if b_status == "PASS" and c_status in ("FAIL", "ERROR"):
                    status_regressions.append({
                        "test_name": name,
                        "baseline_status": b_status,
                        "current_status": c_status
                    })
                elif b_status in ("FAIL", "ERROR") and c_status == "PASS":
                    status_improvements.append({
                        "test_name": name,
                        "baseline_status": b_status,
                        "current_status": c_status
                    })

                if b_dur > 0 and c_dur > (b_dur * 1.5):
                    perf_regressions.append({
                        "test_name": name,
                        "baseline_duration_ms": b_dur,
                        "current_duration_ms": c_dur,
                        "increase_pct": round(((c_dur - b_dur) / b_dur) * 100.0, 1)
                    })

        for name in base_tests:
            if name not in curr_dict:
                missing_tests.append(name)

        bench_diffs = cls.compare_benchmarks(curr_benchmarks, baseline_filepath) if curr_benchmarks else []
        has_reg = bool(status_regressions or any(b.is_regression for b in bench_diffs))

        return BaselineComparisonDiff(
            baseline_timestamp=base_ts,
            current_timestamp=curr_ts,
            total_baseline_tests=len(base_tests),
            total_current_tests=len(curr_results),
            new_tests=new_tests,
            missing_tests=missing_tests,
            status_regressions=status_regressions,
            status_improvements=status_improvements,
            performance_regressions=perf_regressions,
            benchmark_diffs=bench_diffs,
            has_regressions=has_reg
        )

    @classmethod
    def compare_with_baseline(
        cls,
        current_data: Any,
        baseline_filepath: str = "reports/baseline.json"
    ) -> BaselineComparisonDiff:
        """Alias for compare_against_baseline."""
        return cls.compare_against_baseline(current_data, baseline_filepath)

    @classmethod
    def compare_benchmarks(
        cls,
        current_benchmarks: List[Any],
        baseline_filepath: str = "reports/baseline.json",
        thpt_drop_threshold_pct: float = 10.0,
        lat_increase_threshold_pct: float = 15.0,
        loss_increase_threshold_pct: float = 1.0
    ) -> List[PerformanceComparisonDiff]:
        """
        Compare current performance benchmark results against a saved baseline.
        """
        baseline_data = cls.load_baseline(baseline_filepath)
        if not baseline_data:
            logger.warning(f"No baseline found at {baseline_filepath} for benchmark comparison.")
            return []

        base_list = baseline_data.get("benchmarks", [])
        base_dict = {}
        for b in base_list:
            key = f"{b.get('test_name')}_{b.get('protocol')}_{b.get('packet_size', 0)}"
            base_dict[key] = b

        diffs: List[PerformanceComparisonDiff] = []
        base_ts = baseline_data.get("timestamp") or baseline_data.get("summary", {}).get("timestamp")

        for curr in current_benchmarks:
            c_dict = curr.to_dict() if hasattr(curr, "to_dict") else curr
            key = f"{c_dict.get('test_name')}_{c_dict.get('protocol')}_{c_dict.get('packet_size', 0)}"

            diff = PerformanceComparisonDiff(
                baseline_timestamp=base_ts,
                current_timestamp=c_dict.get("environment", {}).get("timestamp", datetime.now(timezone.utc).isoformat()),
                benchmark_name=c_dict.get("test_name", "benchmark"),
                protocol=c_dict.get("protocol", "TCP")
            )

            if key in base_dict:
                b_dict = base_dict[key]

                # 1. Throughput Comparison
                if "throughput" in c_dict and "throughput" in b_dict:
                    c_mbps = float(c_dict["throughput"].get("throughput_mbps", 0.0))
                    b_mbps = float(b_dict["throughput"].get("throughput_mbps", 0.0))
                    diff.throughput_current_mbps = c_mbps
                    diff.throughput_baseline_mbps = b_mbps
                    if b_mbps > 0:
                        delta = ((c_mbps - b_mbps) / b_mbps) * 100.0
                        diff.throughput_delta_pct = round(delta, 2)
                        if delta < -thpt_drop_threshold_pct:
                            diff.is_regression = True
                            diff.regression_reasons.append(f"Throughput dropped by {abs(delta):.1f}% (threshold: {thpt_drop_threshold_pct}%)")

                # 2. Latency Comparison
                if "latency" in c_dict and "latency" in b_dict:
                    c_lat = float(c_dict["latency"].get("avg_ms", 0.0))
                    b_lat = float(b_dict["latency"].get("avg_ms", 0.0))
                    diff.latency_current_ms = c_lat
                    diff.latency_baseline_ms = b_lat
                    if b_lat > 0:
                        delta = ((c_lat - b_lat) / b_lat) * 100.0
                        diff.latency_delta_pct = round(delta, 2)
                        if delta > lat_increase_threshold_pct:
                            diff.is_regression = True
                            diff.regression_reasons.append(f"Latency increased by {delta:.1f}% (threshold: {lat_increase_threshold_pct}%)")

                # 3. Packet Loss Comparison
                if "packet_loss" in c_dict and "packet_loss" in b_dict:
                    c_loss = float(c_dict["packet_loss"].get("packet_loss_percent", 0.0))
                    b_loss = float(b_dict["packet_loss"].get("packet_loss_percent", 0.0))
                    diff.loss_current_pct = c_loss
                    diff.loss_baseline_pct = b_loss
                    loss_diff = c_loss - b_loss
                    diff.loss_delta_pct = round(loss_diff, 2)
                    if loss_diff > loss_increase_threshold_pct:
                        diff.is_regression = True
                        diff.regression_reasons.append(f"Packet loss increased by {loss_diff:.2f}% (threshold: {loss_increase_threshold_pct}%)")

                # 4. Jitter Comparison
                if "jitter" in c_dict and "jitter" in b_dict:
                    c_j = float(c_dict["jitter"].get("average_jitter_ms", 0.0))
                    b_j = float(b_dict["jitter"].get("average_jitter_ms", 0.0))
                    diff.jitter_current_ms = c_j
                    diff.jitter_baseline_ms = b_j
                    if b_j > 0:
                        diff.jitter_delta_pct = round(((c_j - b_j) / b_j) * 100.0, 2)

            diffs.append(diff)

        return diffs


class PerformanceTrendTracker:
    """
    Appends and tracks benchmark results over time for historical trending.
    """

    @staticmethod
    def record_benchmarks(benchmarks: List[Any], filepath: str = "reports/history.json") -> Path:
        """Record benchmark metrics into historical JSON dataset."""
        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        history: List[Dict[str, Any]] = []

        if target.exists():
            try:
                with open(target, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []

        ts = datetime.now(timezone.utc).isoformat()
        env = EnvironmentMetadata.capture()

        for b in benchmarks:
            b_dict = b.to_dict() if hasattr(b, "to_dict") else b
            entry = {
                "timestamp": ts,
                "git_commit": env.git_commit,
                "hostname": env.hostname,
                "os": env.os,
                "test_name": b_dict.get("test_name"),
                "protocol": b_dict.get("protocol"),
                "packet_size": b_dict.get("packet_size", 0),
                "duration_seconds": b_dict.get("duration_seconds", 0.0),
                "throughput_mbps": b_dict.get("throughput", {}).get("throughput_mbps") if b_dict.get("throughput") else None,
                "latency_avg_ms": b_dict.get("latency", {}).get("avg_ms") if b_dict.get("latency") else None,
                "latency_p95_ms": b_dict.get("latency", {}).get("p95_ms") if b_dict.get("latency") else None,
                "packet_loss_percent": b_dict.get("packet_loss", {}).get("packet_loss_percent") if b_dict.get("packet_loss") else None,
                "jitter_ms": b_dict.get("jitter", {}).get("average_jitter_ms") if b_dict.get("jitter") else None,
            }
            history.append(entry)

        with open(target, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

        logger.info(f"Updated benchmark history at {target} ({len(history)} entries total)")
        return target


class TestReportGenerator:
    """
    Exports multi-format reports: JSON, CSV, JUnit XML, Markdown, and Executive HTML Dashboards.
    """

    @staticmethod
    def export_csv_reports(suite_result: SuiteResult) -> Tuple[Path, Path]:
        """Export test results and benchmarks to CSV files."""
        Path("reports").mkdir(exist_ok=True)
        results_csv = Path("reports/results.csv")
        benchmarks_csv = Path("reports/benchmarks.csv")

        # 1. results.csv
        with open(results_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Test Name", "Protocol", "Status", "Duration (ms)", "Retries", "Timestamp", "Error"])
            for r in suite_result.results:
                writer.writerow([r.test_name, r.protocol, r.status.value, f"{r.duration_ms:.2f}", r.retries, r.timestamp, r.error or ""])

        # 2. benchmarks.csv
        with open(benchmarks_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Benchmark", "Protocol", "Packet Size", "Throughput (Mbps)", "Latency Avg (ms)", "Latency P95 (ms)", "Packet Loss %", "Jitter (ms)", "Status"])
            for b in suite_result.performance_benchmarks:
                writer.writerow([
                    b.get("test_name", ""),
                    b.get("protocol", ""),
                    b.get("packet_size", 0),
                    f"{b['throughput']['throughput_mbps']:.2f}" if b.get("throughput") else "",
                    f"{b['latency']['avg_ms']:.4f}" if b.get("latency") else "",
                    f"{b['latency']['p95_ms']:.4f}" if b.get("latency") else "",
                    f"{b['packet_loss']['packet_loss_percent']:.2f}" if b.get("packet_loss") else "",
                    f"{b['jitter']['average_jitter_ms']:.4f}" if b.get("jitter") else "",
                    b.get("status", "PASS")
                ])

        return results_csv, benchmarks_csv

    @staticmethod
    def generate_html_performance_report(
        benchmarks: List[Any],
        diffs: Optional[List[PerformanceComparisonDiff]] = None,
        output_path: str = "reports/performance_report.html"
    ) -> Path:
        """Generate standalone HTML performance report."""
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        bench_dicts = [b.to_dict() if hasattr(b, "to_dict") else b for b in benchmarks]
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        tcp_thpt = [b["throughput"]["throughput_mbps"] for b in bench_dicts if b.get("throughput") and "TCP" in b.get("protocol", "")]
        udp_loss = [b["packet_loss"]["packet_loss_percent"] for b in bench_dicts if b.get("packet_loss")]
        avg_lat = [b["latency"]["avg_ms"] for b in bench_dicts if b.get("latency")]
        avg_jitter = [b["jitter"]["average_jitter_ms"] for b in bench_dicts if b.get("jitter")]

        top_thpt = max(tcp_thpt) if tcp_thpt else 0.0
        mean_lat = sum(avg_lat) / len(avg_lat) if avg_lat else 0.0
        mean_loss = sum(udp_loss) / len(udp_loss) if udp_loss else 0.0
        mean_j = sum(avg_jitter) / len(avg_jitter) if avg_jitter else 0.0

        rows = []
        for b in bench_dicts:
            test_name = b.get("test_name", "")
            proto = b.get("protocol", "")
            size = b.get("packet_size", 0)
            thpt = f"{b['throughput']['throughput_mbps']:.2f} Mbps" if b.get("throughput") else "-"
            lat = f"{b['latency']['avg_ms']:.4f} ms (p95: {b['latency']['p95_ms']:.4f})" if b.get("latency") else "-"
            loss = f"{b['packet_loss']['packet_loss_percent']:.2f}%" if b.get("packet_loss") else "-"
            jitter = f"{b['jitter']['average_jitter_ms']:.4f} ms" if b.get("jitter") else "-"
            status = b.get("status", "PASS")
            badge_class = "badge-pass" if status == "PASS" else "badge-fail"

            rows.append(f"""
            <tr>
                <td><strong>{test_name}</strong></td>
                <td><span class="badge badge-proto">{proto}</span></td>
                <td>{size} B</td>
                <td class="metric-val">{thpt}</td>
                <td class="metric-val">{lat}</td>
                <td class="metric-val">{loss}</td>
                <td class="metric-val">{jitter}</td>
                <td><span class="badge {badge_class}">{status}</span></td>
            </tr>
            """)

        diff_section = ""
        if diffs:
            diff_rows = []
            for d in diffs:
                thpt_diff = f"{d.throughput_delta_pct:+.1f}%" if d.throughput_delta_pct is not None else "-"
                lat_diff = f"{d.latency_delta_pct:+.1f}%" if d.latency_delta_pct is not None else "-"
                loss_diff = f"{d.loss_delta_pct:+.2f}%" if d.loss_delta_pct is not None else "-"
                reg_badge = '<span class="badge badge-fail">REGRESSION</span>' if d.is_regression else '<span class="badge badge-pass">HEALTHY</span>'
                notes = ", ".join(d.regression_reasons) if d.regression_reasons else "Normal variance"

                diff_rows.append(f"""
                <tr>
                    <td><strong>{d.benchmark_name}</strong> ({d.protocol})</td>
                    <td>{thpt_diff}</td>
                    <td>{lat_diff}</td>
                    <td>{loss_diff}</td>
                    <td>{reg_badge}</td>
                    <td><small>{notes}</small></td>
                </tr>
                """)

            diff_section = f"""
            <div class="card">
                <h2>Baseline Regression Comparison</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Benchmark</th>
                            <th>Throughput Change</th>
                            <th>Latency Change</th>
                            <th>Loss Change</th>
                            <th>Status</th>
                            <th>Notes</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(diff_rows)}
                    </tbody>
                </table>
            </div>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NetPulse Performance Report</title>
    <style>
        :root {{
            --bg: #0f172a;
            --card-bg: #1e293b;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
            --primary: #38bdf8;
            --accent: #818cf8;
            --success: #34d399;
            --danger: #f87171;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background-color: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 2rem; line-height: 1.5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{ margin-bottom: 2rem; border-bottom: 1px solid var(--border); padding-bottom: 1rem; }}
        h1 {{ font-size: 2rem; color: var(--primary); margin-bottom: 0.5rem; }}
        .timestamp {{ color: var(--text-muted); font-size: 0.9rem; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
        .card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; margin-bottom: 2rem; }}
        .stat-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem; }}
        .stat-label {{ font-size: 0.85rem; text-transform: uppercase; color: var(--text-muted); }}
        .stat-value {{ font-size: 1.75rem; font-weight: 700; color: var(--primary); margin-top: 0.25rem; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
        th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--border); }}
        th {{ background-color: #0f172a; color: var(--text-muted); font-size: 0.85rem; text-transform: uppercase; }}
        tr:hover {{ background-color: rgba(255, 255, 255, 0.02); }}
        .metric-val {{ font-family: ui-monospace, SFMono-Regular, monospace; }}
        .badge {{ display: inline-block; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }}
        .badge-proto {{ background: #0369a1; color: #e0f2fe; }}
        .badge-pass {{ background: #065f46; color: #a7f3d0; }}
        .badge-fail {{ background: #991b1b; color: #fecaca; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>NetPulse Network Performance Dashboard</h1>
            <div class="timestamp">Generated: {ts} | Environment: Localhost (127.0.0.1)</div>
        </header>

        <div class="grid">
            <div class="stat-card">
                <div class="stat-label">Peak TCP Throughput</div>
                <div class="stat-value">{top_thpt:.1f} <span style="font-size: 1rem; font-weight: 400;">Mbps</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Mean Round-Trip Latency</div>
                <div class="stat-value">{mean_lat:.4f} <span style="font-size: 1rem; font-weight: 400;">ms</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Average UDP Packet Loss</div>
                <div class="stat-value">{mean_loss:.2f} <span style="font-size: 1rem; font-weight: 400;">%</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Mean Inter-Arrival Jitter</div>
                <div class="stat-value">{mean_j:.4f} <span style="font-size: 1rem; font-weight: 400;">ms</span></div>
            </div>
        </div>

        <div class="card">
            <h2>Performance Benchmark Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Benchmark</th>
                        <th>Protocol</th>
                        <th>Packet Size</th>
                        <th>Throughput</th>
                        <th>Latency (Avg / P95)</th>
                        <th>Packet Loss</th>
                        <th>Jitter</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>

        {diff_section}
    </div>
</body>
</html>
"""
        with open(target, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Generated HTML performance report at {target}")
        return target

    @staticmethod
    def generate_executive_dashboard(
        suite_result: SuiteResult,
        output_path: str = "reports/dashboard.html"
    ) -> Path:
        """
        Generate a comprehensive executive HTML dashboard combining functional tests,
        performance benchmarks, flaky test intelligence, and defect-style failure reports.
        """
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        summary = suite_result.get_summary()
        env = suite_result.environment_info or EnvironmentMetadata.capture().to_dict()

        defects = DefectManager.all_defects()
        flaky_summary = FlakyTracker.get_summary(total_tests_executed=summary["total_tests"])

        # Protocol Breakdown Counts
        proto_stats: Dict[str, Dict[str, int]] = {}
        for r in suite_result.results:
            p = r.protocol
            if p not in proto_stats:
                proto_stats[p] = {"pass": 0, "fail": 0, "skip": 0}
            if r.status == TestStatus.PASS:
                proto_stats[p]["pass"] += 1
            elif r.status == TestStatus.SKIPPED:
                proto_stats[p]["skip"] += 1
            else:
                proto_stats[p]["fail"] += 1

        proto_cards = []
        for p, s in proto_stats.items():
            stat_str = "PASS" if s["fail"] == 0 else f"{s['fail']} FAIL"
            b_class = "badge-pass" if s["fail"] == 0 else "badge-fail"
            proto_cards.append(f"""
            <div class="stat-card">
                <div class="stat-label">{p} Protocol</div>
                <div class="stat-value" style="font-size: 1.25rem;">{s['pass']} Passed <span class="badge {b_class}">{stat_str}</span></div>
            </div>
            """)

        # Defects table
        defect_section = ""
        if defects:
            d_rows = []
            for d in defects:
                d_rows.append(f"""
                <tr>
                    <td><code>{d.test_id}</code></td>
                    <td><strong>{d.test_name}</strong></td>
                    <td><span class="badge badge-proto">{d.protocol}</span></td>
                    <td><span class="badge badge-fail">{d.severity}</span></td>
                    <td><code>{d.exception_type or 'AssertionError'}: {d.exception_message or 'Failed'}</code></td>
                </tr>
                """)
            defect_section = f"""
            <div class="card" style="border-left: 4px solid var(--danger);">
                <h2 style="color: var(--danger);">Active Test Defects ({len(defects)})</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Test ID</th>
                            <th>Test Name</th>
                            <th>Protocol</th>
                            <th>Severity</th>
                            <th>Diagnostic Message</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(d_rows)}
                    </tbody>
                </table>
            </div>
            """

        # Full Test Results Table
        test_rows = []
        for r in suite_result.results:
            status_icon = "badge-pass" if r.status == TestStatus.PASS else ("badge-fail" if r.status == TestStatus.FAIL else "badge-proto")
            test_rows.append(f"""
            <tr>
                <td><code>{r.test_name}</code></td>
                <td><span class="badge badge-proto">{r.protocol}</span></td>
                <td>{r.duration_ms:.2f} ms</td>
                <td><span class="badge {status_icon}">{r.status.value}</span></td>
                <td><small>{r.error or '-'}</small></td>
            </tr>
            """)

        dashboard_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NetPulse Executive Dashboard</title>
    <style>
        :root {{
            --bg: #0b1120;
            --card-bg: #1e293b;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
            --primary: #38bdf8;
            --success: #34d399;
            --danger: #f87171;
            --warning: #fbbf24;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background-color: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 2rem; line-height: 1.5; }}
        .container {{ max-width: 1300px; margin: 0 auto; }}
        header {{ margin-bottom: 2rem; border-bottom: 1px solid var(--border); padding-bottom: 1.5rem; }}
        h1 {{ font-size: 2.2rem; color: var(--primary); font-weight: 800; }}
        .env-bar {{ display: flex; gap: 1.5rem; margin-top: 0.5rem; color: var(--text-muted); font-size: 0.85rem; flex-wrap: wrap; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
        .card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; margin-bottom: 2rem; }}
        .stat-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem; }}
        .stat-label {{ font-size: 0.8rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.05em; }}
        .stat-value {{ font-size: 1.8rem; font-weight: 700; color: var(--primary); margin-top: 0.25rem; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
        th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--border); }}
        th {{ background-color: #0b1120; color: var(--text-muted); font-size: 0.8rem; text-transform: uppercase; }}
        tr:hover {{ background-color: rgba(255, 255, 255, 0.02); }}
        .badge {{ display: inline-block; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }}
        .badge-proto {{ background: #0369a1; color: #e0f2fe; }}
        .badge-pass {{ background: #065f46; color: #a7f3d0; }}
        .badge-fail {{ background: #991b1b; color: #fecaca; }}
        .badge-warn {{ background: #78350f; color: #fde68a; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>NetPulse Executive Test & Regression Dashboard</h1>
            <div class="env-bar">
                <span><strong>Execution:</strong> {ts}</span>
                <span><strong>OS:</strong> {env.get('os', 'Unknown')}</span>
                <span><strong>Python:</strong> {env.get('python_version', '3.11+')}</span>
                <span><strong>Commit:</strong> <code>{env.get('git_commit', 'unknown')}</code></span>
                <span><strong>Host:</strong> {env.get('hostname', 'localhost')}</span>
            </div>
        </header>

        <div class="grid">
            <div class="stat-card">
                <div class="stat-label">Total Tests</div>
                <div class="stat-value">{summary['total_tests']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Pass Rate</div>
                <div class="stat-value" style="color: var(--success);">{summary['pass_rate_pct']}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Stable Tests</div>
                <div class="stat-value">{flaky_summary['stable_count']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Flaky Tests</div>
                <div class="stat-value" style="color: {'var(--warning)' if flaky_summary['flaky_count'] > 0 else 'var(--text-muted)'};">{flaky_summary['flaky_count']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Defects / Failed</div>
                <div class="stat-value" style="color: {'var(--danger)' if summary['failed'] > 0 else 'var(--success)'};">{summary['failed']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Duration</div>
                <div class="stat-value" style="font-size: 1.4rem;">{summary['total_duration_ms'] / 1000.0:.2f}s</div>
            </div>
        </div>

        <h3 style="margin-bottom: 1rem; color: var(--text-muted); text-transform: uppercase; font-size: 0.85rem;">Protocol Health Status</h3>
        <div class="grid">
            {''.join(proto_cards)}
        </div>

        {defect_section}

        <div class="card">
            <h2>Complete Automated Test Execution Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Test Case Node ID</th>
                        <th>Protocol</th>
                        <th>Execution Time</th>
                        <th>Status</th>
                        <th>Diagnostics / Error</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(test_rows)}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
        with open(target, "w", encoding="utf-8") as f:
            f.write(dashboard_html)

        # Also write to report.html as default alias
        with open("reports/report.html", "w", encoding="utf-8") as f:
            f.write(dashboard_html)

        logger.info(f"Generated Executive HTML Dashboard at {target}")
        return target
