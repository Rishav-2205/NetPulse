"""
NetPulse High-Level Benchmark Orchestration Runner.

Coordinates execution of TCP/UDP throughput, latency, loss, and jitter benchmarks,
attaching environment metadata, configuration profiles, and packaging into PerformanceResult models.
"""

from typing import Optional

from app.core.logging import get_logger
from app.networking.tcp import TCPServer
from app.networking.udp import UDPServer
from app.performance.latency import LatencyBenchmark
from app.performance.metrics import EnvironmentMetadata, PerformanceResult
from app.performance.packet_loss import UDPPacketLossBenchmark
from app.performance.throughput import TCPThroughputBenchmark, UDPThroughputBenchmark

logger = get_logger("performance.benchmark")


class BenchmarkRunner:
    """
    Orchestrates end-to-end performance benchmarks with automated embedded test servers.
    """

    @classmethod
    def run_tcp_throughput_test(
        cls,
        host: str = "127.0.0.1",
        port: Optional[int] = None,
        duration_seconds: float = 2.0,
        packet_size: int = 8192,
        concurrency: int = 1,
        profile_name: str = "custom"
    ) -> PerformanceResult:
        """
        Run a TCP throughput benchmark against a dedicated or embedded TCPServer.
        """
        server = None
        target_port = port

        try:
            if target_port is None:
                server = TCPServer(host=host, port=0)
                server.start()
                target_port = server.port

            logger.info(f"Starting TCP Throughput test ({concurrency} stream(s), {packet_size}B packets, {duration_seconds}s) on {host}:{target_port}")
            thpt = TCPThroughputBenchmark.run_concurrent(
                host=host,
                port=target_port,
                concurrency=concurrency,
                duration_seconds=duration_seconds,
                packet_size=packet_size
            )

            return PerformanceResult(
                test_name="tcp_throughput",
                protocol="TCP",
                packet_size=packet_size,
                packet_count=thpt.packet_count,
                duration_seconds=thpt.duration_seconds,
                concurrency=concurrency,
                throughput=thpt,
                status="PASS",
                profile_name=profile_name,
                environment=EnvironmentMetadata.capture()
            )
        finally:
            if server:
                server.stop()

    @classmethod
    def run_udp_throughput_test(
        cls,
        host: str = "127.0.0.1",
        port: Optional[int] = None,
        duration_seconds: float = 2.0,
        packet_size: int = 1024,
        profile_name: str = "custom"
    ) -> PerformanceResult:
        """
        Run a UDP throughput benchmark.
        """
        server = None
        target_port = port

        try:
            if target_port is None:
                server = UDPServer(host=host, port=0)
                server.start()
                target_port = server.port

            logger.info(f"Starting UDP Throughput test ({packet_size}B packets, {duration_seconds}s) on {host}:{target_port}")
            thpt = UDPThroughputBenchmark.run_single_stream(
                host=host,
                port=target_port,
                duration_seconds=duration_seconds,
                packet_size=packet_size
            )

            return PerformanceResult(
                test_name="udp_throughput",
                protocol="UDP",
                packet_size=packet_size,
                packet_count=thpt.packet_count,
                duration_seconds=thpt.duration_seconds,
                concurrency=1,
                throughput=thpt,
                status="PASS",
                profile_name=profile_name,
                environment=EnvironmentMetadata.capture()
            )
        finally:
            if server:
                server.stop()

    @classmethod
    def run_tcp_latency_test(
        cls,
        host: str = "127.0.0.1",
        port: Optional[int] = None,
        samples_count: int = 50,
        packet_size: int = 64,
        profile_name: str = "custom"
    ) -> PerformanceResult:
        """
        Run a TCP round-trip latency benchmark.
        """
        server = None
        target_port = port

        try:
            if target_port is None:
                server = TCPServer(host=host, port=0)
                server.start()
                target_port = server.port

            logger.info(f"Starting TCP Latency test ({samples_count} samples, {packet_size}B packets) on {host}:{target_port}")
            lat = LatencyBenchmark.measure_tcp_rtt(
                host=host,
                port=target_port,
                samples_count=samples_count,
                packet_size=packet_size
            )

            return PerformanceResult(
                test_name="tcp_latency",
                protocol="TCP",
                packet_size=packet_size,
                packet_count=samples_count,
                duration_seconds=round(lat.avg_ms * samples_count / 1000.0, 4),
                concurrency=1,
                latency=lat,
                status="PASS",
                profile_name=profile_name,
                environment=EnvironmentMetadata.capture()
            )
        finally:
            if server:
                server.stop()

    @classmethod
    def run_udp_latency_test(
        cls,
        host: str = "127.0.0.1",
        port: Optional[int] = None,
        samples_count: int = 50,
        packet_size: int = 64,
        profile_name: str = "custom"
    ) -> PerformanceResult:
        """
        Run a UDP round-trip latency benchmark.
        """
        server = None
        target_port = port

        try:
            if target_port is None:
                server = UDPServer(host=host, port=0)
                server.start()
                target_port = server.port

            logger.info(f"Starting UDP Latency test ({samples_count} samples, {packet_size}B packets) on {host}:{target_port}")
            lat = LatencyBenchmark.measure_udp_rtt(
                host=host,
                port=target_port,
                samples_count=samples_count,
                packet_size=packet_size
            )

            return PerformanceResult(
                test_name="udp_latency",
                protocol="UDP",
                packet_size=packet_size,
                packet_count=samples_count,
                duration_seconds=round(lat.avg_ms * samples_count / 1000.0, 4),
                concurrency=1,
                latency=lat,
                status="PASS",
                profile_name=profile_name,
                environment=EnvironmentMetadata.capture()
            )
        finally:
            if server:
                server.stop()

    @classmethod
    def run_udp_packet_loss_test(
        cls,
        host: str = "127.0.0.1",
        port: Optional[int] = None,
        packet_count: int = 200,
        packet_size: int = 1024,
        drop_rate: float = 0.0,
        profile_name: str = "custom"
    ) -> PerformanceResult:
        """
        Run a UDP packet loss and jitter benchmark with optional simulated server drop rate.
        """
        server = None
        target_port = port

        try:
            if target_port is None:
                server = UDPServer(host=host, port=0, packet_drop_rate=drop_rate)
                server.start()
                target_port = server.port

            logger.info(f"Starting UDP Loss & Jitter test ({packet_count} pkts, {packet_size}B, simulated drop={drop_rate}) on {host}:{target_port}")
            loss, jitter = UDPPacketLossBenchmark.run_echo_loss_test(
                host=host,
                port=target_port,
                packet_count=packet_count,
                packet_size=packet_size
            )

            return PerformanceResult(
                test_name="udp_packet_loss",
                protocol="UDP",
                packet_size=packet_size,
                packet_count=packet_count,
                duration_seconds=0.5,
                concurrency=1,
                packet_loss=loss,
                jitter=jitter,
                status="PASS",
                profile_name=profile_name,
                environment=EnvironmentMetadata.capture()
            )
        finally:
            if server:
                server.stop()

    run_udp_loss_test = run_udp_packet_loss_test
