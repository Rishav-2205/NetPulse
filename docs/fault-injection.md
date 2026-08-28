# NetPulse: Fault Injection & Traffic Control (tc netem)

## 1. Architecture: Linux Traffic Control (tc netem)
NetPulse directly configures kernel queueing disciplines (`qdisc`) on network interfaces to inject hardware-accurate network impairments.

```text
+---------------------+        +--------------------+        +---------------------+
|   netpulse-client   |        |   netpulse-router  |        |   netpulse-server   |
|   (10.10.1.2/24)    | ─────> |   (10.10.1.1/24)   | ─────> |   (10.10.2.2/24)    |
+---------------------+        +---------┬----------+        +---------------------+
                                         │
                             tc qdisc add dev veth-r-s root
                             netem delay 50ms 5ms loss 2% rate 50mbit
```

---

## 2. Supported Impairment Parameters

| Parameter | Kernel Command Example | Description |
| :--- | :--- | :--- |
| **Latency** | `tc qdisc add dev veth0 root netem delay 50ms` | Configures static one-way transit delay |
| **Jitter** | `tc qdisc add dev veth0 root netem delay 50ms 10ms 25%` | Configures normal distribution delay variation with correlation |
| **Packet Loss** | `tc qdisc add dev veth0 root netem loss 2%` | Drops 2% of egress datagrams at the network layer |
| **Bandwidth** | `tc qdisc add dev veth0 root netem rate 50mbit` | Enforces token bucket rate limiting on egress traffic |
| **Corruption** | `tc qdisc add dev veth0 root netem corrupt 0.5%` | Injects single-bit errors into packet payloads |

---

## 3. Standard Impairment Profiles

NetPulse ships with built-in profiles in `app/faults/profiles.py`:
- `clean`: 0ms latency, 0% loss, unlimited bandwidth (Control baseline)
- `high_latency`: 100ms latency, ±5ms jitter
- `lossy`: 20ms latency, ±5ms jitter, 2% packet loss
- `constrained`: 20ms latency, 1% packet loss, 50 Mbps bandwidth rate limit
- `jittery`: 30ms latency, ±15ms jitter
- `severe_loss`: 10ms latency, 10% packet drop rate
