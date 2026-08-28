# NetPulse: Senior Network QA & Performance Engineering Interview Reference

This reference document compiles key conceptual deep-dives, architectural rationales, and technical talking points for network automation and performance engineering interviews.

---

## 1. Networking Internals

### Q: What is the fundamental difference between TCP and UDP at the socket layer?
- **TCP (Transmission Control Protocol)**: A connection-oriented, reliable byte-stream protocol. Sockets operate over a stateful three-way handshake (`SYN`, `SYN-ACK`, `ACK`), maintain sliding window flow control, handle dynamic retransmissions via sequence/acknowledgment numbers, and provide congestion control algorithms (e.g. CUBIC, BBR). TCP has no record/message boundary; data sent in separate `send()` calls can arrive coalesced in a single `recv()` call.
- **UDP (User Datagram Protocol)**: A connectionless, unreliable datagram protocol. Datagram boundaries are strictly preserved (each `sendto()` corresponds to one datagram received by `recvfrom()`). There are no handshakes, acknowledgments, or flow control mechanisms, making UDP ideal for real-time telemetry, gaming, and streaming where low latency takes precedence over guaranteed arrival.

### Q: How does NetPulse track packet loss and jitter over UDP?
- NetPulse prepends a 16-byte binary sequence header (`!QQ`: uint64 sequence number + uint64 send timestamp in nanoseconds) to every outgoing UDP datagram.
- The receiver calculates packet loss by comparing received sequence IDs against the continuous integer sequence $[0, N-1]$.
- Jitter is computed via **RFC 3393 Inter-Packet Delay Variation (IPDV)**:
  $$\Delta(i-1, i) = (R_i - R_{i-1}) - (S_i - S_{i-1})$$
  measuring the difference in network transit time between consecutive datagrams.

---

## 2. Performance Engineering & Statistics

### Q: Why are latency percentiles (P95/P99) more valuable than arithmetic average latency?
- Average latency is skewed by outliers and masks tail latency (the "long tail"). In multi-tier distributed systems, a single user request can fan out into hundreds of sub-queries; the total transaction response time is bounded by the slowest sub-query (tail latency). P95/P99 percentiles expose these high-latency spikes caused by garbage collection pauses, TCP retransmissions, or bufferbloat.

### Q: Why measure baseline stability (Coefficient of Variation) before running performance regressions?
- If the test execution environment naturally exhibits a $10\%$ measurement variance ($\sigma / \mu = 0.10$), asserting a $5\%$ regression threshold will cause persistent false alarms. NetPulse calculates $CV$ across repeated baseline runs; if $CV > 0.15$, the environment is marked **VOLATILE** and performance alerts are adjusted.

---

## 3. Linux Networking & Kernel Capabilities

### Q: How do Linux Network Namespaces and Virtual Ethernet (veth) pairs work?
- **Network Namespaces (`netns`)**: Provide isolated copies of the network stack, including routing tables, firewall (iptables/nftables) rules, socket tables, and network interfaces.
- **Veth Pairs**: Virtual Ethernet devices acting as a bidirectional pipe. Packets transmitted into one endpoint immediately emerge on the peer endpoint. Moving one endpoint into a client namespace and the peer into a router namespace enables multi-node topology simulation on a single physical host without hardware switches.

### Q: How does `tc netem` simulate network impairment?
- Linux Traffic Control (`tc`) manages packet scheduling through Queueing Disciplines (`qdisc`).
- `netem` (Network Emulator) is a kernel qdisc module that intercepts outgoing packets on an interface, inserting timer-based delays (latency/jitter), randomly dropping packets (loss), or dropping excess tokens via Token Bucket Filters (`tbf`) for rate limiting.

---

## 4. Architecture & Design Decisions

### Q: Why decouple test orchestration from kernel capabilities?
- Requiring `root` / `CAP_NET_ADMIN` for basic unit or functional tests breaks standard developer workflows and unprivileged CI runners. NetPulse uses capability detection (`has_net_admin_capability()`); privileged environments run real `tc netem` and `ip netns`, while unprivileged environments transparently fall back to socket-level simulation while sharing the exact same test suites and metrics engines.
