"""
NetPulse Packet Parser & Dissector.

Parses raw network frames and Scapy packets into structured dataclasses
for Layer 2, Layer 3, and Layer 4 header validation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.l2 import Ether
from scapy.packet import Packet

from app.core.exceptions import PacketValidationError
from app.core.logging import get_logger

logger = get_logger("packets.parser")


@dataclass
class IPHeader:
    src: str
    dst: str
    version: int = 4
    ttl: int = 64
    proto: int = 6
    id: int = 0
    flags: str = ""
    chksum: Optional[int] = None


@dataclass
class TCPHeader:
    sport: int
    dport: int
    seq: int
    ack: int
    flags: str
    window: int
    chksum: Optional[int] = None


@dataclass
class UDPHeader:
    sport: int
    dport: int
    length: int
    chksum: Optional[int] = None


@dataclass
class ParsedPacket:
    """Structured representation of a parsed network packet."""
    summary: str
    layers: List[str]
    raw_length: int
    payload: bytes
    ip: Optional[IPHeader] = None
    tcp: Optional[TCPHeader] = None
    udp: Optional[UDPHeader] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_tcp(self) -> bool:
        return self.tcp is not None

    @property
    def has_udp(self) -> bool:
        return self.udp is not None

    @property
    def has_ip(self) -> bool:
        return self.ip is not None


class PacketParser:
    """
    Dissects network packets and validates header fields against expected invariants.
    """

    @staticmethod
    def parse(packet: Union[Packet, bytes]) -> ParsedPacket:
        """Parse raw bytes or a Scapy Packet into a ParsedPacket object."""
        if isinstance(packet, bytes):
            # Attempt to parse as IP or Ether
            try:
                scapy_pkt = IP(packet)
            except Exception:
                try:
                    scapy_pkt = Ether(packet)
                except Exception as e:
                    raise PacketValidationError(f"Unable to parse raw packet bytes: {e}") from e
        else:
            scapy_pkt = packet

        layers = [layer.__name__ for layer in scapy_pkt.layers()]
        raw_bytes = bytes(scapy_pkt)
        summary = scapy_pkt.summary()

        ip_header: Optional[IPHeader] = None
        tcp_header: Optional[TCPHeader] = None
        udp_header: Optional[UDPHeader] = None
        payload = bytes(scapy_pkt.payload) if hasattr(scapy_pkt, "payload") else b""

        # Extract IP Layer
        if scapy_pkt.haslayer(IP):
            ip_layer = scapy_pkt[IP]
            ip_header = IPHeader(
                src=ip_layer.src,
                dst=ip_layer.dst,
                version=ip_layer.version,
                ttl=ip_layer.ttl,
                proto=ip_layer.proto,
                id=ip_layer.id,
                flags=str(ip_layer.flags),
                chksum=ip_layer.chksum
            )

        # Extract TCP Layer
        if scapy_pkt.haslayer(TCP):
            tcp_layer = scapy_pkt[TCP]
            tcp_header = TCPHeader(
                sport=tcp_layer.sport,
                dport=tcp_layer.dport,
                seq=tcp_layer.seq,
                ack=tcp_layer.ack,
                flags=str(tcp_layer.flags),
                window=tcp_layer.window,
                chksum=tcp_layer.chksum
            )
            payload = bytes(tcp_layer.payload)

        # Extract UDP Layer
        if scapy_pkt.haslayer(UDP):
            udp_layer = scapy_pkt[UDP]
            udp_header = UDPHeader(
                sport=udp_layer.sport,
                dport=udp_layer.dport,
                length=udp_layer.len if hasattr(udp_layer, "len") else len(bytes(udp_layer)),
                chksum=udp_layer.chksum
            )
            payload = bytes(udp_layer.payload)

        return ParsedPacket(
            summary=summary,
            layers=layers,
            raw_length=len(raw_bytes),
            payload=payload,
            ip=ip_header,
            tcp=tcp_header,
            udp=udp_header
        )
