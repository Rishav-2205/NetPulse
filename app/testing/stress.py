"""
NetPulse High-Iteration Stress Test Runner.

Executes controlled, reproducible stress loops across core network primitives,
recording individual execution latencies, status outcomes, and generating
comprehensive statistical summaries in reports/stress_summary.json and reports/stress_history.csv.
"""

import csv
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any, Dict, List

from app.core.logging import get_logger
from app.networking.tcp import TCPClient, TCPServer
from app.networking.udp import UDPClient, UDPServer
from app.performance.statistics import StatisticalSeries

logger = get_logger("testing.stress")


@dataclass
class StressRunRecord:
    """Individual execution record in a stress test session."""
    iteration: int
    test_name: str
    status: str
    duration_ms: float
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StressRunner:
    """
    Executes high-iteration stress validation loops.
    """

    @classmethod
    def run_stress_test(
        cls,
        iterations: int = 50,
        profile: str = "quick",
        output_dir: str = "reports"
    ) -> Dict[str, Any]:
        """
        Execute stress test iterations across TCP/UDP roundtrips.
        """
        logger.info(f"Starting NetPulse Stress Test: {iterations} iterations (profile='{profile}')")
        records: List[StressRunRecord] = []
        durations: List[float] = []

        tcp_server = TCPServer(host="127.0.0.1", port=0)
        tcp_server.start()
        udp_server = UDPServer(host="127.0.0.1", port=0)
        udp_server.start()

        passed_count = 0
        failed_count = 0

        try:
            for i in range(1, iterations + 1):
                t0 = time.perf_counter()
                status = "PASS"
                try:
                    # Alternate between TCP echo and UDP echo
                    if i % 2 == 1:
                        client = TCPClient()
                        client.connect(tcp_server.host, tcp_server.port, timeout=0.5)
                        client.send_all(b"STRESS_TEST_PACKET_PING")
                        resp = client.receive_exact(len(b"STRESS_TEST_PACKET_PING"))
                        client.close()
                        if resp != b"STRESS_TEST_PACKET_PING":
                            status = "FAIL"
                    else:
                        u_client = UDPClient()
                        resp = u_client.send_and_receive(b"UDP_STRESS_PING", udp_server.host, udp_server.port, timeout=0.5)
                        u_client.close()
                        if resp != b"UDP_STRESS_PING":
                            status = "FAIL"

                except Exception as e:
                    logger.debug(f"Stress iteration {i} encountered error: {e}")
                    status = "FAIL"

                dur_ms = round((time.perf_counter() - t0) * 1000.0, 3)
                durations.append(dur_ms)

                if status == "PASS":
                    passed_count += 1
                else:
                    failed_count += 1

                records.append(
                    StressRunRecord(
                        iteration=i,
                        test_name="tcp_udp_stress_ping",
                        status=status,
                        duration_ms=dur_ms,
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
                )

        finally:
            tcp_server.stop()
            udp_server.stop()

        stats = StatisticalSeries.calculate(durations)

        summary = {
            "total_executions": iterations,
            "passed": passed_count,
            "failed": failed_count,
            "skipped": 0,
            "flaky": 0,
            "pass_rate_percent": round((passed_count / iterations) * 100.0, 2) if iterations > 0 else 0.0,
            "duration_statistics_ms": stats.to_dict() if stats else None,
            "profile": profile,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Export outputs
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        with open(out_path / "stress_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        with open(out_path / "stress_history.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["iteration", "test_name", "status", "duration_ms", "timestamp"])
            writer.writeheader()
            for r in records:
                writer.writerow(r.to_dict())

        logger.info(f"Stress test complete: {passed_count}/{iterations} passed. Summary saved to reports/stress_summary.json")
        return summary
