"""
NetPulse Packet Analysis & Dissection Engine.

Extracts deep packet inspection attributes: IP/MAC endpoints, L4 ports, TCP control flags,
payload lengths, and timing metadata across packet streams.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from scapy.layers.inet import IP, TCP, UDP, ICMP
from scapy.layers.l2 import Ether
from scapy.packet import Packet

from app.core.logging import get_logger

logger = get_logger("packets.analyzer")


@dataclass
class PacketSummary:
    """Detailed metadata summary for an individual inspected network packet."""
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    src_mac: Optional[str] = None
    dst_mac: Optional[str] = None
    protocol: str = "UNKNOWN"
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    packet_size: int = 0
    payload_size: int = 0
    tcp_flags: List[str] = field(default_factory=list)
    timestamp: float = 0.0
    layers: List[str] = field(default_factory=list)
    summary_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FlowSummary:
    """Aggregated conversation flow between endpoints."""
    endpoint_a: str
    endpoint_b: str
    protocol: str
    packet_count: int = 0
    total_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PacketAnalyzer:
    """
    Analyzes individual packets and multi-packet capture streams.
    """

    @staticmethod
    def extract_tcp_flags(tcp_layer: TCP) -> List[str]:
        """Translate Scapy TCP flag byte into a list of standard flag names."""
        flags = []
        f_str = str(tcp_layer.flags)
        flag_map = {
            "F": "FIN",
            "S": "SYN",
            "R": "RST",
            "P": "PSH",
            "A": "ACK",
            "U": "URG",
            "E": "ECE",
            "C": "CWR",
        }
        for char, name in flag_map.items():
            if char in f_str:
                flags.append(name)
        return flags

    @classmethod
    def analyze_packet(cls, pkt: Packet) -> PacketSummary:
        """
        Inspect a single Scapy packet and extract full structured metadata.
        """
        layers = [layer.__name__ for layer in pkt.layers()]
        pkt_size = len(pkt)
        summary = PacketSummary(
            packet_size=pkt_size,
            layers=layers,
            timestamp=float(getattr(pkt, "time", 0.0)),
            summary_text=pkt.summary()
        )

        # Layer 2: Ethernet
        if pkt.haslayer(Ether):
            eth = pkt[Ether]
            summary.src_mac = str(eth.src)
            summary.dst_mac = str(eth.dst)

        # Layer 3: IP
        if pkt.haslayer(IP):
            ip = pkt[IP]
            summary.src_ip = str(ip.src)
            summary.dst_ip = str(ip.dst)
            summary.protocol = "IP"

        # Layer 4: TCP
        if pkt.haslayer(TCP):
            tcp = pkt[TCP]
            summary.protocol = "TCP"
            summary.src_port = int(tcp.sport)
            summary.dst_port = int(tcp.dport)
            summary.tcp_flags = cls.extract_tcp_flags(tcp)
            if hasattr(tcp, "payload") and tcp.payload:
                summary.payload_size = len(bytes(tcp.payload))

        # Layer 4: UDP
        elif pkt.haslayer(UDP):
            udp = pkt[UDP]
            summary.protocol = "UDP"
            summary.src_port = int(udp.sport)
            summary.dst_port = int(udp.dport)
            if hasattr(udp, "payload") and udp.payload:
                summary.payload_size = len(bytes(udp.payload))

        # Layer 3: ICMP
        elif pkt.haslayer(ICMP):
            summary.protocol = "ICMP"

        return summary

    @classmethod
    def analyze_stream(cls, packets: List[Packet]) -> Dict[str, Any]:
        """
        Analyze a collection of captured packets to generate flow metrics, protocol breakdown, and flag counts.
        """
        if not packets:
            return {
                "total_packets": 0,
                "total_bytes": 0,
                "protocol_distribution": {},
                "flow_conversations": {},
                "tcp_flags_breakdown": {},
                "avg_packet_size": 0.0,
            }

        summaries = [cls.analyze_packet(p) for p in packets]
        total_packets = len(summaries)
        total_bytes = sum(s.packet_size for s in summaries)

        proto_counts: Dict[str, int] = {}
        flows: Dict[str, int] = {}
        flag_counts: Dict[str, int] = {}

        for s in summaries:
            proto_counts[s.protocol] = proto_counts.get(s.protocol, 0) + 1

            if s.src_ip and s.dst_ip:
                flow_key = f"{s.src_ip}:{s.src_port or 0} -> {s.dst_ip}:{s.dst_port or 0} ({s.protocol})"
                flows[flow_key] = flows.get(flow_key, 0) + 1

            for flag in s.tcp_flags:
                flag_counts[flag] = flag_counts.get(flag, 0) + 1

        return {
            "total_packets": total_packets,
            "total_bytes": total_bytes,
            "avg_packet_size": round(total_bytes / total_packets, 2),
            "protocol_distribution": proto_counts,
            "flow_conversations": flows,
            "tcp_flags_breakdown": flag_counts,
        }

    @classmethod
    def analyze_flows(cls, packets: List[Packet]) -> List[FlowSummary]:
        """Aggregate packet stream into bidirectional conversation flows."""
        flows_map: Dict[tuple, FlowSummary] = {}
        for pkt in packets:
            s = cls.analyze_packet(pkt)
            if not s.src_ip or not s.dst_ip:
                continue
            ep1 = f"{s.src_ip}:{s.src_port or 0}"
            ep2 = f"{s.dst_ip}:{s.dst_port or 0}"
            key_endpoints = tuple(sorted([ep1, ep2]))
            flow_key = (key_endpoints[0], key_endpoints[1], s.protocol)

            if flow_key not in flows_map:
                flows_map[flow_key] = FlowSummary(
                    endpoint_a=key_endpoints[0],
                    endpoint_b=key_endpoints[1],
                    protocol=s.protocol,
                    packet_count=0,
                    total_bytes=0
                )

            flow = flows_map[flow_key]
            flow.packet_count += 1
            flow.total_bytes += s.packet_size

        return list(flows_map.values())

    @classmethod
    def get_protocol_distribution(cls, packets: List[Packet]) -> Dict[str, int]:
        """Count protocol frequency across packet stream."""
        dist: Dict[str, int] = {}
        for pkt in packets:
            s = cls.analyze_packet(pkt)
            dist[s.protocol] = dist.get(s.protocol, 0) + 1
        return dist
