# NetPulse: Testing Strategy & Test Case Taxonomy

## 1. Test ID Taxonomy
NetPulse implements an enterprise test case metadata standard (`@test_case`) across all test modules:

| Test Suite | ID Pattern | OSI Layer | Description |
| :--- | :--- | :--- | :--- |
| **TCP Functional** | `NET-TCP-*` | Layer 4 | Framing, buffer chunks, disconnects, flags |
| **UDP Functional** | `NET-UDP-*` | Layer 4 | Datagram echo, broadcast, boundary preservation |
| **HTTP Functional** | `NET-HTTP-*` | Layer 7 | Status codes, keep-alive pooling, headers |
| **Integration** | `NET-INT-*` | Cross-Layer | End-to-end multi-protocol & topology routing |
| **Performance** | `NET-PERF-*` | Layer 4 & L7 | Throughput, latency percentiles, loss, jitter |
| **Regression** | `NET-REG-*` | Cross-Layer | Baseline invariants & diff engine verification |
| **Fault Injection** | `NET-FAULT-*`| Layer 3 & L4 | Impairment testing (latency, loss, jitter, limits) |
| **Unit Tests** | `NET-UNIT-*` | L2-L7 | Core retry, config, packets, payloads, topology |

---

## 2. Test Execution Workflow
- **Unprivileged Mode (Default)**: Normal functional tests, unit tests, and simulated fault injection execute cleanly without requiring elevated root privileges.
- **Privileged Mode (Optional Network Lab)**: Executed with `sudo` or in Docker containers with `CAP_NET_ADMIN` to create real Linux namespaces and `tc netem` rules.
