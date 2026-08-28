"""
NetPulse Packet Capture Interface with Graceful Capability Degradation.

Detects OS privileges (CAP_NET_RAW, root, WinPcap/Npcap) and provides
live sniffing when available or simulated capture fallbacks.
"""

import os
import platform
import socket
import sys
import threading
from typing import Callable, List, Optional

from scapy.packet import Packet

from app.core.exceptions import TestExecutionError
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
    """

    def __init__(self, filter_bpf: Optional[str] = None, iface: Optional[str] = None):
        self.filter_bpf = filter_bpf
        self.iface = iface
        self.captured_packets: List[Packet] = []
        self.is_privileged = has_raw_socket_capability()
        self._is_capturing = False
        self._sniffer = None

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
                store=True
            )
            self._sniffer.start()
            logger.info("Live packet capture started")
        except Exception as e:
            logger.warning(f"Could not initialize live sniffer ({e}). Falling back to simulated mode.")
            self._sniffer = None

        return self

    def _on_packet(self, pkt: Packet) -> None:
        self.captured_packets.append(pkt)

    def record_simulated_packet(self, pkt: Packet) -> None:
        """Inject a packet into the capture session for simulated test environments."""
        self.captured_packets.append(pkt)

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
