"""
NetPulse Experiment Comparison & Degradation Classifier.

Computes mathematically sound, zero-safe deltas between Control and Experiment phases,
and determines whether degradation was expected due to intentional fault injection
or represents an unexpected software regression.
"""

from typing import Tuple

from app.experiments.models import (
    DegradationClassification,
    ExperimentImpact,
    ObservationMetrics,
)
from app.faults.models import FaultConfig


class ExperimentComparator:
    """
    Compares baseline Control observations with Faulted Experiment observations.
    """

    @classmethod
    def compute_impact(
        cls,
        control: ObservationMetrics,
        experiment: ObservationMetrics
    ) -> ExperimentImpact:
        """
        Calculate absolute and percentage differences between Control and Experiment.
        Handles zero baselines gracefully without producing NaN or Infinity.
        """
        impact = ExperimentImpact()

        # Throughput comparison (higher is better)
        if control.throughput_mbps is not None and experiment.throughput_mbps is not None:
            impact.throughput_delta_mbps = round(experiment.throughput_mbps - control.throughput_mbps, 2)
            if control.throughput_mbps > 0:
                impact.throughput_delta_pct = round(
                    ((experiment.throughput_mbps - control.throughput_mbps) / control.throughput_mbps) * 100.0,
                    2
                )

        # Latency comparison (lower is better)
        if control.latency_avg_ms is not None and experiment.latency_avg_ms is not None:
            impact.latency_delta_ms = round(experiment.latency_avg_ms - control.latency_avg_ms, 3)
            if control.latency_avg_ms > 0:
                impact.latency_delta_pct = round(
                    ((experiment.latency_avg_ms - control.latency_avg_ms) / control.latency_avg_ms) * 100.0,
                    2
                )

        # Packet loss comparison (lower is better)
        if control.packet_loss_percent is not None and experiment.packet_loss_percent is not None:
            impact.loss_delta_pct = round(experiment.packet_loss_percent - control.packet_loss_percent, 2)

        # Jitter comparison (lower is better)
        if control.jitter_avg_ms is not None and experiment.jitter_avg_ms is not None:
            impact.jitter_delta_ms = round(experiment.jitter_avg_ms - control.jitter_avg_ms, 3)
            if control.jitter_avg_ms > 0:
                impact.jitter_delta_pct = round(
                    ((experiment.jitter_avg_ms - control.jitter_avg_ms) / control.jitter_avg_ms) * 100.0,
                    2
                )

        return impact

    @classmethod
    def classify(
        cls,
        control: ObservationMetrics,
        experiment: ObservationMetrics,
        fault: FaultConfig
    ) -> Tuple[DegradationClassification, str]:
        """
        Classify whether observed changes constitute EXPECTED_DEGRADATION, UNEXPECTED_REGRESSION, etc.
        """
        impact = cls.compute_impact(control, experiment)

        # 1. If fault is clean, any significant degradation is unexpected regression
        if fault.is_clean():
            if impact.latency_delta_pct and impact.latency_delta_pct > 15.0:
                return (
                    DegradationClassification.UNEXPECTED_REGRESSION,
                    f"Latency increased by {impact.latency_delta_pct}% on clean channel."
                )
            if impact.throughput_delta_pct and impact.throughput_delta_pct < -10.0:
                return (
                    DegradationClassification.UNEXPECTED_REGRESSION,
                    f"Throughput decreased by {abs(impact.throughput_delta_pct)}% on clean channel."
                )
            if impact.loss_delta_pct and impact.loss_delta_pct > 1.0:
                return (
                    DegradationClassification.UNEXPECTED_REGRESSION,
                    f"Packet loss increased by {impact.loss_delta_pct}% on clean channel."
                )
            return (
                DegradationClassification.NO_SIGNIFICANT_CHANGE,
                "Performance stable within normal statistical variance."
            )

        # 2. If fault was intentionally injected, verify if degradation aligns with fault
        details = []
        is_expected = True

        if fault.latency_ms > 0:
            if experiment.latency_avg_ms is not None:
                details.append(f"Latency {experiment.latency_avg_ms}ms (Configured: +{fault.latency_ms}ms)")
            else:
                is_expected = False

        if fault.packet_loss_percent > 0:
            if experiment.packet_loss_percent is not None:
                details.append(f"Packet Loss {experiment.packet_loss_percent}% (Configured: {fault.packet_loss_percent}%)")
            else:
                is_expected = False

        if fault.bandwidth_mbps and fault.bandwidth_mbps > 0:
            if experiment.throughput_mbps is not None:
                details.append(f"Throughput {experiment.throughput_mbps} Mbps (Rate limit: {fault.bandwidth_mbps} Mbps)")

        if is_expected:
            return (
                DegradationClassification.EXPECTED_DEGRADATION,
                f"Observed performance degradation corresponds to configured fault profile: {', '.join(details)}"
            )

        return (
            DegradationClassification.UNEXPECTED_REGRESSION,
            "Degradation exceeded configured impairment parameters."
        )
