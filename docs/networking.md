# NetPulse: Networking & Protocol Implementation Reference

## 1. Transport Layer Protocols

### 1.1 TCP Streaming & Buffer Framing
TCP is a byte-stream protocol without inherent message boundaries. NetPulse implements structured streaming helpers:
- `send_all(data)`: Guarantees complete transmission of data buffers across socket `send()` calls.
- `receive_exact(n)`: Loops over `recv()` until exactly `n` bytes are accumulated, or raises `NetPulseConnectionError` upon premature peer closure (EOF).
- **Socket Options**:
  - `TCP_NODELAY`: Disables Nagle's algorithm for low-latency request-response round-trip testing.
  - `SO_REUSEADDR`: Enables fast socket port re-binding during high-concurrency automated test cycles.

### 1.2 UDP Datagram Tracking & Loss Engine
UDP datagrams are connectionless and inherently unreliable. To measure packet loss, reordering, and jitter:
- **Binary Header Format (`!QQ`)**:
  - 8 bytes: 64-bit Big-Endian unsigned integer (Sequence Number)
  - 8 bytes: 64-bit Big-Endian unsigned integer (Send Timestamp in Nanoseconds)
  - Remaining: Arbitrary payload bytes / deterministic padding (`\xaa`)
- **Loss Calculation**:
  $$\text{Loss Rate (\%)} = \left(\frac{\text{Sent} - \text{Received}}{\text{Sent}}\right) \times 100.0$$
- **Jitter Calculation (RFC 3393 IPDV)**:
  $$\Delta(i-1, i) = (R_i - R_{i-1}) - (S_i - S_{i-1})$$

---

## 2. Packet Capture & Deep Dissection (Scapy)
NetPulse leverages Scapy for deep inspection across Layers 2 through 7:
- **Ethernet (L2)**: Dissects MAC source/destination addresses.
- **IPv4 / IPv6 (L3)**: Dissects IP endpoints, TTL/Hop limits, and protocols.
- **TCP (L4)**: Bitmask extraction of control flags (`SYN`, `ACK`, `FIN`, `RST`, `PSH`, `URG`).
- **UDP (L4)**: Port pairs and datagram payload validation.
- **Flow Aggregation**: Automatically groups bidirectional packet streams into conversation flows.
