"""
NetPulse Standard Fault Profiles & Profile Registry.

Provides pre-defined and user-customizable fault profiles for deterministic network experiments.
"""

from typing import Dict, List, Optional
import yaml
from pathlib import Path

from app.faults.models import FaultConfig, FaultProfile, FaultType


BUILTIN_PROFILES: Dict[str, FaultProfile] = {
    "clean": FaultProfile(
        name="clean",
        config=FaultConfig(
            fault_type=FaultType.CLEAN,
            latency_ms=0.0,
            jitter_ms=0.0,
            packet_loss_percent=0.0,
            bandwidth_mbps=None,
            description="Clean baseline channel (no impairment)"
        ),
        tags=["baseline", "clean"]
    ),
    "high_latency": FaultProfile(
        name="high_latency",
        config=FaultConfig(
            fault_type=FaultType.LATENCY,
            latency_ms=100.0,
            jitter_ms=5.0,
            packet_loss_percent=0.0,
            bandwidth_mbps=None,
            description="High latency channel (100ms RTT delay, ±5ms jitter)"
        ),
        tags=["latency", "wan"]
    ),
    "lossy": FaultProfile(
        name="lossy",
        config=FaultConfig(
            fault_type=FaultType.LOSS,
            latency_ms=20.0,
            jitter_ms=5.0,
            packet_loss_percent=2.0,
            bandwidth_mbps=None,
            description="Lossy wireless/satellite channel (20ms delay, 2% loss)"
        ),
        tags=["loss", "wireless"]
    ),
    "constrained": FaultProfile(
        name="constrained",
        config=FaultConfig(
            fault_type=FaultType.BANDWIDTH,
            latency_ms=20.0,
            jitter_ms=5.0,
            packet_loss_percent=1.0,
            bandwidth_mbps=50.0,
            description="Bandwidth constrained link (50 Mbps rate limit, 20ms delay, 1% loss)"
        ),
        tags=["bandwidth", "rate_limit", "combined"]
    ),
    "jittery": FaultProfile(
        name="jittery",
        config=FaultConfig(
            fault_type=FaultType.JITTER,
            latency_ms=30.0,
            jitter_ms=15.0,
            packet_loss_percent=0.0,
            bandwidth_mbps=None,
            description="High jitter delay variation channel (30ms base ± 15ms variation)"
        ),
        tags=["jitter", "cellular"]
    ),
    "severe_loss": FaultProfile(
        name="severe_loss",
        config=FaultConfig(
            fault_type=FaultType.LOSS,
            latency_ms=10.0,
            jitter_ms=2.0,
            packet_loss_percent=10.0,
            bandwidth_mbps=None,
            description="Severely degraded link with 10% packet drop rate"
        ),
        tags=["loss", "degraded"]
    ),
}


class FaultProfileRegistry:
    """
    Registry for resolving, loading, and listing named fault profiles.
    """

    _custom_profiles: Dict[str, FaultProfile] = {}

    @classmethod
    def get_profile(cls, name: str) -> Optional[FaultProfile]:
        """Retrieve a fault profile by name (checking custom first, then builtins)."""
        key = name.lower()
        if key in cls._custom_profiles:
            return cls._custom_profiles[key]
        return BUILTIN_PROFILES.get(key)

    @classmethod
    def list_profiles(cls) -> List[FaultProfile]:
        """List all available fault profiles."""
        combined = {**BUILTIN_PROFILES, **cls._custom_profiles}
        return list(combined.values())

    @classmethod
    def register_profile(cls, profile: FaultProfile) -> None:
        """Register a new custom fault profile."""
        cls._custom_profiles[profile.name.lower()] = profile

    @classmethod
    def load_from_yaml(cls, yaml_path: str) -> None:
        """Load custom fault profiles from a YAML configuration file."""
        path = Path(yaml_path)
        if not path.exists():
            return
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        profiles_data = data.get("profiles", {})
        for name, p_cfg in profiles_data.items():
            cfg = FaultConfig(
                fault_type=FaultType.COMBINED if (p_cfg.get("latency_ms", 0) and p_cfg.get("packet_loss_percent", 0)) else FaultType.CLEAN,
                latency_ms=float(p_cfg.get("latency_ms", 0.0)),
                jitter_ms=float(p_cfg.get("jitter_ms", 0.0)),
                packet_loss_percent=float(p_cfg.get("packet_loss_percent", 0.0)),
                bandwidth_mbps=float(p_cfg["bandwidth_mbps"]) if p_cfg.get("bandwidth_mbps") is not None else None,
                corruption_percent=float(p_cfg.get("corruption_percent", 0.0)),
                description=p_cfg.get("description", f"Custom profile '{name}'")
            )
            cls.register_profile(FaultProfile(name=name, config=cfg, tags=p_cfg.get("tags", ["custom"])))
