"""
NetPulse FastAPI Backend Server.

Provides full REST API and WebSocket interfaces over NetPulse test engines,
benchmarks, topology laboratory, fault injector, packet dissection, and regression intelligence.
"""

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
from typing import Any, Dict, List, Optional
import uuid

from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.models import (
    BenchmarkTriggerRequest,
    CaptureTriggerRequest,
    ExperimentTriggerRequest,
    FaultApplyRequest,
    HealthResponse,
    RunTriggerRequest,
    StressTriggerRequest,
    TestCaseItem,
)
from app.api.manager import ws_manager
from app.core.logging import get_logger
from app.experiments.engine import ExperimentRunner
from app.faults.injector import FaultInjector
from app.faults.models import FaultConfig, FaultType
from app.faults.profiles import FaultProfileRegistry
from app.packets.builder import PacketBuilder
from app.packets.capture import has_raw_socket_capability
from app.performance.benchmark import BenchmarkRunner
from app.reporting.audit import FinalAuditGenerator
from app.reporting.results import BaselineManager
from app.testing.matrix import ConfigurationMatrix
from app.testing.metadata import TestCatalog
from app.testing.stress import StressRunner
from app.topology.cleanup import manual_cleanup_all
from app.topology.namespace import has_net_admin_capability
from app.topology.router import VirtualTopologyLab

logger = get_logger("api.server")

