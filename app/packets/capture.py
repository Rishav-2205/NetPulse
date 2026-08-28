"""
NetPulse Packet Capture Interface with Graceful Capability Degradation.

Detects OS privileges (CAP_NET_RAW, root, WinPcap/Npcap) and provides
live sniffing when available or simulated capture fallbacks.
"""

import os
import platform
import socket
from typing import List, Optional

from scapy.packet import Packet

from app.core.logging import get_logger

logger = get_logger("packets.capture")


def has_raw_socket_capability() -> bool:
    """
    Check if the current process has the privileges necessary to open raw sockets.
    On Linux: root or CAP_NET_RAW.
    On Windows: Administrator + Npcap / WinPcap driver.
    """
    system = platform.system().lower()

    if system == "linux":
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            return True
        # Try creating a raw socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
            sock.close()
            return True
        except (PermissionError, OSError):
            return False

    elif system == "windows":
        try:
            # On Windows, raw sockets require admin rights
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
            sock.close()
            return True
        except (PermissionError, OSError):
            return False

    return False


class PacketCaptureSession:
    """
    Captures network packets live (if privileged) or accumulates packets via a simulated sink.
    Supports BPF filtering, interface selection, packet limits, and protocol identification.
    """

    def __init__(
        self,
        filter_bpf: Optional[str] = None,
        iface: Optional[str] = None,
        packet_limit: Optional[int] = None,
        timeout: Optional[float] = None
    ):
        self.filter_bpf = filter_bpf
        self.iface = iface
        self.packet_limit = packet_limit
        self.timeout = timeout
        self.captured_packets: List[Packet] = []
        self.is_privileged = has_raw_socket_capability()
        self._is_capturing = False
        self._sniffer = None

    @property
    def captured_count(self) -> int:
        return len(self.captured_packets)

    def start(self) -> "PacketCaptureSession":
        """Start capturing packets."""
        self._is_capturing = True
        if not self.is_privileged:
            logger.warning("Unprivileged environment: live packet sniffing is disabled. Operating in simulated capture mode.")
            return self

        try:
            from scapy.sendrecv import AsyncSniffer
            self._sniffer = AsyncSniffer(
                filter=self.filter_bpf,
                iface=self.iface,
                prn=self._on_packet,
                count=self.packet_limit or 0,
                timeout=self.timeout,
                store=True
            )
            self._sniffer.start()
            logger.info("Live packet capture started", extra={"filter": self.filter_bpf, "iface": self.iface})
        except Exception as e:
            logger.warning(f"Could not initialize live sniffer ({e}). Falling back to simulated mode.")
            self._sniffer = None

        return self

    def _on_packet(self, pkt: Packet) -> None:
        self.captured_packets.append(pkt)
        if self.packet_limit and len(self.captured_packets) >= self.packet_limit:
            self._is_capturing = False

    def record_simulated_packet(self, pkt: Packet) -> None:
        """Inject a packet into the capture session for simulated test environments."""
        self.captured_packets.append(pkt)

    def get_protocol_distribution(self) -> dict[str, int]:
        """Return counts of identified protocols in captured packets."""
        counts: dict[str, int] = {}
        for pkt in self.captured_packets:
            for layer in pkt.layers():
                name = layer.__name__
                counts[name] = counts.get(name, 0) + 1
        return counts

    def stop(self) -> List[Packet]:
        """Stop capturing and return all captured packets."""
        self._is_capturing = False
        if self._sniffer is not None:
            try:
                self._sniffer.stop()
                if hasattr(self._sniffer, "results") and self._sniffer.results:
                    for pkt in self._sniffer.results:
                        if pkt not in self.captured_packets:
                            self.captured_packets.append(pkt)
            except Exception as e:
                logger.debug(f"Error stopping sniffer: {e}")
            self._sniffer = None

        logger.info(f"Packet capture stopped. Captured {len(self.captured_packets)} packets.")
        return self.captured_packets

    def __enter__(self) -> "PacketCaptureSession":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False
