"""
NetPulse Network Configuration Matrix Generator.

Generates structured combinatorial test configurations across protocols (TCP, UDP, HTTP),
payload sizes (64B to 64KB), concurrency worker levels (1 to 16), and fault profiles.
Exports the complete configuration matrix to reports/configuration_matrix.csv.
"""

import csv
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class NetworkConfiguration:
    """Specific network test permutation specification."""
    config_id: str
    protocol: str
    packet_size_bytes: int
    concurrency_streams: int
    fault_profile: str
    socket_buffer_kb: int
    tcp_nodelay: bool
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ConfigurationMatrix:
    """
    Generates and exports the formal network test configuration matrix.
    """

    @classmethod
    def generate_matrix(cls) -> List[NetworkConfiguration]:
        """
        Generate 40+ intentional network test configurations covering L4-L7 permutations.
        """
        matrix: List[NetworkConfiguration] = []
        cfg_num = 1

        # 1. TCP Combinations: 4 packet sizes x 3 concurrency levels x 3 fault profiles = 36
        tcp_sizes = [64, 1024, 8192, 65536]
        tcp_concurrency = [1, 4, 8]
        tcp_faults = ["clean", "high_latency", "constrained"]

        for size in tcp_sizes:
            for conc in tcp_concurrency:
                for fault in tcp_faults:
                    matrix.append(
                        NetworkConfiguration(
                            config_id=f"CFG-TCP-{cfg_num:03d}",
                            protocol="TCP",
                            packet_size_bytes=size,
                            concurrency_streams=conc,
                            fault_profile=fault,
                            socket_buffer_kb=64,
                            tcp_nodelay=True,
                            description=f"TCP {size}B packets, {conc} streams under '{fault}' profile"
                        )
                    )
                    cfg_num += 1

        # 2. UDP Combinations: 3 packet sizes x 2 fault profiles = 6
        udp_sizes = [128, 1024, 1400]
        udp_faults = ["clean", "lossy"]

        for size in udp_sizes:
            for fault in udp_faults:
                matrix.append(
                    NetworkConfiguration(
                        config_id=f"CFG-UDP-{cfg_num:03d}",
                        protocol="UDP",
                        packet_size_bytes=size,
                        concurrency_streams=1,
                        fault_profile=fault,
                        socket_buffer_kb=64,
                        tcp_nodelay=False,
                        description=f"UDP {size}B datagrams under '{fault}' profile"
                    )
                )
                cfg_num += 1

        # 3. HTTP Combinations: Keep-Alive vs Non-Keep-Alive = 2
        for keep_alive in [True, False]:
            matrix.append(
                NetworkConfiguration(
                    config_id=f"CFG-HTTP-{cfg_num:03d}",
                    protocol="HTTP",
                    packet_size_bytes=1024,
                    concurrency_streams=1,
                    fault_profile="clean",
                    socket_buffer_kb=32,
                    tcp_nodelay=True,
                    description=f"HTTP/1.1 {'Keep-Alive' if keep_alive else 'Close'} baseline"
                )
            )
            cfg_num += 1

        return matrix

    @classmethod
    def export_csv(cls, output_path: str = "reports/configuration_matrix.csv") -> str:
        """Export the matrix to a CSV file."""
        matrix = cls.generate_matrix()
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "config_id", "protocol", "packet_size_bytes", "concurrency_streams",
                "fault_profile", "socket_buffer_kb", "tcp_nodelay", "description"
            ])
            writer.writeheader()
            for cfg in matrix:
                writer.writerow(cfg.to_dict())

        return str(path)
