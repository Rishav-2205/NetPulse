# NetPulse: Network Validation Laboratory & Fault-Injection Engine

[![CI Test Matrix](https://github.com/your-org/netpulse/actions/workflows/tests.yml/badge.svg)](https://github.com/your-org/netpulse/actions/workflows/tests.yml)
[![Regression Pipeline](https://github.com/your-org/netpulse/actions/workflows/regression.yml/badge.svg)](https://github.com/your-org/netpulse/actions/workflows/regression.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**NetPulse** is an advanced network validation laboratory, performance benchmarking engine, and regression intelligence framework built in Python using low-level sockets, Linux kernel traffic control (`tc netem`), Scapy deep packet inspection, and Pytest.

It empowers network engineers, DevOps architects, and QA engineers to construct multi-node routed virtual topologies, inject controlled network faults (latency, packet loss, jitter, bandwidth rate limiting), execute high-throughput traffic generators, and evaluate Control vs. Experiment impact deltas against historical baselines.

---

## 1. System Architecture

```
                         NETPULSE
                            │
              ┌─────────────┴─────────────┐
              │                           │
        TEST ORCHESTRATOR            OBSERVABILITY
              │                           │
              ▼                           ▼
       Traffic Generator            Packet Capture
              │                    Metrics Collector
              │                           │
              ▼                           │
     ┌─────────────────── NETWORK LAB ───────────────────┐
     │                                                     │
     │  Client Namespace (10.10.1.2/24)                   │
     │       │                                             │
     │      veth-c-r (10.10.1.0/24)                        │
     │       │                                             │
     │  Router Namespace (10.10.1.1 & 10.10.2.1/24)        │
     │       │ (ip_forward=1)                              │
     │      veth-r-s (10.10.2.0/24)                        │
     │       │                                             │
     │  Server Namespace (10.10.2.2/24)                   │
     │                                                     │
     │       Fault Injection Layer (tc netem)              │
     │       ├── Latency (e.g. 50 ms)                      │
     │       ├── Packet Loss (e.g. 2%)                     │
     │       ├── RFC 3393 Jitter (e.g. ±5 ms)              │
     │       ├── Bandwidth Limit (e.g. 50 Mbps)            │
     │       └── Packet Corruption                         │
     │                                                     │
     └─────────────────────────────────────────────────────┘
                            │
                            ▼
                  Metrics + Baseline
                            │
                            ▼
                 Regression Intelligence
                            │
                            ▼
               HTML Dashboard / JSON / CSV
```

---

## 2. Core Capabilities

### 2.1 Routed Linux Network Namespace Lab (`app/topology/`)
- **3-Node Topology**: Orchestrates isolated Linux network namespaces (`netpulse-client` $\leftrightarrow$ `netpulse-router` $\leftrightarrow$ `netpulse-server`) connected via virtual Ethernet (`veth`) pairs with IPv4 routing and packet forwarding (`sysctl net.ipv4.ip_forward=1`).
- **Signal-Safe Cleanup**: Automatic exit traps (`atexit`) and signal handlers (`SIGINT`, `SIGTERM`) guarantee no host namespace or virtual link pollution.
- **Unprivileged Graceful Degradation**: Detects whether `CAP_NET_ADMIN` / `root` is available, falling back to local loopback and userland simulation when running unprivileged.

### 2.2 Kernel-Level Fault Injection (`app/faults/`)
- **Linux Traffic Control (`tc netem`)**: Directly configures kernel queueing disciplines (`qdisc`) on virtual interfaces:
  - **Latency**: Precise one-way packet delays (5ms to 500ms).
  - **Jitter**: Delay variation modeling with normal distribution correlation.
  - **Packet Loss**: Deterministic or probabilistic datagram drops (0.1% to 100%).
  - **Rate Limiting**: Token Bucket Filter (`tbf`) bandwidth constraints (10 Mbps to 1 Gbps).
  - **Corruption**: Single-bit error injection into datagram payloads.
- **Standard Impairment Profiles**: `clean`, `high_latency`, `lossy`, `constrained`, `jittery`, `severe_loss`.

### 2.3 Controlled Experiment Engine (`app/experiments/`)
- **Control vs. Experiment Methodology**: Automatically runs a clean **Control Phase** followed by an impaired **Experiment Phase**, recording delta impact ($\Delta \text{throughput}$, $\Delta \text{latency}$, $\Delta \text{loss}$, $\Delta \text{jitter}$).
- **Degradation Classification**: Differentiates between `EXPECTED_DEGRADATION` (due to intentional fault injection) and `UNEXPECTED_REGRESSION`.

### 2.4 Multi-Protocol Networking & Deep Dissection
- **TCP Engine**: Byte stream framing, chunked buffer accumulation, half-close detection, and `TCP_NODELAY` tuning.
- **UDP Loss & Jitter Engine**: 16-byte binary sequence header (`!QQ`: uint64 sequence number + uint64 timestamp) computing packet loss and RFC 3393 Inter-Packet Delay Variation (IPDV).
- **HTTP/1.1 Engine**: Connection pooling and embedded test server.
- **Scapy Packet Dissection**: Decodes L2 MACs, L3 IP headers, and L4 TCP control flags (`SYN`, `ACK`, `FIN`, `RST`, `PSH`, `URG`).

### 2.5 Statistical Validation & Baseline Stability
- Computes sample mean, median, min, max, sample standard deviation ($\sigma$), variance, P95/P99 percentiles, and the Coefficient of Variation ($CV = \sigma / \mu$) across multi-iteration runs to verify environment measurement stability.

---

## 3. Evidence-Based Portfolio Metrics Audit Table

All metrics below are verified against raw generated test and telemetry files in [`reports/`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/reports).

| Engineering Metric | Measured Value | Verification Methodology | Sample Size | Raw Evidence File | Resume Safe |
| :--- | :---: | :--- | :---: | :---: | :---: |
| **Automated Test Suite** | **105 tests** | Pytest discovery across 6 test suites | 105 tests | [`reports/results.json`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/reports/results.json) | **YES** |
| **Network Configurations** | **44 permutations** | Combinatorial L4-L7 parameter generator | 44 configs | [`reports/configuration_matrix.csv`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/reports/configuration_matrix.csv) | **YES** |
| **Validated Executions** | **5,000+** | High-iteration stress runner | 5,000+ runs | [`reports/stress_summary.json`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/reports/stress_summary.json) | **YES** |
| **Average Socket Latency** | **0.087 ms** | Monotonic high-resolution timer (`perf_counter_ns`) | 50 RTT probes | [`reports/history.json`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/reports/history.json) | **YES** |
| **P95 Socket Latency** | **0.150 ms** | Statistical percentile interpolation | 50 RTT probes | [`reports/history.json`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/reports/history.json) | **YES** |
| **UDP Throughput** | **600.4 Mbps** | Sustained datagram stream over 1024B buffers | 3.0s duration | [`reports/history.json`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/reports/history.json) | **YES** |
| **Packet Loss Measurement**| **0.00% / 2.00%** | 16-byte `!QQ` binary sequence header validation | 200 packets | [`reports/experiments.json`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/reports/experiments.json) | **YES** |
| **Regression Intelligence**| **100% detection**| Baseline threshold diffing comparator | 4 suites | [`reports/regression.json`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/reports/regression.json) | **YES** |
| **CI/CD Environments** | **4 matrix jobs** | GitHub Actions matrix (Ubuntu/Windows x Py3.11/Py3.12)| 2 OS x 2 Py | [`.github/workflows/tests.yml`](file:///c:/Users/hatas/OneDrive/Desktop/NetPulse/.github/workflows/tests.yml) | **YES** |

---

## 4. Project Directory Layout

```
NetPulse/
├── .github/
│   └── workflows/
│       ├── tests.yml                  # PR workflow: Ruff lint + Python 3.11/3.12 matrix on Ubuntu/Windows
│       └── regression.yml             # Main branch workflow: Full regression, baseline diff & HTML upload
├── app/
│   ├── core/                          # Config, Logging, Exceptions, Retry Engine
│   ├── experiments/                   # ExperimentRunner, Control vs. Experiment, Impact Comparator
│   ├── faults/                        # FaultInjector, Linux tc netem, Impairment Profiles
│   ├── networking/                    # TCPClient/Server, UDPClient/Server, HTTPClient/Server
│   ├── packets/                       # Scapy PacketBuilder, PacketParser, FlowSummary, Capture
│   ├── performance/                   # Latency, Throughput, Loss, Jitter, StatisticalSeries
│   ├── regression/                    # RegressionComparator, BaselineManager, Thresholds
│   ├── reporting/                     # Executive Dashboard, Final Audit, DefectManager, FlakyTracker
│   ├── testing/                       # TestCaseMetadata (@test_case), Matrix, StressRunner, ClaimsAuditor
│   ├── topology/                      # NetworkNamespaceManager, VethPair, VirtualTopologyLab, Cleanup
│   └── cli.py                         # Unified NetPulse CLI
├── docs/                              # Technical documentation & interview deep dives
│   ├── architecture.md                # System design & component interaction
│   ├── networking.md                  # Sockets, framing, and Scapy dissection
│   ├── performance.md                 # Latency percentiles, throughput, jitter formulas
│   ├── fault-injection.md             # Linux tc netem, qdisc, and impairment models
│   ├── regression.md                  # Control vs. Experiment diffing & tolerance thresholds
│   ├── testing-strategy.md            # Test case taxonomy and execution tiers
│   ├── troubleshooting.md             # Operational diagnostics & unprivileged workarounds
│   └── interview-notes.md             # Senior network QA & performance interview talking points
├── reports/                           # Output artifacts
│   ├── dashboard.html                 # Executive interactive HTML dashboard
│   ├── final_project_audit.html       # Authoritative system audit & portfolio report
│   ├── final_project_audit.json       # Machine-readable audit summary
│   ├── portfolio_metrics.json         # Audited resume metrics with raw evidence links
│   ├── configuration_matrix.csv       # Tested network permutations (44 combinations)
│   ├── experiments.json               # Control vs. Experiment measurement logs
│   ├── stress_summary.json            # High-iteration stress execution results
│   ├── results.json                   # Pytest session results
│   ├── baseline.json                  # Authoritative performance baseline
│   └── history.json                   # Historical telemetry trend logs
├── scripts/
│   ├── demo.py                        # Cross-platform end-to-end verification script
│   └── demo.sh                        # Linux bash demonstration script
├── tests/
│   ├── faults/                        # Controlled fault injection tests (NET-FAULT-*)
│   ├── functional/                    # Protocol tests (NET-TCP-*, NET-UDP-*, NET-HTTP-*)
│   ├── integration/                   # Cross-protocol and topology tests (NET-INT-*)
│   ├── performance/                   # Latency, throughput, loss, capture benchmarks (NET-PERF-*)
│   ├── regression/                    # Network invariants and baseline diffing (NET-REG-*)
│   └── unit/                          # Core modules, retry, config, payloads, edge cases (NET-UNIT-*)
└── README.md                          # Engineering portfolio documentation
```

---

## 5. Getting Started & Usage

### 5.1 Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/netpulse.git
cd netpulse

# 2. Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies and package
pip install -r requirements.txt
pip install -e .
```

### 5.2 Command Line Interface (CLI)

```bash
# Run all 105 automated test cases across all suites
pytest -v

# Run controlled Control vs. Experiment fault validation
python -m netpulse experiment --profile lossy

# Execute high-iteration stress validation
python -m netpulse stress --iterations 50 --profile quick

# Generate and export network configuration matrix
python -m netpulse matrix

# Audit all portfolio claims and compile final project audit report
python -m netpulse audit

# Manage Linux Virtual Network Laboratory (requires root / CAP_NET_ADMIN on Linux)
sudo netpulse topology create
sudo netpulse topology status
sudo netpulse topology cleanup
sudo netpulse topology destroy
```

---

## 6. Technical Limitations & Safety

1. **Local & Hermetic Targets**: NetPulse defaults strictly to local interfaces (`127.0.0.1`, `lo`) and private virtual namespaces (`10.10.1.0/24`). It enforces safe traffic limits and bounded durations to prevent accidental stress testing against external systems.
2. **Capability Detection**: Linux namespace manipulation and kernel `tc netem` require `CAP_NET_ADMIN` / root privileges. Unprivileged execution automatically operates in userland simulation mode without error.
3. **Hardware Line Rate**: NetPulse benchmarks operate over standard BSD socket APIs; line-rate multi-gigabit testing on 100GbE NICs would require kernel-bypass drivers (e.g. DPDK, XDP/eBPF).

---

## 7. License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
