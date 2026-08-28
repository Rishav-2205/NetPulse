"""
NetPulse Performance Metrics & Statistical Data Models.

Defines dataclasses for throughput, latency percentiles, UDP packet loss,
and inter-packet delay variation (jitter) with serialization and calculation utilities.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import math
import os
import platform
import socket
import statistics
import sys
from typing import Any, Dict, List, Optional


@dataclass
class LatencyMetrics:
    """Statistical distribution of round-trip or transit latency samples."""
    min_ms: float = 0.0
    max_ms: float = 0.0
    avg_ms: float = 0.0
    median_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    samples_count: int = 0
    samples_ms: List[float] = field(default_factory=list, repr=False)

    @classmethod
    def from_samples(cls, samples: List[float]) -> "LatencyMetrics":
        """
        Calculate statistical metrics from a list of latency samples in milliseconds.
        """
        if not samples:
            return cls()

        sorted_samples = sorted(samples)
        n = len(sorted_samples)

        def percentile(p: float) -> float:
            if n == 1:
                return sorted_samples[0]
            k = (n - 1) * (p / 100.0)
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return sorted_samples[int(k)]
            d0 = sorted_samples[int(f)] * (c - k)
            d1 = sorted_samples[int(c)] * (k - f)
            return d0 + d1

        min_val = round(sorted_samples[0], 4)
        max_val = round(sorted_samples[-1], 4)
        avg_val = round(statistics.mean(sorted_samples), 4)
        med_val = round(statistics.median(sorted_samples), 4)
        p95_val = round(percentile(95.0), 4)
        p99_val = round(percentile(99.0), 4)

        return cls(
            min_ms=min_val,
            max_ms=max_val,
            avg_ms=avg_val,
            median_ms=med_val,
            p95_ms=p95_val,
            p99_ms=p99_val,
            samples_count=n,
            samples_ms=sorted_samples
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Limit sample serialization to avoid massive JSON blobs
        if len(data.get("samples_ms", [])) > 50:
            data["samples_ms"] = data["samples_ms"][:50]
        return data


@dataclass
class ThroughputMetrics:
    """Network throughput metrics computed from actual transferred bytes and duration."""
    protocol: str = "TCP"
    bytes_transferred: int = 0
    duration_seconds: float = 0.0
    throughput_mbps: float = 0.0
    throughput_kbps: float = 0.0
    throughput_gbps: float = 0.0
    packet_count: int = 0
    rate_pps: float = 0.0

    @classmethod
    def calculate(
        cls,
        protocol: str,
        bytes_transferred: int,
        duration_seconds: float,
        packet_count: int = 0
    ) -> "ThroughputMetrics":
        """
        Calculate throughput from measured bytes and duration in seconds.
        Formula: Throughput (Mbps) = (bytes * 8) / (duration_seconds * 1,000,000)
        """
        if duration_seconds <= 0 or bytes_transferred <= 0:
            return cls(protocol=protocol, bytes_transferred=bytes_transferred, duration_seconds=max(0.0, duration_seconds))

        bits = bytes_transferred * 8.0
        mbps = bits / (duration_seconds * 1_000_000.0)
        kbps = bits / (duration_seconds * 1_000.0)
        gbps = bits / (duration_seconds * 1_000_000_000.0)
        pps = packet_count / duration_seconds if duration_seconds > 0 else 0.0

        return cls(
            protocol=protocol,
            bytes_transferred=bytes_transferred,
            duration_seconds=round(duration_seconds, 6),
            throughput_mbps=round(mbps, 4),
            throughput_kbps=round(kbps, 4),
            throughput_gbps=round(gbps, 6),
            packet_count=packet_count,
            rate_pps=round(pps, 2)
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PacketLossMetrics:
    """UDP packet loss and sequence tracking metrics."""
    protocol: str = "UDP"
    packet_size: int = 0
    packets_sent: int = 0
    packets_received: int = 0
    packets_missing: int = 0
    duplicate_packets: int = 0
    out_of_order_packets: int = 0
    packet_loss_percent: float = 0.0

    @classmethod
    def calculate(
        cls,
        packets_sent: int,
        packets_received: int,
        packet_size: int = 0,
        duplicate_packets: int = 0,
        out_of_order_packets: int = 0,
        protocol: str = "UDP"
    ) -> "PacketLossMetrics":
        """
        Calculate packet loss percentage based on observed send/receive counts.
        """
        missing = max(0, packets_sent - packets_received)
        loss_pct = (missing / packets_sent * 100.0) if packets_sent > 0 else 0.0

        return cls(
            protocol=protocol,
            packet_size=packet_size,
            packets_sent=packets_sent,
            packets_received=packets_received,
            packets_missing=missing,
            duplicate_packets=duplicate_packets,
            out_of_order_packets=out_of_order_packets,
            packet_loss_percent=round(loss_pct, 4)
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class JitterMetrics:
    """
    Inter-packet delay variation (jitter) metrics for UDP streams.

    Methodology:
    Computes statistical inter-packet delay variation (IPDV, RFC 3393 / RFC 3550):
    D(i-1, i) = (R_i - R_{i-1}) - (S_i - S_{i-1})
    Average Jitter = mean(|D|)
    Max Jitter = max(|D|)
    """
    protocol: str = "UDP"
    average_jitter_ms: float = 0.0
    max_jitter_ms: float = 0.0
    jitter_samples_ms: List[float] = field(default_factory=list, repr=False)
    methodology: str = "RFC 3393 IPDV (Inter-Packet Delay Variation)"

    @classmethod
    def from_delays(cls, delays_ms: List[float], methodology: str = "RFC 3393 IPDV") -> "JitterMetrics":
        """
        Calculate jitter metrics from a list of transit delay differences (inter-arrival variations).
        """
        if not delays_ms or len(delays_ms) < 2:
            return cls(methodology=methodology)

        abs_variations = [abs(d) for d in delays_ms]
        avg_j = round(statistics.mean(abs_variations), 4)
        max_j = round(max(abs_variations), 4)

        return cls(
            protocol="UDP",
            average_jitter_ms=avg_j,
            max_jitter_ms=max_j,
            jitter_samples_ms=abs_variations[:50],
            methodology=methodology
        )

    @property
    def mean_jitter_ms(self) -> float:
        return self.average_jitter_ms

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EnvironmentMetadata:
    """Execution environment details for benchmark reproducibility."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hostname: str = field(default_factory=socket.gethostname)
    os: str = field(default_factory=lambda: f"{platform.system()} {platform.release()} ({platform.machine()})")
    python_version: str = field(default_factory=lambda: f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    cpu_count: int = field(default_factory=lambda: os.cpu_count() or 1)
    git_commit: str = "unknown"

    @classmethod
    def capture(cls) -> "EnvironmentMetadata":
        meta = cls()
        try:
            import subprocess
            res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                meta.git_commit = res.stdout.strip()
        except Exception:
            pass
        return meta

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PerformanceResult:
    """
    Standardized, self-contained result container for all network performance benchmarks.
    """
    test_name: str
    protocol: str  # TCP, UDP, HTTP
    packet_size: int = 0
    packet_count: int = 0
    duration_seconds: float = 0.0
    concurrency: int = 1
    throughput: Optional[ThroughputMetrics] = None
    latency: Optional[LatencyMetrics] = None
    packet_loss: Optional[PacketLossMetrics] = None
    jitter: Optional[JitterMetrics] = None
    status: str = "PASS"
    error: Optional[str] = None
    profile_name: str = "default"
    environment: EnvironmentMetadata = field(default_factory=EnvironmentMetadata.capture)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to a structured dictionary."""
        data = {
            "test_name": self.test_name,
            "protocol": self.protocol,
            "packet_size": self.packet_size,
            "packet_count": self.packet_count,
            "duration_seconds": self.duration_seconds,
            "concurrency": self.concurrency,
            "status": self.status,
            "error": self.error,
            "profile_name": self.profile_name,
            "environment": self.environment.to_dict(),
            "details": self.details
        }
        if self.throughput:
            data["throughput"] = self.throughput.to_dict()
        if self.latency:
            data["latency"] = self.latency.to_dict()
        if self.packet_loss:
            data["packet_loss"] = self.packet_loss.to_dict()
        if self.jitter:
            data["jitter"] = self.jitter.to_dict()
        return data
