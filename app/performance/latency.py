"""
NetPulse Latency Benchmark Engine.

Measures round-trip time (RTT), request-response latency, and connection establishment time
using high-resolution monotonic clocks (time.perf_counter_ns) with full percentile calculations.
"""

import socket
import time
from typing import List, Optional

from app.core.exceptions import ConnectionError as NetPulseConnectionError
from app.core.logging import get_logger
from app.networking.connection import SocketOptions
from app.networking.sockets import create_tcp_socket, create_udp_socket, safe_close
from app.packets.builder import PayloadGenerator
from app.performance.metrics import LatencyMetrics

logger = get_logger("performance.latency")


class LatencyBenchmark:
    """
    High-precision latency measurement suite for TCP and UDP protocols.
    """

    @staticmethod
    def measure_connection_time(
        host: str,
        port: int,
        samples_count: int = 20,
        timeout: float = 2.0,
        options: Optional[SocketOptions] = None
    ) -> LatencyMetrics:
        """
        Measure the time required to establish a TCP 3-way handshake connection.
        """
        opts = options or SocketOptions(timeout=timeout, tcp_nodelay=True)
        samples: List[float] = []

        for _ in range(samples_count):
            sock = None
            try:
                sock = create_tcp_socket(opts)
                sock.settimeout(timeout)
                t_start = time.perf_counter_ns()
                sock.connect((host, port))
                t_end = time.perf_counter_ns()
                elapsed_ms = (t_end - t_start) / 1_000_000.0
                samples.append(elapsed_ms)
            except (socket.timeout, OSError) as e:
                logger.warning(f"Connection establishment failed during latency probe: {e}")
            finally:
                if sock:
                    safe_close(sock)

        return LatencyMetrics.from_samples(samples)

    @staticmethod
    def measure_tcp_rtt(
        host: str,
        port: int,
        samples_count: int = 50,
        packet_size: int = 64,
        timeout: float = 2.0,
        options: Optional[SocketOptions] = None
    ) -> LatencyMetrics:
        """
        Measure round-trip request/response latency over an established TCP connection.
        """
        opts = options or SocketOptions(timeout=timeout, tcp_nodelay=True)
        payload = PayloadGenerator.generate_random(size=packet_size, seed=42)
        samples: List[float] = []

        sock = None
        try:
            sock = create_tcp_socket(opts)
            sock.settimeout(timeout)
            sock.connect((host, port))

            for _ in range(samples_count):
                t_start = time.perf_counter_ns()
                sock.sendall(payload)

                # Receive exact bytes back (echo)
                received = bytearray()
                while len(received) < packet_size:
                    chunk = sock.recv(packet_size - len(received))
                    if not chunk:
                        raise NetPulseConnectionError("Socket closed prematurely during TCP RTT probe")
                    received.extend(chunk)

                t_end = time.perf_counter_ns()
                elapsed_ms = (t_end - t_start) / 1_000_000.0
                samples.append(elapsed_ms)

        except Exception as e:
            logger.warning(f"TCP RTT probe encountered an error: {e}")
            if not samples:
                raise
        finally:
            if sock:
                safe_close(sock)

        return LatencyMetrics.from_samples(samples)

    @staticmethod
    def measure_udp_rtt(
        host: str,
        port: int,
        samples_count: int = 50,
        packet_size: int = 64,
        timeout: float = 2.0,
        options: Optional[SocketOptions] = None
    ) -> LatencyMetrics:
        """
        Measure round-trip datagram echo latency over UDP.
        """
        opts = options or SocketOptions(timeout=timeout)
        payload = PayloadGenerator.generate_random(size=packet_size, seed=42)
        samples: List[float] = []

        sock = None
        try:
            sock = create_udp_socket(opts)
            sock.settimeout(timeout)

            for _ in range(samples_count):
                t_start = time.perf_counter_ns()
                sock.sendto(payload, (host, port))
                data, _ = sock.recvfrom(65535)
                t_end = time.perf_counter_ns()

                elapsed_ms = (t_end - t_start) / 1_000_000.0
                samples.append(elapsed_ms)

        except Exception as e:
            logger.warning(f"UDP RTT probe encountered an error: {e}")
            if not samples:
                raise
        finally:
            if sock:
                safe_close(sock)

        return LatencyMetrics.from_samples(samples)