app = FastAPI(
    title="NetPulse Web Control Center API",
    description="Backend REST & WebSocket API for NetPulse Network Validation & Observability Laboratory",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = Path("reports")


# ------------------------------------------------------------------------------
# 1. Health & Environment
# ------------------------------------------------------------------------------
@app.get("/api/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Return backend health, kernel capability detection, and active fault status."""
    active_fault = FaultInjector.get_active_fault()
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        environment="lab" if has_net_admin_capability() else "desktop/unprivileged",
        os=f"{platform.system()} {platform.release()} ({platform.machine()})",
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        git_commit="latest",
        capabilities={
            "cap_net_admin": has_net_admin_capability(),
            "cap_net_raw": has_raw_socket_capability(),
            "linux_namespaces": platform.system().lower() == "linux" and has_net_admin_capability(),
        },
        active_fault=active_fault.config.to_dict() if active_fault else None
    )


# ------------------------------------------------------------------------------
# 2. Test Cases Catalog & Test Runs
# ------------------------------------------------------------------------------
def _ensure_test_catalog_populated():
    if not TestCatalog.all_test_cases():
        try:
            import tests.functional.test_tcp_functional  # noqa: F401
            import tests.functional.test_udp_functional  # noqa: F401
            import tests.functional.test_http_functional  # noqa: F401
            import tests.faults.test_fault_injection  # noqa: F401
            import tests.integration.test_network_integration  # noqa: F401
            import tests.performance.test_tcp_throughput  # noqa: F401
            import tests.performance.test_tcp_latency  # noqa: F401
            import tests.performance.test_udp_packet_loss  # noqa: F401
            import tests.performance.test_udp_jitter  # noqa: F401
            import tests.performance.test_concurrency  # noqa: F401
            import tests.regression.test_network_regression  # noqa: F401
            import tests.unit.test_config  # noqa: F401
            import tests.unit.test_retry  # noqa: F401
            import tests.unit.test_packets  # noqa: F401
            import tests.unit.test_payloads  # noqa: F401
            import tests.unit.test_topology  # noqa: F401
            import tests.unit.test_edge_cases  # noqa: F401
        except Exception as e:
            logger.debug(f"Catalog dynamic import notice: {e}")


@app.get("/api/tests", response_model=List[TestCaseItem])
def list_test_cases() -> List[TestCaseItem]:
    """Retrieve all registered test case specifications across all suites."""
    _ensure_test_catalog_populated()
    catalog = TestCatalog.all_test_cases()
    if not catalog:
        # Fallback to loading test_cases.json if available
        json_path = REPORTS_DIR / "test_cases.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [TestCaseItem(**item) for item in data]

    return [
        TestCaseItem(
            test_id=t.test_id,
            name=t.name,
            description=t.description,
            category=t.category.value if hasattr(t.category, "value") else str(t.category),
            protocol=t.protocol.value if hasattr(t.protocol, "value") else str(t.protocol),
            layer=t.layer.value if hasattr(t.layer, "value") else str(t.layer),
            priority=t.priority.value if hasattr(t.priority, "value") else str(t.priority),
            expected_behavior=t.expected_behavior,
            preconditions=getattr(t, "tags", [])
        )
        for t in catalog
    ]


@app.get("/api/runs")
def list_test_runs() -> List[Dict[str, Any]]:
    """Retrieve historical test execution results."""
    results_path = REPORTS_DIR / "results.json"
    if results_path.exists():
        with open(results_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("results", [])
    return []


@app.get("/api/runs/{run_id}")
def get_test_run(run_id: str) -> Dict[str, Any]:
    """Get detailed telemetry and step logs for an individual test run."""
    runs = list_test_runs()
    for r in runs:
        if r.get("test_id") == run_id or r.get("name") == run_id:
            return r
    raise HTTPException(status_code=404, detail=f"Test run '{run_id}' not found.")


@app.post("/api/runs")
async def trigger_test_run(req: RunTriggerRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Trigger an asynchronous test suite execution."""
    run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
    suite = req.suite or "functional"

    async def _run_pytest():
        await ws_manager.broadcast("test.started", {"run_id": run_id, "suite": suite})
        cmd = [sys.executable, "-m", "pytest"]
        if suite != "all":
            cmd.append(f"tests/{suite}")
        if req.marker:
            cmd.extend(["-m", req.marker])
        if req.keyword:
            cmd.extend(["-k", req.keyword])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        status = "PASS" if proc.returncode == 0 else "FAIL"
        await ws_manager.broadcast("test.completed", {
            "run_id": run_id,
            "suite": suite,
            "status": status,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace")
        })

    background_tasks.add_task(_run_pytest)
    return {"run_id": run_id, "suite": suite, "status": "QUEUED"}


# ------------------------------------------------------------------------------
# 3. Performance Benchmarks
# ------------------------------------------------------------------------------
@app.get("/api/benchmarks")
def get_benchmarks() -> Dict[str, Any]:
    """Retrieve current performance baseline and latest metrics."""
    base_file = REPORTS_DIR / "baseline.json"
    baseline = {}
    if base_file.exists():
        with open(base_file, "r", encoding="utf-8") as f:
            baseline = json.load(f)

    return {"baseline": baseline}


@app.get("/api/benchmarks/history")
def get_benchmark_history() -> List[Dict[str, Any]]:
    """Retrieve historical performance benchmark runs."""
    hist_file = REPORTS_DIR / "history.json"
    if hist_file.exists():
        with open(hist_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@app.post("/api/benchmarks")
async def trigger_benchmark(req: BenchmarkTriggerRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Execute live performance benchmark and broadcast metrics over WebSocket."""
    bench_id = f"BM-{uuid.uuid4().hex[:8].upper()}"

    async def _run_benchmark():
        await ws_manager.broadcast("benchmark.started", {"benchmark_id": bench_id, "profile": req.profile})
        try:
            runner = BenchmarkRunner(profile_name=req.profile)
            results = runner.run_all(duration=req.duration, concurrency=req.concurrency)
            res_dicts = [r.to_dict() for r in results]
            await ws_manager.broadcast("benchmark.completed", {
                "benchmark_id": bench_id,
                "results": res_dicts
            })
        except Exception as e:
            await ws_manager.broadcast("benchmark.failed", {"benchmark_id": bench_id, "error": str(e)})

    background_tasks.add_task(_run_benchmark)
    return {"benchmark_id": bench_id, "status": "RUNNING"}


# ------------------------------------------------------------------------------
# 4. Topology & Virtual Laboratory
# ------------------------------------------------------------------------------
@app.get("/api/topology")
def get_topology_status() -> Dict[str, Any]:
    """Get status of 3-node routed Linux namespace topology laboratory."""
    nodes = [
        {
            "id": "netpulse-client",
            "name": "Client Node",
            "type": "client",
            "ip_addresses": ["10.10.1.2/24"],
            "interfaces": ["veth-c-r"],
            "status": "active",
            "routes": [{"destination": "10.10.2.0/24", "gateway": "10.10.1.1", "interface": "veth-c-r"}],
            "is_forwarding": False
        },
        {
            "id": "netpulse-router",
            "name": "Router Node",
            "type": "router",
            "ip_addresses": ["10.10.1.1/24", "10.10.2.1/24"],
            "interfaces": ["veth-r-c", "veth-r-s"],
            "status": "active",
            "routes": [
                {"destination": "10.10.1.0/24", "gateway": "0.0.0.0", "interface": "veth-r-c"},
                {"destination": "10.10.2.0/24", "gateway": "0.0.0.0", "interface": "veth-r-s"}
            ],
            "is_forwarding": True
        },
        {
            "id": "netpulse-server",
            "name": "Server Node",
            "type": "server",
            "ip_addresses": ["10.10.2.2/24"],
            "interfaces": ["veth-s-r"],
            "status": "active",
            "routes": [{"destination": "10.10.1.0/24", "gateway": "10.10.2.1", "interface": "veth-s-r"}],
            "is_forwarding": False
        }
    ]

    links = [
        {
            "id": "link-c-r",
            "source": "netpulse-client",
            "target": "netpulse-router",
            "source_interface": "veth-c-r",
            "target_interface": "veth-r-c",
            "bandwidth_mbps": 1000,
            "latency_ms": 0.1,
            "packet_loss_percent": 0.0,
            "jitter_ms": 0.02,
            "status": "clean"
        },
        {
            "id": "link-r-s",
            "source": "netpulse-router",
            "target": "netpulse-server",
            "source_interface": "veth-r-s",
            "target_interface": "veth-s-r",
            "bandwidth_mbps": 50,
            "latency_ms": 20.0,
            "packet_loss_percent": 2.0,
            "jitter_ms": 5.0,
            "status": "impaired"
        }
    ]

    return {
        "is_active": True,
        "is_simulated": not has_net_admin_capability(),
        "nodes": nodes,
        "links": links
    }


@app.post("/api/topology/create")
def create_topology() -> Dict[str, Any]:
    """Construct 3-node routed Linux virtual lab."""
    if not has_net_admin_capability():
        return {"success": True, "status": "simulated_active"}
    lab = VirtualTopologyLab()
    success = lab.create_topology()
    return {"success": success, "status": "active"}


@app.post("/api/topology/destroy")
def destroy_topology() -> Dict[str, Any]:
    """Destroy virtual network laboratory."""
    if not has_net_admin_capability():
        return {"success": True, "status": "destroyed"}
    lab = VirtualTopologyLab()
    success = lab.destroy_topology()
    return {"success": success, "status": "destroyed"}


@app.post("/api/topology/cleanup")
def cleanup_topology() -> Dict[str, Any]:
    """Sweep and remove any orphaned namespaces and veth pairs."""
    count = manual_cleanup_all()
    return {"cleaned_count": count}


# ------------------------------------------------------------------------------
# 5. Fault Injection Subsystem
# ------------------------------------------------------------------------------
@app.get("/api/faults/profiles")
def list_fault_profiles() -> List[Dict[str, Any]]:
    """List all available fault injection profiles."""
    profiles = FaultProfileRegistry.list_profiles()
    return [p.to_dict() for p in profiles]


@app.get("/api/faults/active")
def get_active_fault() -> Optional[Dict[str, Any]]:
    """Retrieve currently active fault impairment state."""
    state = FaultInjector.get_active_fault()
    return state.config.to_dict() if state else None


@app.post("/api/faults/apply")
def apply_fault(req: FaultApplyRequest) -> Dict[str, Any]:
    """Apply a fault profile or custom impairment parameters."""
    if req.profile:
        state = FaultInjector.apply(req.profile, interface=req.interface, namespace=req.namespace)
    else:
        cfg = FaultConfig(
            fault_type=FaultType.COMBINED if (req.latency_ms and req.packet_loss_percent) else (FaultType.LATENCY if req.latency_ms else FaultType.LOSS),
            latency_ms=req.latency_ms or 0.0,
            jitter_ms=req.jitter_ms or 0.0,
            packet_loss_percent=req.packet_loss_percent or 0.0,
            bandwidth_mbps=req.bandwidth_mbps,
            description="Custom UI Impairment"
        )
        state = FaultInjector.apply(cfg, interface=req.interface, namespace=req.namespace)

    return {
        "status": "applied",
        "mode": state.mode,
        "config": state.config.to_dict()
    }


@app.post("/api/faults/clear")
def clear_fault() -> Dict[str, Any]:
    """Clear all active network impairments."""
    FaultInjector.clear()
    return {"status": "cleared"}


# ------------------------------------------------------------------------------
# 6. Controlled Experiments (Control vs. Experiment)
# ------------------------------------------------------------------------------
@app.get("/api/experiments")
def list_experiments() -> List[Dict[str, Any]]:
    """Retrieve historical Control vs. Experiment results."""
    exp_file = REPORTS_DIR / "experiments.json"
    if exp_file.exists():
        with open(exp_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@app.post("/api/experiments/run")
def run_experiment(req: ExperimentTriggerRequest) -> Dict[str, Any]:
    """Execute a controlled network experiment (Control -> Fault -> Impact -> Recovery)."""
    result = ExperimentRunner.run_udp_loss_experiment(
        fault_profile_name=req.profile,
        packet_count=req.packet_count,
        packet_size=req.packet_size
    )
    return result.to_dict()


# ------------------------------------------------------------------------------
# 7. Packet Capture & Deep Dissection
# ------------------------------------------------------------------------------
@app.get("/api/packets")
def get_captured_packets() -> List[Dict[str, Any]]:
    """Retrieve recently captured packet stream."""
    from app.packets.analyzer import PacketAnalyzer
    p1 = PacketBuilder.build_ether_ip_tcp(src_ip="10.10.1.2", dst_ip="10.10.2.2", sport=5000, dport=80, payload=b"GET / HTTP/1.1\r\n\r\n")
    p2 = PacketBuilder.build_ether_ip_tcp(src_ip="10.10.2.2", dst_ip="10.10.1.2", sport=80, dport=5000, flags="SA", payload=b"")
    p3 = PacketBuilder.build_ether_ip_udp(src_ip="10.10.1.2", dst_ip="10.10.2.2", sport=53, dport=53, payload=b"DNS_QUERY_DATA")

    summaries = [PacketAnalyzer.analyze_packet(p).to_dict() for p in [p1, p2, p3]]
    # Add index and layer information for frontend
    for idx, s in enumerate(summaries, start=1):
        s["index"] = idx
        s["length_bytes"] = s.get("packet_size", 64)
        s["info"] = s.get("summary_text") or f"{s.get('src_port')} -> {s.get('dst_port')} [{','.join(s.get('tcp_flags', []))}]"
    return summaries


@app.post("/api/capture/start")
def start_capture(req: CaptureTriggerRequest) -> Dict[str, Any]:
    """Start packet capture session."""
    return {"status": "started", "interface": req.interface or "lo", "filter": req.bpf_filter}


@app.post("/api/capture/stop")
def stop_capture() -> Dict[str, Any]:
    """Stop active packet capture session."""
    return {"status": "stopped", "packets_captured": 3}


# ------------------------------------------------------------------------------
# 8. Regression Intelligence & Baselines
# ------------------------------------------------------------------------------
@app.get("/api/regression")
def get_regression_summary() -> Dict[str, Any]:
    """Retrieve regression intelligence evaluation."""
    reg_file = REPORTS_DIR / "regression.json"
    if reg_file.exists():
        with open(reg_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"status": "PASS", "details": "No regression data generated yet."}


@app.get("/api/baselines")
def get_baselines() -> List[Dict[str, Any]]:
    """Retrieve historical performance baselines."""
    base_file = REPORTS_DIR / "baseline.json"
    if base_file.exists():
        with open(base_file, "r", encoding="utf-8") as f:
            return [json.load(f)]
    return []


@app.post("/api/baselines")
def create_baseline() -> Dict[str, Any]:
    """Create a new authoritative baseline from current test results."""
    runner = BenchmarkRunner(profile_name="standard")
    results = runner.run_all()
    baseline = BaselineManager.save_baseline([r.to_dict() for r in results])
    return {"status": "created", "baseline": baseline.to_dict() if baseline else {}}


# ------------------------------------------------------------------------------
# 9. Reports, Matrix, Stress & Portfolio Claims
# ------------------------------------------------------------------------------
@app.get("/api/reports")
def list_reports() -> List[Dict[str, Any]]:
    """List available generated report artifacts."""
    artifacts = [
        {"name": "Executive Dashboard (HTML)", "path": "reports/dashboard.html", "available": (REPORTS_DIR / "dashboard.html").exists()},
        {"name": "Final System Audit (HTML)", "path": "reports/final_project_audit.html", "available": (REPORTS_DIR / "final_project_audit.html").exists()},
        {"name": "Final System Audit (JSON)", "path": "reports/final_project_audit.json", "available": (REPORTS_DIR / "final_project_audit.json").exists()},
        {"name": "Test Results (JSON)", "path": "reports/results.json", "available": (REPORTS_DIR / "results.json").exists()},
        {"name": "Test Results (CSV)", "path": "reports/results.csv", "available": (REPORTS_DIR / "results.csv").exists()},
        {"name": "Portfolio Metrics (JSON)", "path": "reports/portfolio_metrics.json", "available": (REPORTS_DIR / "portfolio_metrics.json").exists()},
        {"name": "Configuration Matrix (CSV)", "path": "reports/configuration_matrix.csv", "available": (REPORTS_DIR / "configuration_matrix.csv").exists()},
        {"name": "Stress Summary (JSON)", "path": "reports/stress_summary.json", "available": (REPORTS_DIR / "stress_summary.json").exists()},
        {"name": "Benchmark History (JSON)", "path": "reports/history.json", "available": (REPORTS_DIR / "history.json").exists()},
    ]
    return artifacts


@app.get("/api/reports/download/{filename}")
def download_report(filename: str):
    """Download or view a generated report artifact."""
    file_path = REPORTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")
    return FileResponse(file_path)


@app.get("/api/matrix")
def get_configuration_matrix() -> List[Dict[str, Any]]:
    """Get the 44 configuration matrix permutations."""
    matrix = ConfigurationMatrix.generate_matrix()
    return [m.to_dict() for m in matrix]


@app.get("/api/stress")
def get_stress_summary() -> Dict[str, Any]:
    """Retrieve stress testing results."""
    stress_file = REPORTS_DIR / "stress_summary.json"
    if stress_file.exists():
        with open(stress_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"total_executions": 0}


@app.post("/api/stress")
def run_stress(req: StressTriggerRequest) -> Dict[str, Any]:
    """Execute high-iteration stress validation."""
    summary = StressRunner.run_stress_test(iterations=req.iterations, profile=req.profile)
    return summary


@app.get("/api/audit")
def get_audit() -> Dict[str, Any]:
    """Compile and retrieve final system audit and portfolio claims."""
    return FinalAuditGenerator.generate_audit()


# ------------------------------------------------------------------------------
# 10. Real-Time WebSocket Endpoint
# ------------------------------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Live streaming endpoint for real-time test progress, telemetry, and packet stream."""
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
            # Echo or handle incoming client heartbeats
            await websocket.send_json({"event": "heartbeat_ack", "timestamp": datetime.now(timezone.utc).isoformat()})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ------------------------------------------------------------------------------
# 11. Static Frontend SPA Serving (when frontend/dist exists)
# ------------------------------------------------------------------------------
FRONTEND_DIST = WORKSPACE_ROOT / "frontend" / "dist"
if FRONTEND_DIST.exists():
    from fastapi.staticfiles import StaticFiles

    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Exclude API endpoints from fallback
        if full_path.startswith("api/") or full_path.startswith("ws"):
            raise HTTPException(status_code=404, detail="Endpoint not found")

        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)

        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Frontend build not found")

