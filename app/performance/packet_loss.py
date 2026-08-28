"""
NetPulse UDP Packet Loss & Jitter Engine.

Constructs uniquely identifiable UDP datagrams containing sequence numbers and nanosecond timestamps.
Tracks received packets, missing sequence numbers, duplicate packets, out-of-order packets,
and calculates RFC 3393 / RFC 3550 inter-packet delay variation (jitter).
"""

import socket
import struct
import time
from typing import List, Optional, Set, Tuple

from app.core.logging import get_logger
from app.networking.connection import SocketOptions
from app.networking.sockets import create_udp_socket, safe_close
from app.performance.metrics import JitterMetrics, PacketLossMetrics

logger = get_logger("performance.packet_loss")

# Binary Header Format: 64-bit Sequence Number (uint64) + 64-bit Send Timestamp in ns (uint64)
HEADER_STRUCT = struct.Struct("!QQ")
HEADER_SIZE = HEADER_STRUCT.size  # 16 bytes


class UDPPacketLossBenchmark:
    """
    Measures packet loss, duplicate rate, out-of-order delivery, and jitter for UDP streams.
    """

    @staticmethod
    def encode_packet(seq: int, send_time_ns: int, packet_size: int = 1024) -> bytes:
        """
        Encode sequence number and send timestamp into a binary packet with padded payload.
        """
        header = HEADER_STRUCT.pack(seq, send_time_ns)
        pad_length = max(0, packet_size - HEADER_SIZE)
        # Pad with predictable deterministic bytes
        pad = b"\xaa" * pad_length
        return header + pad

    @staticmethod
    def decode_packet(data: bytes) -> Tuple[int, int, bytes]:
        """
        Decode packet into (sequence_number, send_time_ns, payload).
        """
        if len(data) < HEADER_SIZE:
            raise ValueError(f"Packet data size ({len(data)}B) smaller than header size ({HEADER_SIZE}B)")
        seq, send_time_ns = HEADER_STRUCT.unpack(data[:HEADER_SIZE])
        return seq, send_time_ns, data[HEADER_SIZE:]

    @staticmethod
    def encode_sequence_packet(seq: int, send_time_ns: int, payload: bytes = b"") -> bytes:
        """Encode sequence number and send timestamp with arbitrary raw bytes payload."""
        header = HEADER_STRUCT.pack(seq, send_time_ns)
        return header + payload

    @staticmethod
    def decode_sequence_packet(data: bytes) -> Tuple[int, int, bytes]:
        """Decode packet into (sequence_number, send_time_ns, payload)."""
        return UDPPacketLossBenchmark.decode_packet(data)

    @classmethod
    def run_echo_loss_test(
        cls,
        host: str,
        port: int,
        packet_count: int = 100,
        packet_size: int = 1024,
        inter_packet_interval_seconds: float = 0.001,
        timeout: float = 0.05,
        options: Optional[SocketOptions] = None
    ) -> Tuple[PacketLossMetrics, JitterMetrics]:
        """
        Send numbered UDP datagrams to a UDP server and listen for echoes to track loss and jitter.
        """
        opts = options or SocketOptions(timeout=timeout)
        sock = None

        packets_sent = 0
        received_seqs: Set[int] = set()
        duplicate_count = 0
        out_of_order_count = 0
        max_seq_seen = -1

        # Inter-packet delay variations for jitter
        transit_delays_ms: List[float] = []
        inter_arrival_variations_ms: List[float] = []

        prev_send_ns: Optional[int] = None
        prev_recv_ns: Optional[int] = None

        try:
            sock = create_udp_socket(opts)
            sock.settimeout(timeout)

            # Send and receive loop
            for seq in range(packet_count):
                send_ns = time.perf_counter_ns()
                pkt = cls.encode_packet(seq=seq, send_time_ns=send_ns, packet_size=packet_size)
                sock.sendto(pkt, (host, port))
                packets_sent += 1

                # Attempt to receive with a brief window
                try:
                    data, _ = sock.recvfrom(65535)
                    recv_ns = time.perf_counter_ns()

                    if len(data) >= HEADER_SIZE:
                        rec_seq, orig_send_ns, _ = cls.decode_packet(data)

                        if rec_seq in received_seqs:
                            duplicate_count += 1
                        else:
                            received_seqs.add(rec_seq)

                        if rec_seq < max_seq_seen:
                            out_of_order_count += 1
                        else:
                            max_seq_seen = rec_seq

                        # Calculate one-way / RTT transit delay
                        rtt_ms = (recv_ns - orig_send_ns) / 1_000_000.0
                        transit_delays_ms.append(rtt_ms)

                        # Calculate IPDV (RFC 3393) inter-arrival jitter
                        if prev_send_ns is not None and prev_recv_ns is not None:
                            d_send = (orig_send_ns - prev_send_ns) / 1_000_000.0
                            d_recv = (recv_ns - prev_recv_ns) / 1_000_000.0
                            variation = d_recv - d_send
                            inter_arrival_variations_ms.append(variation)

                        prev_send_ns = orig_send_ns
                        prev_recv_ns = recv_ns

                except (socket.timeout, OSError):
                    # Packet drop or timeout
                    pass

                if inter_packet_interval_seconds > 0:
                    time.sleep(inter_packet_interval_seconds)

        except Exception as e:
            logger.warning(f"UDP packet loss benchmark encountered error: {e}")
            if packets_sent == 0:
                raise
        finally:
            if sock:
                safe_close(sock)

        loss_metrics = PacketLossMetrics.calculate(
            packets_sent=packets_sent,
            packets_received=len(received_seqs),
            packet_size=packet_size,
            duplicate_packets=duplicate_count,
            out_of_order_packets=out_of_order_count,
            protocol="UDP"
        )

        jitter_metrics = JitterMetrics.from_delays(
            delays_ms=inter_arrival_variations_ms,
            methodology="RFC 3393 IPDV (Inter-Packet Delay Variation)"
        )

        return loss_metrics, jitter_metrics
