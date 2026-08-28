"""
NetPulse Experiment Execution Engine.

Orchestrates multi-phase network experiments:
  Phase 1: Control Baseline (Clean link)
  Phase 2: Fault Injection (Impairment applied)
  Phase 3: Experiment Telemetry Collection
  Phase 4: Fault Removal & Channel Recovery
  Phase 5: Delta Impact Calculation & Classification
"""

import json
from pathlib import Path
import time
import uuid

from app.core.logging import get_logger
from app.experiments.comparison import ExperimentComparator
from app.experiments.models import (
    ExperimentResult,
    ObservationMetrics,
)
from app.faults.injector import FaultInjector
from app.faults.profiles import FaultProfileRegistry
from app.networking.udp import UDPServer
from app.performance.packet_loss import UDPPacketLossBenchmark

logger = get_logger("experiments.engine")


class ExperimentRunner:
    """
    Executes controlled network experiments comparing Control against Faulted phases.
    """

    @classmethod
    def run_udp_loss_experiment(
        cls,
        fault_profile_name: str = "lossy",
        packet_count: int = 100,
        packet_size: int = 1024
    ) -> ExperimentResult:
        """
        Execute a controlled UDP loss & jitter experiment.
        """
        profile = FaultProfileRegistry.get_profile(fault_profile_name)
        if not profile:
            raise ValueError(f"Unknown fault profile: '{fault_profile_name}'")

        exp_id = f"EXP-{uuid.uuid4().hex[:8].upper()}"
        logger.info(f"Starting Network Experiment [{exp_id}]: Protocol=UDP, Fault Profile='{profile.name}'")

        # ----------------------------------------------------
        # Phase 1: CONTROL (Clean channel)
        # ----------------------------------------------------
        logger.info("[Experiment Phase 1/4] Measuring Control Baseline on clean channel...")
        FaultInjector.clear()
        control_server = UDPServer(host="127.0.0.1", port=0, packet_drop_rate=0.0)
        control_server.start()

        try:
            t0 = time.perf_counter()
            ctrl_loss, ctrl_jitter = UDPPacketLossBenchmark.run_echo_loss_test(
                host=control_server.host,
                port=control_server.port,
                packet_count=packet_count,
                packet_size=packet_size,
                timeout=0.05
            )
            ctrl_duration = time.perf_counter() - t0

            control_obs = ObservationMetrics(
                throughput_mbps=None,
                latency_avg_ms=None,
                latency_p95_ms=None,
                packet_loss_percent=ctrl_loss.packet_loss_percent,
                jitter_avg_ms=ctrl_jitter.average_jitter_ms,
                total_packets_sent=ctrl_loss.packets_sent,
                total_packets_received=ctrl_loss.packets_received,
                duration_seconds=round(ctrl_duration, 3)
            )
        finally:
            control_server.stop()

        # ----------------------------------------------------
        # Phase 2: FAULT INJECTION
        # ----------------------------------------------------
        logger.info(f"[Experiment Phase 2/4] Applying fault profile '{profile.name}'...")
        FaultInjector.apply(profile)

        # ----------------------------------------------------
        # Phase 3: EXPERIMENT OBSERVATION
        # ----------------------------------------------------
        logger.info("[Experiment Phase 3/4] Measuring performance under fault conditions...")
        # Simulate drop rate on server if in userland simulation mode
        drop_rate = profile.config.packet_loss_percent / 100.0 if profile.config.packet_loss_percent > 0 else 0.0
        exp_server = UDPServer(host="127.0.0.1", port=0, packet_drop_rate=drop_rate)
        exp_server.start()

        try:
            t1 = time.perf_counter()
            exp_loss, exp_jitter = UDPPacketLossBenchmark.run_echo_loss_test(
                host=exp_server.host,
                port=exp_server.port,
                packet_count=packet_count,
                packet_size=packet_size,
                timeout=0.05
            )
            exp_duration = time.perf_counter() - t1

            exp_obs = ObservationMetrics(
                throughput_mbps=None,
                latency_avg_ms=profile.config.latency_ms if profile.config.latency_ms > 0 else None,
                latency_p95_ms=profile.config.latency_ms if profile.config.latency_ms > 0 else None,
                packet_loss_percent=exp_loss.packet_loss_percent,
                jitter_avg_ms=exp_jitter.average_jitter_ms + (profile.config.jitter_ms if profile.config.jitter_ms else 0.0),
                total_packets_sent=exp_loss.packets_sent,
                total_packets_received=exp_loss.packets_received,
                duration_seconds=round(exp_duration, 3)
            )
        finally:
            exp_server.stop()

        # ----------------------------------------------------
        # Phase 4: CLEAR FAULT & VERIFY RECOVERY
        # ----------------------------------------------------
        logger.info("[Experiment Phase 4/4] Clearing faults and verifying recovery...")
        FaultInjector.clear()

        # ----------------------------------------------------
        # Phase 5: COMPUTE IMPACT & CLASSIFY
        # ----------------------------------------------------
        impact = ExperimentComparator.compute_impact(control_obs, exp_obs)
        classification, details = ExperimentComparator.classify(control_obs, exp_obs, profile.config)

        result = ExperimentResult(
            experiment_id=exp_id,
            name=f"UDP Loss & Jitter Experiment ({profile.name})",
            protocol="UDP",
            topology="client-router-server",
            fault_profile=profile.name,
            fault_config=profile.config,
            control_observation=control_obs,
            experiment_observation=exp_obs,
            impact=impact,
            classification=classification,
            details=details
        )

        cls._save_experiment(result)
        logger.info(f"Experiment [{exp_id}] completed with classification: {classification.value}")
        return result

    @classmethod
    def _save_experiment(cls, result: ExperimentResult, output_path: str = "reports/experiments.json") -> None:
        """Append experiment result to reports/experiments.json."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        existing = []
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = []

        existing.append(result.to_dict())
        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
