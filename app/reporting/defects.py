"""
NetPulse Actionable Defect-Style Failure Reporting Engine.

Extracts structured diagnostic context when tests fail, preserving
test IDs, expected vs actual values, full tracebacks, and environmental state.
"""

import csv
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.performance.metrics import EnvironmentMetadata


@dataclass
class TestDefect:
    """
    Structured defect report capturing actionable context for a failed test.
    """
    defect_id: str
    test_id: str
    test_name: str
    category: str = "Functional"
    protocol: str = "TCP"
    layer: str = "Layer 4"
    severity: str = "High"
    expected: Optional[str] = None
    actual: Optional[str] = None
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    stack_trace: Optional[str] = None
    retries_attempted: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    environment: Dict[str, Any] = field(default_factory=lambda: EnvironmentMetadata.capture().to_dict())
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DefectManager:
    """
    Collects, manages, and serializes test execution defects.
    """
    _defects: List[TestDefect] = []

    @classmethod
    def record_defect(cls, defect: TestDefect) -> None:
        """Record a test defect."""
        cls._defects.append(defect)

    @classmethod
    def all_defects(cls) -> List[TestDefect]:
        return list(cls._defects)

    @classmethod
    def clear(cls) -> None:
        cls._defects.clear()

    @classmethod
    def export_json(cls, filepath: str = "reports/defects.json") -> Path:
        """Export all recorded defects to JSON."""
        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = [d.to_dict() for d in cls.all_defects()]
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return target

    @classmethod
    def export_csv(cls, filepath: str = "reports/defects.csv") -> Path:
        """Export all recorded defects to CSV."""
        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        defects = cls.all_defects()
        if not defects:
            with open(target, "w", newline="", encoding="utf-8") as f:
                f.write("defect_id,test_id,test_name,category,protocol,severity,exception_type,exception_message,timestamp\n")
            return target

        fieldnames = ["defect_id", "test_id", "test_name", "category", "protocol", "severity", "exception_type", "exception_message", "timestamp"]
        with open(target, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for d in defects:
                writer.writerow(d.to_dict())
        return target
