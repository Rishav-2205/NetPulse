#!/usr/bin/env python3
"""
NetPulse End-to-End Demonstration Script.

Executes a complete clean-room demonstration workflow:
1. Environment & capability inspection
2. Automated functional test suite execution
3. Performance smoke benchmarks (Throughput, Latency, Loss, Jitter)
4. Intelligent regression comparison against baseline
5. Flaky test evaluation & defect tracking
6. Multi-format report export (Executive Dashboard HTML, JSON, CSV, XML)
"""

import json
from pathlib import Path
import subprocess
import sys
import time
from typing import List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console(force_terminal=True, legacy_windows=False)


def section_header(title: str, step: int, total_steps: int = 6) -> None:
    console.print(f"\n[bold cyan]Step {step}/{total_steps}: {title}[/bold cyan]")
    console.print("=" * 60)


def run_cmd(cmd: List[str], description: str) -> int:
    console.print(f"[dim]Executing: {' '.join(cmd)}[/dim]")
    start = time.perf_counter()
    code = subprocess.call(cmd)
    elapsed = time.perf_counter() - start
    if code == 0:
        console.print(f"[bold green][PASS] {description} completed in {elapsed:.2f}s[/bold green]")
    else:
        console.print(f"[bold red][FAIL] {description} failed with exit code {code}[/bold red]")
    return code


def main() -> int:
    console.print(Panel(
        "[bold white on blue] NetPulse: Automated Network Validation & Performance Framework [/bold white on blue]\n"
        "[bold cyan]End-to-End Demonstration & Clean-Room Verification[/bold cyan]",
        border_style="blue"
    ))

    total_steps = 6

    # 1. Environment & Capability Check
    section_header("Environment & Capability Inspection", 1, total_steps)
    from app.packets.capture import has_raw_socket_capability
    from app.performance.metrics import EnvironmentMetadata

    env = EnvironmentMetadata.capture()
    priv_status = "Privileged (CAP_NET_RAW / WinPcap)" if has_raw_socket_capability() else "Unprivileged (Simulated Fallback)"

    env_table = Table(border_style="cyan")
    env_table.add_column("Property", style="cyan")
    env_table.add_column("Value", style="bold")
    env_table.add_row("Operating System", env.os)
    env_table.add_row("Python Version", env.python_version)
    env_table.add_row("CPU Core Count", str(env.cpu_count))
    env_table.add_row("Git Commit", env.git_commit)
    env_table.add_row("Socket Privilege", priv_status)
    console.print(env_table)

    # 2. Automated Functional Test Suites
    section_header("Executing Functional & Regression Test Suites", 2, total_steps)
    test_code = run_cmd(
        [sys.executable, "-m", "pytest", "tests/functional", "tests/regression", "tests/integration", "-v"],
        "Functional & Regression Tests"
    )
    if test_code != 0:
        return test_code

    # 3. Performance Smoke Benchmarks
    section_header("Running Network Performance Benchmarks", 3, total_steps)
    bench_code = run_cmd(
        [sys.executable, "-m", "netpulse", "benchmark", "--profile", "quick", "--compare-baseline", "--html"],
        "Performance Benchmarks (Throughput, Latency, Loss, Jitter)"
    )
    if bench_code != 0:
        return bench_code

    # 4. Test Case Management Catalog
    section_header("Exporting Test Case Catalog & Traceability Matrix", 4, total_steps)
    cat_code = run_cmd(
        [sys.executable, "-m", "netpulse", "catalog"],
        "Test Case Taxonomy Export"
    )
    if cat_code != 0:
        return cat_code

    # 5. Flaky Test Intelligence & Defect Report
    section_header("Evaluating Stability, Flakiness & Defects", 5, total_steps)
    flaky_file = Path("reports/flaky.json")
    defects_file = Path("reports/defects.json")

    if flaky_file.exists():
        with open(flaky_file, "r", encoding="utf-8") as f:
            flaky_data = json.load(f)
        console.print(f"Stability Stats: [green]{flaky_data.get('stable_count', 0)} Stable[/green], "
                      f"[yellow]{flaky_data.get('flaky_count', 0)} Flaky[/yellow], "
                      f"[red]{flaky_data.get('failed_count', 0)} Failed[/red]")

    if defects_file.exists():
        with open(defects_file, "r", encoding="utf-8") as f:
            defects_data = json.load(f)
        console.print(f"Active Defects Logged: [bold {'green' if len(defects_data) == 0 else 'red'}]{len(defects_data)} defects[/bold {'green' if len(defects_data) == 0 else 'red'}]")

    # 6. Report Artifacts Summary
    section_header("Generated Production-Grade Artifacts", 6, total_steps)
    report_code = run_cmd(
        [sys.executable, "-m", "netpulse", "report"],
        "Report Directory Inventory"
    )
    if report_code != 0:
        return report_code

    console.print(Panel(
        "[bold green][PASS] NetPulse Demonstration Workflow Completed Successfully![/bold green]\n"
        "[cyan]Executive Dashboard: reports/dashboard.html[/cyan]\n"
        "[cyan]Performance Report:  reports/performance_report.html[/cyan]",
        border_style="green"
    ))

    return 0


if __name__ == "__main__":
    sys.exit(main())
