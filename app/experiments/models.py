"""
NetPulse Network Experiment Data Models.

Defines specs, control vs. experiment telemetry observations, impact comparisons,
and experimental degradation classifications.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from app.faults.models import FaultConfig
from app.performance.metrics import EnvironmentMetadata


class DegradationClassification(str, Enum):
    """Classification of experimental outcome."""
    EXPECTED_DEGRADATION = "EXPECTED_DEGRADATION"  # Performance decreased due to intentional fault
    UNEXPECTED_REGRESSION = "UNEXPECTED_REGRESSION"  # Performance decreased more than tolerated beyond the fault
    NO_SIGNIFICANT_CHANGE = "NO_SIGNIFICANT_CHANGE"  # Performance within tolerance
    IMPROVEMENT = "IMPROVEMENT"                    # Performance unexpectedly improved
    TEST_FAILURE = "TEST_FAILURE"                  # Protocol error or execution exception


@dataclass
class ObservationMetrics:
    """Observed network metrics for a single experimental phase."""
    throughput_mbps: Optional[float] = None
    latency_avg_ms: Optional[float] = None
    latency_p95_ms: Optional[float] = None
    packet_loss_percent: Optional[float] = None
    jitter_avg_ms: Optional[float] = None
    total_packets_sent: int = 0
    total_packets_received: int = 0
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExperimentImpact:
    """Calculated delta metrics comparing Control vs Experiment."""
    throughput_delta_mbps: Optional[float] = None
    throughput_delta_pct: Optional[float] = None

    latency_delta_ms: Optional[float] = None
    latency_delta_pct: Optional[float] = None

    loss_delta_pct: Optional[float] = None
    jitter_delta_ms: Optional[float] = None
    jitter_delta_pct: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExperimentResult:
    """Complete experimental result capturing Control vs Experiment observations and classification."""
    experiment_id: str
    name: str
    protocol: str
    topology: str
    fault_profile: str
    fault_config: FaultConfig

    control_observation: ObservationMetrics
    experiment_observation: ObservationMetrics
    impact: ExperimentImpact

    classification: DegradationClassification
    details: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    environment: EnvironmentMetadata = field(default_factory=EnvironmentMetadata.capture)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["classification"] = self.classification.value if isinstance(self.classification, Enum) else str(self.classification)
        return data
