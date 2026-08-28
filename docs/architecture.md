# NetPulse: Architectural Deep Dive & System Design

## 1. System Overview
NetPulse is engineered as a modular, layered network validation and performance testing framework. It decouples high-level test orchestration and statistical reporting from low-level Linux kernel network primitives and raw socket APIs.

```
+---------------------------------------------------------------------------------------------------+
|                                      NETPULSE UNIFIED CLI                                          |
|   test | functional | regression | benchmark | topology | fault | experiment | stress | audit      |
+---------------------------------------------------------------------------------------------------+
                                                  │
                 ┌────────────────────────────────┴────────────────────────────────┐
                 ▼                                                                 ▼
+------------------------------------+                           +------------------------------------+
|       CORE RUNTIME ENGINE          |                           |        TEST CASE MANAGEMENT        |
|  - ConfigManager (YAML & Profiles) |                           |  - TestCatalog Taxonomy (NET-*)    |
|  - JSON Lines Structured Logging   |                           |  - TestCaseMetadata & Priority     |
|  - Retry Engine (Jitter & Backoff) |                           |  - Traceability & Matrix Exporters |
+------------------------------------+                           +------------------------------------+
                 │                                                                 │
                 ▼                                                                 ▼
+---------------------------------------------------------------------------------------------------+
|                                 NETWORKING & DISSECTION ENGINES                                   |
|                                                                                                   |
|  [ Layer 4: TCP Engine ]         [ Layer 4: UDP Engine ]            [ Layer 7: HTTP Engine ]      |
|  - Framing & Buffer Chunks       - Binary uint64 Seq Header         - Keep-Alive Connection Pool  |
|  - TCPClient / TCPServer         - Packet Loss & Jitter Engine      - HTTPClient / HTTPServer     |
|                                                                                                   |
|  [ Packet Engine (Scapy) ]       [ Topology & Lab ]                 [ Fault Injection (tc netem) ]|
|  - L2/L3/L4 Packet Dissection    - 3-Node Routed Linux Namespaces   - Latency, Loss, Jitter, Rate |
|  - BPF Filter & Flag Bitmasks    - Veth Pairs & Routing Tables      - Kernel netem + Sim Fallback |
+---------------------------------------------------------------------------------------------------+
                 │                                                                 │
                 ▼                                                                 ▼
+------------------------------------+                           +------------------------------------+
|    REGRESSION & EXPERIMENT ENGINE  |                           |      PRODUCTION-GRADE REPORTING    |
|  - ExperimentRunner (Ctrl vs Exp)  |                           |  - Executive HTML Dashboard        |
|  - RegressionComparator (Diffing)  |                           |  - Multi-Format (JSON, CSV, XML)   |
|  - StatisticalSeries (Mean/P95/CV) |                           |  - Final System Audit Report       |
+------------------------------------+                           +------------------------------------+
                 │                                                                 │
                 └────────────────────────────────┬────────────────────────────────┘
                                                  ▼
+---------------------------------------------------------------------------------------------------+
|                                   CONTAINERIZATION & CI/CD MATRIX                                 |
|  - GitHub Actions Matrix (Python 3.11/3.12 on Ubuntu & Windows)                                    |
|  - Multi-Stage Docker & Compose Targets (functional, regression, performance, network-lab)         |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Core Subsystems

### 2.1 Networking Engine (`app/networking/`)
- **Transport Abstraction**: Sockets are wrapped in non-blocking / configurable timeout interfaces with explicit state transitions (`IDLE` $\rightarrow$ `CONNECTING` $\rightarrow$ `CONNECTED` $\rightarrow$ `CLOSED` / `FAILED`).
- **TCP Framing**: Implements chunked buffer transfers, detecting EOF and remote resets without hanging.
- **UDP Tracking**: Employs a custom 16-byte binary sequence header (`!QQ`: uint64 sequence number + uint64 send timestamp in nanoseconds).

### 2.2 Network Topology & Virtual Lab (`app/topology/`)
- **3-Node Routed Linux Lab**: Builds an isolated multi-subnet virtual network on Linux:
  - `netpulse-client` (`10.10.1.2/24`)
  - `netpulse-router` (`10.10.1.1/24` & `10.10.2.1/24`) with `sysctl -w net.ipv4.ip_forward=1`
  - `netpulse-server` (`10.10.2.2/24`)
- **Lifecycle & Cleanup**: Employs signal traps and exit hooks (`atexit`) ensuring virtual interfaces and namespaces are never orphaned.

### 2.3 Fault Injection Subsystem (`app/faults/`)
- **Traffic Control (tc netem)**: Interacts with kernel queueing disciplines (`qdisc`) on virtual interfaces (`veth-r-s`) to inject deterministic latency, packet loss, jitter, and token bucket rate limits (`tbf`).
- **Userland Fallback**: Gracefully simulates socket drop/delay filters in unprivileged CI/CD environments.

### 2.4 Controlled Experiment Engine (`app/experiments/`)
- **Control vs. Experiment Methodology**: Evaluates performance by comparing a pristine Control run against a Faulted run, calculating delta impact ($\Delta \text{throughput}$, $\Delta \text{latency}$, $\Delta \text{loss}$, $\Delta \text{jitter}$).
- **Classification**: Distinguishes between `EXPECTED_DEGRADATION` (due to intentional fault injection) and `UNEXPECTED_REGRESSION`.
