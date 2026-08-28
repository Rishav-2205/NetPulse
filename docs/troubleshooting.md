# NetPulse: Troubleshooting & Operational Diagnostics

## 1. Common Diagnostics & Solutions

### 1.1 "Linux network namespace operations require root/CAP_NET_ADMIN"
- **Cause**: Linux namespace (`ip netns`) and traffic control (`tc`) require elevated Linux capabilities (`CAP_NET_ADMIN`).
- **Solution**:
  - Run the specific topology command with elevated privileges: `sudo netpulse topology create`
  - Or use Docker with capabilities: `docker-compose -f docker/docker-compose.yml run netpulse-raw-capable`
  - In unprivileged environments, NetPulse automatically and transparently operates in userland simulation mode.

### 1.2 "No libpcap provider available ! pcap won't be used"
- **Cause**: Scapy requires WinPcap / Npcap (Windows) or libpcap (Linux) for promiscuous hardware packet sniffing.
- **Solution**:
  - NetPulse detects the missing provider and operates gracefully in simulated capture mode, allowing 100% of packet building, flag dissection, and stream flow aggregation tests to execute cleanly.

### 1.3 Orphaned Namespaces or Virtual Interfaces
- **Cause**: Interrupted test processes (e.g. killed with `kill -9` without invoking cleanup handlers).
- **Solution**:
  - Run the built-in emergency sweep:
    ```bash
    sudo netpulse topology cleanup
    ```
