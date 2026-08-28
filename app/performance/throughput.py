"""
NetPulse Network Throughput Benchmark Engine.

Measures raw TCP and UDP throughput across single and concurrent streams,
calculating real megabits per second (Mbps) based on actual socket byte counts and microsecond durations.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from typing import List, Optional

from app.core.logging import get_logger
from app.networking.connection import SocketOptions
from app.networking.sockets import create_tcp_socket, create_udp_socket, safe_close
from app.packets.builder import PayloadGenerator
from app.performance.metrics import ThroughputMetrics

logger = get_logger("performance.throughput")


class TCPThroughputBenchmark:
    """
    Measures TCP stream throughput via high-speed payload transmission.
    """

    @staticmethod
    def run_single_stream(
        host: str,
        port: int,
        duration_seconds: Optional[float] = 2.0,
        total_bytes: Optional[int] = None,
        packet_size: int = 8192,
        options: Optional[SocketOptions] = None
    ) -> ThroughputMetrics:
        """
        Execute a single-stream TCP throughput benchmark for a given duration or byte count.
        """
        opts = options or SocketOptions(timeout=5.0, tcp_nodelay=True, so_rcvbuf=65536, so_sndbuf=65536)
        payload = PayloadGenerator.generate_random(size=packet_size, seed=42)

        sock = None
        bytes_transferred = 0
        packets_sent = 0
        t_start = 0
        t_end = 0

        try:
            sock = create_tcp_socket(opts)
            sock.settimeout(5.0)
            sock.connect((host, port))

            t_start = time.perf_counter_ns()
            end_time_ns = (t_start + int(duration_seconds * 1_000_000_000)) if duration_seconds else None

            while True:
                sock.sendall(payload)
                bytes_transferred += len(payload)
                packets_sent += 1

                curr_time_ns = time.perf_counter_ns()

                if end_time_ns is not None and curr_time_ns >= end_time_ns:
                    t_end = curr_time_ns
                    break

                if total_bytes is not None and bytes_transferred >= total_bytes:
                    t_end = curr_time_ns
                    break

            if t_end == 0:
                t_end = time.perf_counter_ns()

        except Exception as e:
            t_end = time.perf_counter_ns() if t_start > 0 else 0
            logger.warning(f"TCP throughput benchmark encountered error after {bytes_transferred} bytes: {e}")
            if bytes_transferred == 0:
                raise
        finally:
            if sock:
                safe_close(sock)

        elapsed_seconds = (t_end - t_start) / 1_000_000_000.0 if (t_start > 0 and t_end > t_start) else 0.0
        return ThroughputMetrics.calculate(
            protocol="TCP",
            bytes_transferred=bytes_transferred,
            duration_seconds=elapsed_seconds,
            packet_count=packets_sent
        )

    @classmethod
    def run_concurrent(
        cls,
        host: str,
        port: int,
        concurrency: int = 4,
        duration_seconds: float = 2.0,
        packet_size: int = 8192,
        options: Optional[SocketOptions] = None
    ) -> ThroughputMetrics:
        """
        Execute concurrent multi-stream TCP throughput benchmark and aggregate total throughput.
        """
        if concurrency <= 1:
            return cls.run_single_stream(
                host=host,
                port=port,
                duration_seconds=duration_seconds,
                packet_size=packet_size,
                options=options
            )

        total_bytes = 0
        total_packets = 0
        durations: List[float] = []

        with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="TCP-Thpt") as executor:
            futures = [
                executor.submit(
                    cls.run_single_stream,
                    host,
                    port,
                    duration_seconds,
                    None,
                    packet_size,
                    options
                )
                for _ in range(concurrency)
            ]

            for future in as_completed(futures):
                try:
                    res = future.result()
                    total_bytes += res.bytes_transferred
                    total_packets += res.packet_count
                    durations.append(res.duration_seconds)
                except Exception as e:
                    logger.warning(f"Concurrent TCP stream failed: {e}")

        avg_duration = sum(durations) / len(durations) if durations else duration_seconds
        return ThroughputMetrics.calculate(
            protocol=f"TCP (concurrency={concurrency})",
            bytes_transferred=total_bytes,
            duration_seconds=avg_duration,
            packet_count=total_packets
        )


class UDPThroughputBenchmark:
    """
    Measures UDP datagram transmission throughput.
    """

    @staticmethod
    def run_single_stream(
        host: str,
        port: int,
        duration_seconds: Optional[float] = 2.0,
        packet_count: Optional[int] = None,
        packet_size: int = 1024,
        options: Optional[SocketOptions] = None
    ) -> ThroughputMetrics:
        """
        Execute a single UDP stream throughput benchmark.
        """
        opts = options or SocketOptions(timeout=2.0)
        payload = PayloadGenerator.generate_random(size=packet_size, seed=42)

        sock = None
        bytes_transferred = 0
        packets_sent = 0
        t_start = 0
        t_end = 0

        try:
            sock = create_udp_socket(opts)
            t_start = time.perf_counter_ns()
            end_time_ns = (t_start + int(duration_seconds * 1_000_000_000)) if duration_seconds else None

            while True:
                sock.sendto(payload, (host, port))
                bytes_transferred += len(payload)
                packets_sent += 1

                curr_time_ns = time.perf_counter_ns()

                if end_time_ns is not None and curr_time_ns >= end_time_ns:
                    t_end = curr_time_ns
                    break

                if packet_count is not None and packets_sent >= packet_count:
                    t_end = curr_time_ns
                    break

            if t_end == 0:
                t_end = time.perf_counter_ns()

        except Exception as e:
            t_end = time.perf_counter_ns() if t_start > 0 else 0
            logger.warning(f"UDP throughput benchmark encountered error: {e}")
            if bytes_transferred == 0:
                raise
        finally:
            if sock:
                safe_close(sock)

        elapsed_seconds = (t_end - t_start) / 1_000_000_000.0 if (t_start > 0 and t_end > t_start) else 0.0
        return ThroughputMetrics.calculate(
            protocol="UDP",
            bytes_transferred=bytes_transferred,
            duration_seconds=elapsed_seconds,
            packet_count=packets_sent
        )
