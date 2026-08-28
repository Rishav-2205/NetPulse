"""
NetPulse High-Speed Traffic Generator.

Supports configurable multi-stream TCP and UDP traffic generation with rate limiting,
duration/packet count limits, concurrency control, and real-time telemetry metrics.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import time
from typing import List, Optional, Tuple

from app.core.logging import get_logger
from app.networking.connection import SocketOptions
from app.networking.sockets import create_tcp_socket, create_udp_socket, safe_close
from app.packets.builder import PayloadGenerator
from app.performance.metrics import ThroughputMetrics

logger = get_logger("performance.traffic_generator")


@dataclass
class TrafficConfig:
    """Configuration parameters for traffic generation."""
    target_host: str = "127.0.0.1"
    target_port: int = 5001
    protocol: str = "TCP"  # TCP or UDP
    duration_seconds: Optional[float] = 2.0
    packet_count: Optional[int] = None
    packet_size: int = 1024
    concurrency: int = 1
    rate_limit_pps: Optional[int] = None  # None = unthrottled
    socket_options: Optional[SocketOptions] = None


class TrafficGenerator:
    """
    Multi-threaded network traffic generation engine for throughput, stress, and load testing.
    """

    def __init__(self, config: Optional[TrafficConfig] = None):
        self.config = config or TrafficConfig()

    def _generate_tcp_worker(
        self,
        worker_id: int,
        duration_seconds: Optional[float],
        packets_per_worker: Optional[int],
        packet_size: int,
        rate_limit_pps: Optional[int]
    ) -> Tuple[int, int, float]:
        """Worker thread sending streaming TCP traffic."""
        opts = self.config.socket_options or SocketOptions(timeout=5.0, tcp_nodelay=True, so_rcvbuf=65536, so_sndbuf=65536)
        payload = PayloadGenerator.generate_random(size=packet_size, seed=100 + worker_id)

        sock = None
        bytes_sent = 0
        packets_sent = 0
        t_start = 0
        t_end = 0

        try:
            sock = create_tcp_socket(opts)
            sock.settimeout(5.0)
            sock.connect((self.config.target_host, self.config.target_port))

            t_start = time.perf_counter_ns()
            end_ns = (t_start + int(duration_seconds * 1_000_000_000)) if duration_seconds else None
            interval = (1.0 / rate_limit_pps) if rate_limit_pps else 0.0

            while True:
                sock.sendall(payload)
                bytes_sent += len(payload)
                packets_sent += 1

                curr_ns = time.perf_counter_ns()
                if end_ns and curr_ns >= end_ns:
                    t_end = curr_ns
                    break
                if packets_per_worker and packets_sent >= packets_per_worker:
                    t_end = curr_ns
                    break

                if interval > 0:
                    time.sleep(interval)

            if t_end == 0:
                t_end = time.perf_counter_ns()

        except Exception as e:
            t_end = time.perf_counter_ns() if t_start > 0 else 0
            logger.warning(f"TCP Traffic worker {worker_id} terminated: {e}")
        finally:
            if sock:
                safe_close(sock)

        elapsed = (t_end - t_start) / 1_000_000_000.0 if (t_start > 0 and t_end > t_start) else 0.0
        return bytes_sent, packets_sent, elapsed

    def _generate_udp_worker(
        self,
        worker_id: int,
        duration_seconds: Optional[float],
        packets_per_worker: Optional[int],
        packet_size: int,
        rate_limit_pps: Optional[int]
    ) -> Tuple[int, int, float]:
        """Worker thread sending UDP datagram bursts."""
        opts = self.config.socket_options or SocketOptions(timeout=2.0)
        payload = PayloadGenerator.generate_random(size=packet_size, seed=200 + worker_id)

        sock = None
        bytes_sent = 0
        packets_sent = 0
        t_start = 0
        t_end = 0

        try:
            sock = create_udp_socket(opts)
            t_start = time.perf_counter_ns()
            end_ns = (t_start + int(duration_seconds * 1_000_000_000)) if duration_seconds else None
            interval = (1.0 / rate_limit_pps) if rate_limit_pps else 0.0

            while True:
                sock.sendto(payload, (self.config.target_host, self.config.target_port))
                bytes_sent += len(payload)
                packets_sent += 1

                curr_ns = time.perf_counter_ns()
                if end_ns and curr_ns >= end_ns:
                    t_end = curr_ns
                    break
                if packets_per_worker and packets_sent >= packets_per_worker:
                    t_end = curr_ns
                    break

                if interval > 0:
                    time.sleep(interval)

            if t_end == 0:
                t_end = time.perf_counter_ns()

        except Exception as e:
            t_end = time.perf_counter_ns() if t_start > 0 else 0
            logger.warning(f"UDP Traffic worker {worker_id} terminated: {e}")
        finally:
            if sock:
                safe_close(sock)

        elapsed = (t_end - t_start) / 1_000_000_000.0 if (t_start > 0 and t_end > t_start) else 0.0
        return bytes_sent, packets_sent, elapsed

    def start(self) -> ThroughputMetrics:
        """
        Execute traffic generation across configured worker threads and aggregate total metrics.
        """
        concurrency = max(1, self.config.concurrency)
        packets_per_worker = (self.config.packet_count // concurrency) if self.config.packet_count else None
        rate_per_worker = (self.config.rate_limit_pps // concurrency) if self.config.rate_limit_pps else None

        target_fn = self._generate_tcp_worker if self.config.protocol.upper() == "TCP" else self._generate_udp_worker

        total_bytes = 0
        total_packets = 0
        durations: List[float] = []

        with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix=f"TrafficGen-{self.config.protocol}") as executor:
            futures = [
                executor.submit(
                    target_fn,
                    w_id,
                    self.config.duration_seconds,
                    packets_per_worker,
                    self.config.packet_size,
                    rate_per_worker
                )
                for w_id in range(concurrency)
            ]

            for future in as_completed(futures):
                try:
                    b_sent, p_sent, dur = future.result()
                    total_bytes += b_sent
                    total_packets += p_sent
                    durations.append(dur)
                except Exception as e:
                    logger.warning(f"Traffic worker future failed: {e}")

        avg_dur = max(durations) if durations else (self.config.duration_seconds or 0.0)
        return ThroughputMetrics.calculate(
            protocol=self.config.protocol.upper(),
            bytes_transferred=total_bytes,
            duration_seconds=avg_dur,
            packet_count=total_packets
        )
