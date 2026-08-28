"""
NetPulse Regression Threshold Configurations.

Defines configurable tolerance thresholds for functional regressions and performance metrics.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass
class RegressionThresholds:
    """
    Tolerance thresholds for regression detection.
    """
    throughput_drop_pct: float = 10.0          # Flag if throughput drops by > 10%
    latency_increase_pct: float = 15.0         # Flag if latency increases by > 15%
    packet_loss_increase_pct: float = 1.0      # Flag if packet loss increases by > 1.0%
    duration_increase_pct: float = 30.0        # Flag if test execution time increases by > 30%
    min_duration_ms: float = 5.0               # Ignore duration differences for microsecond-level fast tests

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegressionThresholds":
        return cls(
            throughput_drop_pct=float(data.get("throughput_drop_pct", 10.0)),
            latency_increase_pct=float(data.get("latency_increase_pct", 15.0)),
            packet_loss_increase_pct=float(data.get("packet_loss_increase_pct", 1.0)),
            duration_increase_pct=float(data.get("duration_increase_pct", 30.0)),
            min_duration_ms=float(data.get("min_duration_ms", 5.0)),
        )
