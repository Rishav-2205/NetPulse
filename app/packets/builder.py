"""
NetPulse Deterministic Test Payload & Packet Builders.

Generates reproducible payloads (small, medium, large, random, binary pattern)
with checksum calculations and builds Scapy L2/L3/L4 network packets.
"""

import hashlib
import os
import random
from typing import Any, Dict, Optional
import zlib

from scapy.layers.inet import IP, TCP, UDP, ICMP
from scapy.layers.l2 import Ether
from scapy.packet import Packet

from app.core.exceptions import PacketValidationError
from app.core.logging import get_logger

logger = get_logger("packets.builder")


class PayloadGenerator:
    """
    Deterministic payload generator producing verifiable byte payloads for transmission testing.
    """

    @staticmethod
    def generate_small(seed: Optional[int] = 42) -> bytes:
        """Generate a 64-byte deterministic payload."""
        return PayloadGenerator.generate_random(size=64, seed=seed)

    @staticmethod
    def generate_medium(seed: Optional[int] = 42) -> bytes:
        """Generate a 1,024-byte (1KB) deterministic payload."""
        return PayloadGenerator.generate_random(size=1024, seed=seed)

    @staticmethod
    def generate_large(seed: Optional[int] = 42) -> bytes:
        """Generate a 65,536-byte (64KB) deterministic payload."""
        return PayloadGenerator.generate_random(size=65536, seed=seed)

    @staticmethod
    def generate_random(size: int, seed: Optional[int] = None) -> bytes:
        """Generate a random byte sequence of specified size with optional deterministic seed."""
        if seed is not None:
            rng = random.Random(seed)
            # Generate deterministic bytes via integer generation
            return bytes(rng.getrandbits(8) for _ in range(size))
        return os.urandom(size)

    @staticmethod
    def generate_binary_pattern(size: int, pattern: bytes = b"\xaa\x55\x00\xff") -> bytes:
        """Generate a repeated binary pattern up to the requested size."""
        if not pattern:
            raise ValueError("Pattern cannot be empty")
        repeats = (size // len(pattern)) + 1
        return (pattern * repeats)[:size]

    @staticmethod
    def calculate_checksum(data: bytes, algorithm: str = "sha256") -> str:
        """Calculate hexadecimal checksum (sha256, md5, crc32)."""
        alg = algorithm.lower()
        if alg == "sha256":
            return hashlib.sha256(data).hexdigest()
        elif alg == "md5":
            return hashlib.md5(data).hexdigest()
        elif alg == "crc32":
            return f"{zlib.crc32(data) & 0xffffffff:08x}"
        else:
            raise ValueError(f"Unsupported checksum algorithm: {algorithm}")

    @staticmethod
    def verify_checksum(data: bytes, expected_checksum: str, algorithm: str = "sha256") -> bool:
        """Verify that data matches the expected checksum."""
        actual = PayloadGenerator.calculate_checksum(data, algorithm=algorithm)
        if actual.lower() != expected_checksum.lower():
            raise PacketValidationError(
                f"Checksum mismatch ({algorithm}): expected {expected_checksum}, got {actual}",
                expected=expected_checksum,
                actual=actual
            )
        return True


class PacketBuilder:
    """
    Constructs Scapy network packets across Layer 2, Layer 3, and Layer 4.
    """

    @staticmethod
    def build_ethernet(
        src_mac: str = "00:11:22:33:44:55",
        dst_mac: str = "ff:ff:ff:ff:ff:ff",
        eth_type: int = 0x0800
    ) -> Ether:
        """Construct an Ethernet Layer 2 frame."""
        return Ether(src=src_mac, dst=dst_mac, type=eth_type)

    @staticmethod
    def build_ip_packet(
        src_ip: str = "127.0.0.1",
        dst_ip: str = "127.0.0.1",
        ttl: int = 64,
        id: int = 1000,
        flags: str = "DF"
    ) -> IP:
        """Construct an IPv4 Layer 3 header."""
        return IP(src=src_ip, dst=dst_ip, ttl=ttl, id=id, flags=flags)

    @staticmethod
    def build_tcp_packet(
        src_ip: str = "127.0.0.1",
        dst_ip: str = "127.0.0.1",
        sport: int = 12345,
        dport: int = 80,
        flags: str = "S",
        seq: int = 100,
        ack: int = 0,
        payload: bytes = b""
    ) -> Packet:
        """Construct a complete IP/TCP packet."""
        ip_layer = IP(src=src_ip, dst=dst_ip)
        tcp_layer = TCP(sport=sport, dport=dport, flags=flags, seq=seq, ack=ack)
        if payload:
            return ip_layer / tcp_layer / payload
        return ip_layer / tcp_layer

    @staticmethod
    def build_udp_packet(
        src_ip: str = "127.0.0.1",
        dst_ip: str = "127.0.0.1",
        sport: int = 12345,
        dport: int = 5001,
        payload: bytes = b"NetPulse Test Datagram"
    ) -> Packet:
        """Construct a complete IP/UDP packet."""
        ip_layer = IP(src=src_ip, dst=dst_ip)
        udp_layer = UDP(sport=sport, dport=dport)
        return ip_layer / udp_layer / payload

    @staticmethod
    def build_icmp_echo(
        src_ip: str = "127.0.0.1",
        dst_ip: str = "127.0.0.1",
        seq: int = 1,
        id: int = 100,
        payload: bytes = b"NetPulse Ping"
    ) -> Packet:
        """Construct an ICMP Echo Request (Ping) packet."""
        ip_layer = IP(src=src_ip, dst=dst_ip)
        icmp_layer = ICMP(type=8, code=0, id=id, seq=seq)
        return ip_layer / icmp_layer / payload
