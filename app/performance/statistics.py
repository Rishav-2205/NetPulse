"""
NetPulse Statistical Validation & Baseline Stability Engine.

Computes statistical distribution metrics across multi-iteration benchmark runs:
mean, median, min, max, variance, sample standard deviation, percentiles (P50, P90, P95, P99),
and coefficient of variation (CV) for environment stability assessment.
"""

from dataclasses import dataclass, asdict
import math
from typing import Any, Dict, List, Optional


@dataclass
class StatisticalSummary:
    """Statistical summary across a series of numerical sample measurements."""
    count: int
    mean: float
    median: float
    min: float
    max: float
    variance: float
    std_dev: float
    p50: float
    p90: float
    p95: float
    p99: float
    coefficient_of_variation: float
    is_stable: bool
    stability_grade: str  # "STABLE" (CV < 5%), "MODERATE" (5-15%), "VOLATILE" (>15%)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StatisticalSeries:
    """
    Analyzes sample series to validate measurement stability and variance.
    """

    @classmethod
    def calculate(cls, samples: List[float], stability_threshold_cv: float = 0.10) -> Optional[StatisticalSummary]:
        """
        Calculate statistical properties of the sample series.
        """
        if not samples:
            return None

        n = len(samples)
        sorted_samples = sorted(samples)

        mean_val = sum(samples) / n
        median_val = cls._percentile(sorted_samples, 50.0)
        min_val = sorted_samples[0]
        max_val = sorted_samples[-1]

        if n > 1:
            variance_val = sum((x - mean_val) ** 2 for x in samples) / (n - 1)
            std_dev_val = math.sqrt(variance_val)
        else:
            variance_val = 0.0
            std_dev_val = 0.0

        p50 = median_val
        p90 = cls._percentile(sorted_samples, 90.0)
        p95 = cls._percentile(sorted_samples, 95.0)
        p99 = cls._percentile(sorted_samples, 99.0)

        cv = (std_dev_val / mean_val) if mean_val > 0 else 0.0

        if cv < 0.05:
            grade = "STABLE"
        elif cv <= 0.15:
            grade = "MODERATE"
        else:
            grade = "VOLATILE"

        is_stable = cv <= stability_threshold_cv

        return StatisticalSummary(
            count=n,
            mean=round(mean_val, 4),
            median=round(median_val, 4),
            min=round(min_val, 4),
            max=round(max_val, 4),
            variance=round(variance_val, 6),
            std_dev=round(std_dev_val, 4),
            p50=round(p50, 4),
            p90=round(p90, 4),
            p95=round(p95, 4),
            p99=round(p99, 4),
            coefficient_of_variation=round(cv, 4),
            is_stable=is_stable,
            stability_grade=grade
        )

    @staticmethod
    def _percentile(sorted_data: List[float], p: float) -> float:
        """Compute p-th percentile from pre-sorted data using linear interpolation."""
        if not sorted_data:
            return 0.0
        n = len(sorted_data)
        if n == 1:
            return sorted_data[0]
        rank = (p / 100.0) * (n - 1)
        lower_idx = int(math.floor(rank))
        upper_idx = int(math.ceil(rank))
        weight = rank - lower_idx
        return sorted_data[lower_idx] * (1.0 - weight) + sorted_data[upper_idx] * weight
