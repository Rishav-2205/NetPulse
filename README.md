# NetPulse: Network Validation Laboratory & Performance Engineering Platform

[![CI & Test Matrix](https://github.com/Rishav-2205/NetPulse/actions/workflows/tests.yml/badge.svg)](https://github.com/Rishav-2205/NetPulse/actions/workflows/tests.yml)
[![Regression Pipeline](https://github.com/Rishav-2205/NetPulse/actions/workflows/regression.yml/badge.svg)](https://github.com/Rishav-2205/NetPulse/actions/workflows/regression.yml)
[![Deploy Web Control Center](https://github.com/Rishav-2205/NetPulse/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/Rishav-2205/NetPulse/actions/workflows/deploy-pages.yml)
[![Automated Tests](https://img.shields.io/badge/tests-115%20passed%20%7C%20100%25-brightgreen.svg)](https://github.com/Rishav-2205/NetPulse)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Frontend](https://img.shields.io/badge/Frontend-React%2018%20%2B%20TypeScript%20%2B%20Tailwind-61DAFB.svg)](https://github.com/Rishav-2205/NetPulse)
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%2B%20WebSockets-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**NetPulse** is a production-grade network validation laboratory, performance benchmarking engine, and regression intelligence platform built with Python low-level sockets, Linux kernel traffic control (`tc netem`), Scapy deep packet inspection, Pytest, FastAPI, and a modern React 18 Web Control Center.

It empowers network performance engineers, SREs, and DevOps architects to construct multi-node routed virtual topologies, inject controlled network impairments (latency, packet loss, jitter, bandwidth rate limiting), execute high-throughput multi-stream traffic generators, and evaluate Control vs. Experiment impact deltas against historical baselines in real-time.

---

## 1. System Architecture

```
                                 NETPULSE PLATFORM
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
 ┌──────────────┐                 ┌──────────────┐                 ┌──────────────┐
 │ WEB CONTROL  │                 │ REST & WS    │                 │ CLI RUNNER   │
 │ CENTER (SPA) │ ◄─────────────► │ API BACKEND  │ ◄─────────────► │ & TEST SUITE │
 │  (React 18)  │   WebSocket/    │  (FastAPI)   │     Pytest/     │  (Click/Rich)│
 └──────────────┘   REST JSON     └──────────────┘     Subprocess  └──────────────┘
                                         │
                         ┌───────────────┴───────────────┐
                         ▼                               ▼
                 TEST ORCHESTRATOR                 OBSERVABILITY
                         │                               │
                  Traffic Generator               Packet Capture
                         │                      Metrics Collector
                         ▼                               │
                ┌──────────────── NETWORK LAB ───────────┴───┐
                │                                            │
                │  Client Namespace (10.10.1.2/24)          │
                │       │                                    │
                │      veth-c-r (10.10.1.0/24)               │
                │       │                                    │
                │  Router Namespace (10.10.1.1 & 10.10.2.1)  │
                │       │ (ip_forward=1)                     │
                │      veth-r-s (10.10.2.0/24)               │
                │       │                                    │
                │  Server Namespace (10.10.2.2/24)          │
                │                                            │
                │       Fault Injection Layer (tc netem)     │
                │       ├── Latency (e.g. 50 ms)             │
                │       ├── Packet Loss (e.g. 2%)            │
                │       ├── RFC 3393 Jitter (e.g. ±5 ms)     │
                │       ├── Bandwidth Limit (e.g. 50 Mbps)   │
                │       └── Packet Corruption                │
                └────────────────────────────────────────────┘
                                         │
                                         ▼
                         Regression Diff & Baseline Manager
                                         │
                                         ▼
                  Executive HTML Dashboards, JSON & Audit Reports
```

---

## 2. Core Capabilities

### 2.1 Web Control Center (`frontend/`)
A responsive single-page application built with React 18, TypeScript, Tailwind CSS, TanStack Query, Recharts, and Zustand:
- **Executive Dashboard**: System telemetry KPIs, real-time activity stream, and health gauges.
- **Test Runs & Live Execution**: Live streaming of Pytest suites with ANSI console output over WebSockets.
- **Performance Benchmarks**: Interactive charts for Throughput (Mbps), RTT Latency distributions, RFC 3393 Jitter, and Packet Loss.
- **Topology Visualizer**: Visual Canvas diagram of network nodes and simulated hop-by-hop latency routing.
- **Live Packet Capture & Dissector**: Real-time packet capture stream with Layer 2/3/4 deep protocol dissection and hex dump inspector.
- **Test Case Catalog**: Interactive filtering across all 115 test cases categorized by OSI layer, protocol, and priority.
- **Regression Intelligence**: Historical baseline comparison with automated regression detection and tolerance threshold diffing.
- **Fault Injection Lab**: Live application of kernel `tc netem` impairment profiles (`lossy`, `jittery`, `high_latency`, `constrained`).
- **Reports & Claims Audit**: Download and preview executive dashboards, CSV matrix exports, and verified portfolio claims.
- **Global Command Palette (`Ctrl+K`)**: Quick navigation, instant test triggering, and system shortcuts.

### 2.2 Routed Linux Network Namespace Lab (`app/topology/`)
- **3-Node Topology**: Orchestrates isolated Linux network namespaces (`netpulse-client` $\leftrightarrow$ `netpulse-router` $\leftrightarrow$ `netpulse-server`) connected via virtual Ethernet (`veth`) pairs with IPv4 routing and packet forwarding (`sysctl net.ipv4.ip_forward=1`).
- **Signal-Safe Cleanup**: Automatic exit traps (`atexit`) and signal handlers (`SIGINT`, `SIGTERM`) guarantee no host namespace or virtual link pollution.
- **Unprivileged Graceful Degradation**: Detects whether `CAP_NET_ADMIN` / `root` is available, falling back to local loopback and userland simulation when running unprivileged.

### 2.3 Kernel-Level Fault Injection (`app/faults/`)
- **Linux Traffic Control (`tc netem`)**: Directly configures kernel queueing disciplines (`qdisc`) on virtual interfaces:
  - **Latency**: Precise one-way packet delays (5ms to 500ms).
  - **Jitter**: Delay variation modeling with normal distribution correlation.
  - **Packet Loss**: Deterministic or probabilistic datagram drops (0.1% to 100%).
  - **Rate Limiting**: Token Bucket Filter (`tbf`) bandwidth constraints (10 Mbps to 1 Gbps).
  - **Corruption**: Single-bit error injection into datagram payloads.

### 2.4 Controlled Experiment Engine (`app/experiments/`)
- **Control vs. Experiment Methodology**: Automatically runs a clean **Control Phase** followed by an impaired **Experiment Phase**, recording delta impact ($\Delta \text{throughput}$, $\Delta \text{latency}$, $\Delta \text{loss}$, $\Delta \text{jitter}$).
- **Degradation Classification**: Differentiates between `EXPECTED_DEGRADATION` (due to intentional fault injection) and `UNEXPECTED_REGRESSION`.

### 2.5 Multi-Protocol Networking & Deep Dissection
- **TCP Engine**: Byte stream framing, chunked buffer accumulation, half-close detection, and `TCP_NODELAY` tuning.
- **UDP Loss & Jitter Engine**: 16-byte binary sequence header (`!QQ`: uint64 sequence number + uint64 timestamp) computing packet loss and RFC 3393 Inter-Packet Delay Variation (IPDV).
- **HTTP/1.1 Engine**: Connection pooling and embedded test server.
- **Scapy Packet Dissection**: Decodes L2 MACs, L3 IP headers, and L4 TCP control flags (`SYN`, `ACK`, `FIN`, `RST`, `PSH`, `URG`).

---

## 3. Evidence-Based Portfolio Metrics Audit Table

All metrics below are verified against raw generated test and telemetry files in [`reports/`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/reports).

| Engineering Metric | Measured Value | Verification Methodology | Sample Size | Raw Evidence File | Resume Safe |
| :--- | :---: | :--- | :---: | :---: | :---: |
| **Automated Test Suite** | **115 tests** | Pytest discovery across 7 test suites | 115 tests | [`reports/results.json`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/reports/results.json) | **YES** |
| **Network Configurations** | **44 permutations** | Combinatorial L4-L7 parameter generator | 44 configs | [`reports/configuration_matrix.csv`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/reports/configuration_matrix.csv) | **YES** |
| **Validated Executions** | **5,000+** | High-iteration stress runner | 5,000+ runs | [`reports/stress_summary.json`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/reports/stress_summary.json) | **YES** |
| **Average Socket Latency** | **0.087 ms** | Monotonic high-resolution timer (`perf_counter_ns`) | 50 RTT probes | [`reports/history.json`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/reports/history.json) | **YES** |
| **P95 Socket Latency** | **0.150 ms** | Statistical percentile interpolation | 50 RTT probes | [`reports/history.json`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/reports/history.json) | **YES** |
| **UDP Throughput** | **600.4 Mbps** | Sustained datagram stream over 1024B buffers | 3.0s duration | [`reports/history.json`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/reports/history.json) | **YES** |
| **Packet Loss Measurement**| **0.00% / 2.00%** | 16-byte `!QQ` binary sequence header validation | 200 packets | [`reports/experiments.json`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/reports/experiments.json) | **YES** |
| **Regression Intelligence**| **100% detection**| Baseline threshold diffing comparator | 4 suites | [`reports/regression.json`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/reports/regression.json) | **YES** |
| **CI/CD Environments** | **4 matrix jobs** | GitHub Actions matrix (Ubuntu/Windows x Py3.11/Py3.12)| 2 OS x 2 Py | [`.github/workflows/tests.yml`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/.github/workflows/tests.yml) | **YES** |

---

## 4. Quickstart Guide

### 4.1 Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/Rishav-2205/NetPulse.git
cd NetPulse

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies and package
pip install -r requirements.txt
pip install -e .
```

### 4.2 Launching the Web Control Center

```bash
# Start the unified backend server & built Web UI (Single-port host):
netpulse serve --host 127.0.0.1 --port 8000
```
Open **`http://127.0.0.1:8000`** in your browser to access the full NetPulse Web Control Center!

For frontend development with hot-reloading:
```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173 with API proxying to :8000
```

### 4.3 Running the Automated Test Suite & Benchmarks

```bash
# Run all 115 automated test cases
pytest -v

# Run performance benchmarks with baseline comparison
python -m netpulse benchmark --profile standard --compare-baseline --html

# Run controlled fault-injection experiment
python -m netpulse experiment --profile lossy

# Execute high-iteration stress validation
python -m netpulse stress --iterations 50 --profile quick

# Run complete clean-room demonstration workflow
python scripts/demo.py
```

### 4.4 Docker Container Execution

```bash
# Build the Docker image
docker build -t netpulse:latest .

# Run automated tests inside the container
docker run --rm netpulse:latest

# Or launch the containerized Web Control Center
docker compose -f docker/docker-compose.yml up netpulse-web
```

---

## 5. Project Directory Structure

```
NetPulse/
├── .github/
│   └── workflows/
│       ├── tests.yml                  # PR workflow: Ruff lint + Python 3.11/3.12 on Ubuntu/Windows
│       ├── regression.yml             # Main branch: Full regression & performance verification
│       └── deploy-pages.yml           # Continuous deployment of Web UI to GitHub Pages
├── app/
│   ├── api/                           # FastAPI REST & WebSocket streaming server
│   ├── core/                          # Config, Logging, Exceptions, Retry Engine
│   ├── experiments/                   # ExperimentRunner, Control vs. Experiment Comparator
│   ├── faults/                        # FaultInjector, Linux tc netem, Impairment Profiles
│   ├── networking/                    # TCPClient/Server, UDPClient/Server, HTTPClient/Server
│   ├── packets/                       # Scapy PacketBuilder, PacketParser, FlowSummary, Capture
│   ├── performance/                   # Latency, Throughput, Loss, Jitter, StatisticalSeries
│   ├── regression/                    # RegressionComparator, BaselineManager, Thresholds
│   ├── reporting/                     # Executive Dashboard, Final Audit, DefectManager, FlakyTracker
│   ├── testing/                       # TestCaseMetadata (@test_case), Matrix, StressRunner
│   ├── topology/                      # NetworkNamespaceManager, VethPair, VirtualTopologyLab
│   └── cli.py                         # Unified NetPulse CLI (`netpulse serve`, `netpulse benchmark`)
├── frontend/                          # React 18 + TypeScript + Vite + Tailwind CSS Web Control Center
│   ├── src/
│   │   ├── components/                # Layout, Sidebar, Topbar, CommandPalette, StatCard, ChartCard
│   │   ├── features/                  # 10 Dashboard views (Dashboard, TestRuns, Performance, Topology, etc.)
│   │   ├── services/                  # REST API Client & WebSocket streaming manager
│   │   └── types/                     # TypeScript data models and API schemas
│   └── dist/                          # Production compiled SPA bundle
├── docs/                              # Technical documentation & architecture deep dives
├── docker/                            # Dockerfile and multi-service docker-compose.yml
├── reports/                           # Output artifacts (HTML dashboards, CSV matrices, JSON telemetry)
├── scripts/                           # End-to-end demo and validation scripts
└── tests/                             # 115 Pytest test cases across 7 test suites
```

---

## 6. License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
