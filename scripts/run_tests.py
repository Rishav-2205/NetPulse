"""
NetPulse CLI Test Runner & Baseline Orchestration Utility.

Allows running test suites by profile, marker, generating HTML/JSON/JUnit reports,
and conducting baseline regression comparisons with rich terminal formatting.
"""

import argparse
import os
from pathlib import Path
import subprocess
import sys
from typing import List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from app.core.config import ConfigManager
from app.core.result import SuiteResult, TestResult, TestStatus
from app.reporting.results import BaselineManager, TestReportGenerator

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="NetPulse: Automated Network Validation & Performance Testing CLI"
    )
    parser.add_argument(
        "--profile",
        "-p",
        default="default",
        help="Configuration profile (default, fast, stress, ci, regression, debug)"
    )
    parser.add_argument(
        "-m",
        "--marker",
        default=None,
        help="Pytest marker filter (e.g., tcp, udp, http, functional, regression, unit)"
    )
    parser.add_argument(
        "-k",
        "--keyword",
        default=None,
        help="Pytest expression filter for test names"
    )
    parser.add_argument(
        "--generate-baseline",
        action="store_true",
        help="Save test results as the official regression baseline in reports/baseline.json"
    )
    parser.add_argument(
        "--compare-baseline",
        action="store_true",
        help="Compare current results against reports/baseline.json and flag regressions"
    )
    parser.add_argument(
        "--baseline-path",
        default="reports/baseline.json",
        help="Path to baseline JSON file (default: reports/baseline.json)"
    )
    parser.add_argument(
        "--html",
        action="store_true",
        default=True,
        help="Generate standalone HTML report in reports/report.html"
    )
    parser.add_argument(
        "--junit",
        action="store_true",
        default=True,
        help="Generate JUnit XML report in reports/junit.xml"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose test execution"
    )
    parser.add_argument(
        "test_paths",
        nargs="*",
        default=["tests"],
        help="Specific test directories or files to execute"
    )
    return parser.parse_args()


def display_results_table(suite: SuiteResult) -> None:
    """Print a clean summary table using Rich."""
    table = Table(title=f"NetPulse Execution Results: {suite.suite_name}", border_style="bright_blue")
    table.add_column("Protocol", style="cyan", no_wrap=True)
    table.add_column("Test Case", style="white")
    table.add_column("Status", justify="center")
    table.add_column("Duration (ms)", justify="right", style="magenta")

    for r in suite.results:
        if r.status == TestStatus.PASS:
            status_str = "[bold green]PASS[/bold green]"
        elif r.status == TestStatus.FAIL:
            status_str = "[bold red]FAIL[/bold red]"
        elif r.status == TestStatus.ERROR:
            status_str = "[bold yellow]ERROR[/bold yellow]"
        else:
            status_str = "[dim white]SKIPPED[/dim white]"

        # Truncate test name for clean table display
        short_name = r.test_name.split("::")[-1]
        table.add_row(r.protocol, short_name, status_str, f"{r.duration_ms:.2f}")

    console.print(table)

    summary = suite.get_summary()
    summary_panel = Panel(
        f"[bold]Total Tests:[/bold] {summary['total_tests']} | "
        f"[bold green]Passed:[/bold green] {summary['passed']} | "
        f"[bold red]Failed:[/bold red] {summary['failed']} | "
        f"[bold yellow]Errors:[/bold yellow] {summary['errors']} | "
        f"[bold]Pass Rate:[/bold] {summary['pass_rate_pct']}% | "
        f"[bold magenta]Total Duration:[/bold magenta] {summary['total_duration_ms']:.2f}ms",
        title="[bold green]Suite Execution Summary[/bold green]" if summary['failed'] == 0 else "[bold red]Suite Execution Summary[/bold red]",
        border_style="green" if summary['failed'] == 0 else "red"
    )
    console.print(summary_panel)


def main() -> int:
    args = parse_args()

    # Load configuration
    try:
        cfg = ConfigManager.load(profile=args.profile if args.profile != "default" else None)
        console.print(f"[bold cyan]Loaded NetPulse configuration profile:[/bold cyan] [yellow]{args.profile}[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Configuration error:[/bold red] {e}")
        return 1

    # Ensure output directories exist
    reports_dir = WORKSPACE_ROOT / "reports"
    logs_dir = WORKSPACE_ROOT / "logs"
    reports_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)

    # Assemble pytest CLI arguments
    pytest_cmd = [sys.executable, "-m", "pytest"]

    if args.verbose:
        pytest_cmd.append("-v")

    if args.marker:
        pytest_cmd.extend(["-m", args.marker])

    if args.keyword:
        pytest_cmd.extend(["-k", args.keyword])

    if args.html:
        html_file = str(reports_dir / "report.html")
        pytest_cmd.extend([f"--html={html_file}", "--self-contained-html"])

    if args.junit:
        junit_file = str(reports_dir / "junit.xml")
        pytest_cmd.append(f"--junitxml={junit_file}")

    # JSON report plugin
    results_json = str(reports_dir / "results.json")
    pytest_cmd.extend([f"--json-report", f"--json-report-file={results_json}"])

    pytest_cmd.extend(args.test_paths)

    console.print(f"[bold blue]Running command:[/bold blue] {' '.join(pytest_cmd)}\n")
    exit_code = subprocess.call(pytest_cmd, cwd=str(WORKSPACE_ROOT))

    # Read collected results
    collected_results = BaselineManager.load_baseline(results_json)
    if collected_results and "tests" in collected_results:
        suite = SuiteResult(
            suite_name=f"NetPulse Test Run (Profile: {args.profile})",
            timestamp=collected_results.get("summary", {}).get("timestamp", ""),
            results=[TestResult.from_dict(t) for t in collected_results.get("tests", [])]
        )
        display_results_table(suite)

        # Baseline Handling
        if args.generate_baseline:
            saved_path = BaselineManager.save_baseline(suite, args.baseline_path)
            console.print(f"[bold green]Official baseline saved to:[/bold green] {saved_path}")

        if args.compare_baseline:
            diff = BaselineManager.compare_against_baseline(suite, args.baseline_path)
            if diff.has_regressions:
                console.print("\n[bold red]REGRESSIONS DETECTED AGAINST BASELINE:[/bold red]")
                for reg in diff.status_regressions:
                    console.print(f"  - [red]{reg['test_name']}[/red]: {reg['baseline_status']} -> {reg['current_status']}")
                for perf in diff.performance_regressions:
                    console.print(f"  - [yellow]{perf['test_name']}[/yellow]: +{perf['increase_pct']}% latency increase ({perf['baseline_duration_ms']}ms -> {perf['current_duration_ms']}ms)")
            else:
                console.print("\n[bold green]No regressions detected against baseline.[/bold green]")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
