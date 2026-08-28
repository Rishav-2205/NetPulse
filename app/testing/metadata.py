"""
NetPulse Test Case Management, Metadata & Traceability Taxonomy.

Defines structured test case metadata models, taxonomy decorators (@test_case),
and test catalog aggregation for full traceability from test specification to execution report.
"""

import csv
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

F = TypeVar("F", bound=Callable[..., Any])


class TestCategory(str, Enum):
    """Broad category of the network test."""
    FUNCTIONAL = "Functional"
    PERFORMANCE = "Performance"
    REGRESSION = "Regression"
    INTEGRATION = "Integration"
    UNIT = "Unit"
    SECURITY = "Security"


class ProtocolType(str, Enum):
    """Network protocol under test."""
    TCP = "TCP"
    UDP = "UDP"
    HTTP = "HTTP"
    ICMP = "ICMP"
    ETHERNET = "Ethernet"
    TOPOLOGY = "Topology"
    FRAMEWORK = "Framework"


class OSI_Layer(str, Enum):
    """OSI model layer corresponding to the test scope."""
    LAYER_2 = "Layer 2 (Data Link)"
    LAYER_3 = "Layer 3 (Network)"
    LAYER_4 = "Layer 4 (Transport)"
    LAYER_7 = "Layer 7 (Application)"
    CROSS_LAYER = "Cross-Layer"


class TestPriority(str, Enum):
    """Execution priority and criticality."""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass
class TestCaseMetadata:
    """
    Standardized specification metadata for an automated test case.
    """
    __test__ = False
    test_id: str  # e.g., "NET-TCP-001"
    name: str
    category: str
    protocol: str
    layer: str
    priority: str = "High"
    description: str = ""
    expected_behavior: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TestCatalog:
    """
    Registry for discovered and decorated test cases.
    """
    _registry: Dict[str, TestCaseMetadata] = {}

    @classmethod
    def register(cls, metadata: TestCaseMetadata) -> None:
        """Register a test case in the catalog."""
        cls._registry[metadata.test_id] = metadata

    @classmethod
    def get(cls, test_id: str) -> Optional[TestCaseMetadata]:
        return cls._registry.get(test_id)

    @classmethod
    def all_test_cases(cls) -> List[TestCaseMetadata]:
        return list(cls._registry.values())

    @classmethod
    def export_json(cls, filepath: str = "reports/test_cases.json") -> Path:
        """Export the full test case catalog to JSON."""
        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = [tc.to_dict() for tc in cls.all_test_cases()]
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return target

    @classmethod
    def export_csv(cls, filepath: str = "reports/test_cases.csv") -> Path:
        """Export the full test case catalog to CSV."""
        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        cases = cls.all_test_cases()
        if not cases:
            with open(target, "w", newline="", encoding="utf-8") as f:
                f.write("test_id,name,category,protocol,layer,priority,description,expected_behavior\n")
            return target

        fieldnames = ["test_id", "name", "category", "protocol", "layer", "priority", "description", "expected_behavior"]
        with open(target, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for tc in cases:
                writer.writerow(tc.to_dict())
        return target


def test_case(
    test_id: str,
    name: str,
    category: Union[TestCategory, str],
    protocol: Union[ProtocolType, str],
    layer: Union[OSI_Layer, str],
    priority: Union[TestPriority, str] = TestPriority.HIGH,
    description: str = "",
    expected_behavior: str = "",
    tags: Optional[List[str]] = None
) -> Callable[[F], F]:
    """
    Decorator attaching enterprise test case metadata to a pytest test function or method.
    """
    meta = TestCaseMetadata(
        test_id=test_id,
        name=name,
        category=category.value if isinstance(category, TestCategory) else str(category),
        protocol=protocol.value if isinstance(protocol, ProtocolType) else str(protocol),
        layer=layer.value if isinstance(layer, OSI_Layer) else str(layer),
        priority=priority.value if isinstance(priority, TestPriority) else str(priority),
        description=description,
        expected_behavior=expected_behavior,
        tags=tags or []
    )
    TestCatalog.register(meta)

    def decorator(fn: F) -> F:
        setattr(fn, "__netpulse_test_case__", meta)
        return fn

    return decorator


test_case.__test__ = False
