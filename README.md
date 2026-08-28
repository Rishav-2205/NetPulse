# NetPulse: Automated Network Validation & Performance Testing Framework

[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Testing](https://img.shields.io/badge/pytest-passing-success.svg)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Architecture](https://img.shields.io/badge/architecture-modular-orange.svg)]()

**NetPulse** is a portfolio-grade, automated network validation and performance testing framework built in Python. Designed for enterprise network automation engineers, QA automation architects, and site reliability engineers, NetPulse provides reusable socket abstractions, deterministic payload generators, packet dissection/building via Scapy, embedded multi-threaded test servers, resilient exponential backoff retry engines, structured contextual logging, and automated baseline regression tracking.

---

## Architecture Overview

```mermaid
graph TD
    subgraph Core Engine
        CFG[ConfigManager\nYAML Profiles + Env Overrides]
        LOG[Structured Logger\nJSON Lines + Colored Console]
        RETRY[Retry Engine\nExponential Backoff + Jitter]
        RES[Result Model\nTestResult & SuiteResult]
    end

    subgraph Networking Layer
        TCP_C[TCP Client] <--> TCP_S[Local TCP Echo Server]
        UDP_C[UDP Client] <--> UDP_S[Local UDP Drop/Echo Server]
        HTTP_C[HTTP Client / Session] <--> HTTP_S[Embedded Threading HTTP Server]
    end

    subgraph Packet Subsystem
        GEN[Payload Generator\nSmall / Med / Large / Pattern]
        BLD[Scapy Packet Builder\nL2 / L3 / L4 Frames]
        PRS[Packet Dissector\nHeader Extraction & CRC32/SHA-256]
        CAP[Capture Interface\nPrivilege Detection & Graceful Fallback]
    end

    subgraph Test & Reporting Orchestration
        TOPO[Simulated Topology\nClient -> Router -> Server]
        PYT[Pytest Test Harness\nFixtures & Custom Assertions]
        REP[Reporting Engine\nHTML, JUnit XML, JSON & Baselines]
    end

    CFG --> Networking Layer
    LOG --> Networking Layer
    RETRY --> Networking Layer
    Networking Layer --> PYT
    Packet Subsystem --> PYT
    TOPO --> PYT
    PYT --> RES
    RES --> REP
```

---

## Key Features

- **Protocol Coverage**:
  - **TCP**: Full connection lifecycle, chunked streaming, `receive_exact`, connection timeout detection, connection refused handling, socket option tuning (`TCP_NODELAY`, `SO_REUSEADDR`, `SO_RCVBUF`, `SO_SNDBUF`).
  - **UDP**: Datagram transmission, checksum validation, timeout handling, packet loss rate simulation, and boundary preservation.
  - **HTTP**: `requests.Session` connection pooling, custom headers, query parameters, status code assertions, JSON response parsing, and microsecond-level latency measurement.
- **100% Offline & Reproducible**:
  - Embedded, thread-safe background servers (`TCPServer`, `UDPServer`, `HTTPServer`) binding to ephemeral OS ports (`0`), ensuring zero dependency on external third-party services.
- **Packet Construction & Dissection**:
  - Scapy-powered Layer 2 (Ethernet), Layer 3 (IPv4/ICMP), and Layer 4 (TCP/UDP) builder and parser.
  - Deterministic payload generator with reproducible seeds and CRC32 / SHA-256 integrity verification.
  - Graceful capability degradation when running in unprivileged environments (`CAP_NET_RAW` / root detection).
- **Network Topology Simulation**:
  - Logical `Client -> Router -> Server` model tracking hop-by-hop latency accumulation, link MTU drop enforcement, and packet loss probability.
- **Resilient Retry Engine**:
  - Classifies errors into transient (retryable: socket timeouts, connection aborts) vs deterministic (non-retryable: checksum mismatches, configuration errors).
  - Exponential backoff with jitter and full root-cause exception preservation.
- **Enterprise Reporting & Baseline Regressions**:
  - Generates HTML reports (`reports/report.html`), JUnit XML (`reports/junit.xml`), structured JSON (`reports/results.json`), and baseline diffs (`reports/baseline.json`).

---

## Repository Structure

```
netpulse/
├── app/
│   ├── core/
│   │   ├── config.py           # YAML configuration loader & env var overrides
│   │   ├── exceptions.py       # Custom exception hierarchy
│   │   ├── logging.py          # Structured JSON & colored console loggers
│   │   ├── retry.py            # Exponential backoff retry engine
│   │   └── result.py           # TestResult & SuiteResult data models
│   ├── networking/
│   │   ├── connection.py       # Connection states, Endpoints, SocketOptions
│   │   ├── sockets.py          # Low-level socket creation & option tuning
│   │   ├── tcp.py              # TCPClient & multi-threaded TCPServer
│   │   ├── udp.py              # UDPClient & loss-simulating UDPServer
│   │   └── http.py             # HTTPClient & embedded HTTPServer
│   ├── packets/
│   │   ├── builder.py          # PayloadGenerator & Scapy PacketBuilder
│   │   ├── parser.py           # Header dissector (IPHeader, TCPHeader, UDPHeader)
│   │   └── capture.py          # Sniffing interface with privilege degradation
│   ├── topology/
│   │   └── model.py            # Logical topology (Client -> Router -> Server)
│   ├── testing/
│   │   ├── base_test.py        # BaseNetworkTest with lifecycle timing
│   │   ├── assertions.py       # Domain assertions (assert_latency_within, etc.)
│   │   └── fixtures.py         # Pytest fixtures
│   └── reporting/
│       └── results.py          # BaselineManager & TestReportGenerator
├── tests/
│   ├── conftest.py             # Pytest hooks & automatic result collector
│   ├── functional/             # TCP, UDP, HTTP functional test suites
│   ├── regression/             # Cross-protocol invariants & baseline checks
│   ├── integration/            # Multi-protocol flows & simulated topology routing
│   └── unit/                   # Unit tests for config, retry, payloads, packets, topology
├── configs/
│   ├── default.yaml            # Default network and test parameters
│   └── test_profiles.yaml      # Profiles: fast, stress, ci, regression, debug
├── reports/                    # Generated test reports (HTML, JUnit XML, JSON, baseline)
├── logs/                       # Execution logs (human-readable & JSON lines)
├── scripts/
│   └── run_tests.py            # CLI test runner with profile & baseline options
├── docker/
│   ├── Dockerfile              # Containerized test runner
│   └── docker-compose.yml      # Multi-container orchestration
├── .github/
│   └── workflows/test.yml      # GitHub Actions CI matrix workflow
├── requirements.txt
├── pyproject.toml
├── pytest.ini
└── README.md
```

---

## Installation & Setup

### 1. Local Environment Setup

Clone the repository and install dependencies in an active Python 3.11+ virtual environment:

```bash
# Clone repository
git clone https://github.com/your-org/netpulse.git
cd netpulse

# Install dependencies and netpulse in editable mode
pip install -r requirements.txt
pip install -e .
```

### 2. Linux Setup & Privilege Capabilities

NetPulse runs unprivileged for standard TCP, UDP, HTTP, and topology simulation tests. For raw packet sniffing and Scapy frame injection:

```bash
# Grant raw packet capabilities on Linux without root:
sudo setcap cap_net_raw,cap_net_admin=eip $(readlink -f $(which python3))
```

If unprivileged, NetPulse automatically detects capabilities and degrades to simulated capture mode without crashing test runs.

---

## Running the Automated Test Suite

### 1. Standard Pytest Execution

```bash
# Run the entire test suite with verbose output
pytest -v

# Run specific functional suites
pytest tests/functional
pytest tests/regression
pytest tests/integration
pytest tests/unit

# Run by protocol marker
pytest -m tcp -v
pytest -m udp -v
pytest -m http -v
pytest -m "tcp and functional"
```

### 2. NetPulse CLI Runner (`scripts/run_tests.py`)

NetPulse includes an enterprise CLI runner that supports test profiles, report generation, and baseline comparisons:

```bash
# Run with fast profile
python scripts/run_tests.py --profile fast

# Run TCP tests and generate an official baseline
python scripts/run_tests.py --generate-baseline

# Run tests and verify zero performance or functional regressions
python scripts/run_tests.py --compare-baseline

# Filter by marker
python scripts/run_tests.py -m udp -v
```

---

## Configuration System

Configuration is loaded from `configs/default.yaml` and merged with profiles in `configs/test_profiles.yaml`.

### Environment Variable Overrides

Every configuration value can be overridden via environment variables using the `NETPULSE_<SECTION>_<KEY>` convention:

```bash
export NETPULSE_NETWORK_TCP_TIMEOUT=10.0
export NETPULSE_TESTING_RETRIES=3
export NETPULSE_LOGGING_LEVEL=DEBUG
```

### Available Profiles

| Profile | Purpose | TCP Timeout | Retries | Log Level |
| :--- | :--- | :--- | :--- | :--- |
| `default` | Standard development execution | 5.0s | 2 | INFO |
| `fast` | Rapid test loop during development | 1.5s | 1 | WARNING |
| `ci` | Deterministic CI matrix runs | 5.0s | 2 | INFO |
| `stress` | High-load & buffer stress testing | 10.0s | 3 | INFO |
| `debug` | Verbose troubleshooting & socket tracing | 10.0s | 0 | DEBUG |

---

## Structured Logging & Machine-Readable Output

NetPulse logs simultaneously to:
1. **Console**: Color-coded, human-readable terminal output.
2. **`logs/netpulse.log`**: Traditional log file with timestamps, line numbers, and messages.
3. **`logs/netpulse.json.log`**: Structured JSON Lines format for ingestion into ELK, Datadog, or Grafana Loki.

Example JSON log record:
```json
{
  "timestamp": "2026-08-28T15:18:47.123456+00:00",
  "level": "INFO",
  "logger": "netpulse.tcp",
  "message": "Connected to 127.0.0.1:60337",
  "module": "tcp",
  "line": 56,
  "protocol": "TCP",
  "destination": "127.0.0.1:60337",
  "status": "CONNECTED"
}
```

---

## Docker & Containerization

Build and run the containerized test suite:

```bash
# Build and run unprivileged container
docker compose -f docker/docker-compose.yml up --build netpulse-test

# Run with raw packet capabilities
docker compose -f docker/docker-compose.yml up --build netpulse-raw-capable
```

---

## Stage 1 Validation Summary

| Test Suite | Total Tests | Passed | Failed | Status |
| :--- | :--- | :--- | :--- | :--- |
| TCP Functional | 10 | 10 | 0 | **PASS** |
| UDP Functional | 7 | 7 | 0 | **PASS** |
| HTTP Functional | 8 | 8 | 0 | **PASS** |
| Multi-Protocol Integration | 3 | 3 | 0 | **PASS** |
| Baseline Regression | 4 | 4 | 0 | **PASS** |
| Framework Unit Tests | 22 | 22 | 0 | **PASS** |
| **Total** | **54** | **54** | **0** | **100% PASS** |

---

## Stage 2 Roadmap (Coming Next)

- [ ] L2 / L3 Raw Socket Packet Crafting & ARP / ICMP Probing
- [ ] Hardware Interface Sniffing with BPF filters
- [ ] Jitter, Bandwidth & Throughput Performance Benchmarking Engine
- [ ] Automated Failure Injection (Chaos network simulator: packet corruption, duplication, reordering)
- [ ] Real-time Metrics Dashboard & Prometheus Exporter
