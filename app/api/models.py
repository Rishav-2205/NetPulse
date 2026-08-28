"""
NetPulse FastAPI Request & Response Data Models.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    environment: str = "production"
    os: str
    python_version: str
    git_commit: str = "unknown"
    capabilities: Dict[str, bool] = Field(default_factory=dict)
    active_fault: Optional[Dict[str, Any]] = None


class TestCaseItem(BaseModel):
    test_id: str
    name: str
    description: str
    category: str
    protocol: str
    layer: str
    priority: str
    expected_behavior: str
    preconditions: List[str] = Field(default_factory=list)


class RunTriggerRequest(BaseModel):
    suite: Optional[str] = "functional"  # "functional", "regression", "performance", "unit", "faults", "all"
    marker: Optional[str] = None
    keyword: Optional[str] = None


class RunStepModel(BaseModel):
    name: str
    status: str
    duration_ms: float
    timestamp: str
    error: Optional[str] = None


class TestRunDetail(BaseModel):
    run_id: str
    test_id: Optional[str] = None
    name: str
    protocol: str
    category: str
    status: str
    duration_ms: float
    started_at: str
    steps: List[RunStepModel] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    logs: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None


class BenchmarkTriggerRequest(BaseModel):
    profile: str = "standard"
    protocol: str = "ALL"  # "ALL", "TCP", "UDP"
    concurrency: int = 1
    packet_size: int = 1024
    duration: float = 2.0


class FaultApplyRequest(BaseModel):
    profile: Optional[str] = None
    latency_ms: Optional[float] = 0.0
    jitter_ms: Optional[float] = 0.0
    packet_loss_percent: Optional[float] = 0.0
    bandwidth_mbps: Optional[float] = None
    interface: str = "veth-r-s"
    namespace: Optional[str] = "netpulse-router"


class ExperimentTriggerRequest(BaseModel):
    profile: str = "lossy"
    packet_count: int = 50
    packet_size: int = 1024


class CaptureTriggerRequest(BaseModel):
    interface: Optional[str] = None
    bpf_filter: Optional[str] = None
    packet_limit: int = 20
    timeout: float = 2.0


class StressTriggerRequest(BaseModel):
    iterations: int = 50
    profile: str = "quick"
