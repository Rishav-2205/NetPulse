"""
NetPulse Fault Injection Data Models.

Defines network impairments, fault types, and configuration profiles for latency,
loss, jitter, bandwidth rate limiting, and corruption.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class FaultType(str, Enum):
    """Classification of network impairments."""
    CLEAN = "CLEAN"
    LATENCY = "LATENCY"
    LOSS = "LOSS"
    JITTER = "JITTER"
    BANDWIDTH = "BANDWIDTH"
    CORRUPTION = "CORRUPTION"
    DISCONNECTED = "DISCONNECTED"
    COMBINED = "COMBINED"


@dataclass
class FaultConfig:
    """Detailed parameters defining a network fault or impairment."""
    fault_type: FaultType = FaultType.CLEAN
    latency_ms: float = 0.0
    jitter_ms: float = 0.0
    correlation_pct: float = 0.0
    packet_loss_percent: float = 0.0
    bandwidth_mbps: Optional[float] = None
    corruption_percent: float = 0.0
    description: str = "Clean channel (no impairment)"

    def is_clean(self) -> bool:
        """Return True if all impairment parameters are zero / inactive."""
        return (
            self.latency_ms == 0.0
            and self.jitter_ms == 0.0
            and self.packet_loss_percent == 0.0
            and self.bandwidth_mbps is None
            and self.corruption_percent == 0.0
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["fault_type"] = self.fault_type.value if isinstance(self.fault_type, Enum) else str(self.fault_type)
        return data


@dataclass
class FaultProfile:
    """Named profile grouping standard test impairment configurations."""
    name: str
    config: FaultConfig
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "config": self.config.to_dict(),
            "tags": self.tags,
        }
