"""
NetPulse Regression Baseline Model & Storage Engine.

Persists and loads authoritative test execution and benchmark baselines with environment metadata.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.logging import get_logger
from app.performance.metrics import EnvironmentMetadata

logger = get_logger("regression.baseline")


@dataclass
class RegressionBaseline:
    """
    Authoritative baseline representation containing test statuses, durations, and benchmark metrics.
    """
    version: str = "1.0.0"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    git_commit: str = "unknown"
    environment: Dict[str, Any] = field(default_factory=lambda: EnvironmentMetadata.capture().to_dict())
    tests: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    benchmarks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegressionBaseline":
        return cls(
            version=data.get("version", "1.0.0"),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            git_commit=data.get("git_commit", "unknown"),
            environment=data.get("environment", {}),
            tests=data.get("tests", {}),
            benchmarks=data.get("benchmarks", {}),
            summary=data.get("summary", {})
        )

    def save(self, filepath: str = "reports/baseline.json") -> Path:
        """Persist the baseline to JSON."""
        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Saved regression baseline ({len(self.tests)} tests, {len(self.benchmarks)} benchmarks) to {target}")
        return target

    @classmethod
    def load(cls, filepath: str = "reports/baseline.json") -> Optional["RegressionBaseline"]:
        """Load baseline from file."""
        target = Path(filepath)
        if not target.exists():
            return None
        try:
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
                return cls.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to read baseline file at {filepath}: {e}")
            return None
