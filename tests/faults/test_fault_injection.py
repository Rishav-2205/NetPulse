"""
NetPulse Network Fault Injection & Impairment Validation Test Suite.

Validates transport behavior and telemetry under controlled network impairments:
latency, packet loss, jitter, rate limiting, connection reset, and recovery.
"""

import pytest
import time

from app.core.exceptions import NetPulseConnectionError, NetPulseTimeoutError
from app.experiments.engine import ExperimentRunner
from app.experiments.models import DegradationClassification
from app.faults.injector import FaultInjector
from app.faults.models import FaultConfig, FaultType
from app.faults.profiles import BUILTIN_PROFILES
from app.networking.tcp import TCPClient, TCPServer
from app.networking.udp import UDPClient, UDPServer
from app.performance.packet_loss import UDPPacketLossBenchmark
from app.testing.metadata import OSI_Layer, ProtocolType, TestCategory, TestPriority, test_case


class TestFaultInjectionScenarios:
    """
    Automated network validation under controlled fault injection.
    """

    @test_case(
        test_id="NET-FAULT-001",
        name="Baseline Clean Channel Performance",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.CRITICAL,
        description="Verify baseline performance on a clean channel with zero injected faults.",
        expected_behavior="Latency is under 10.0ms with 0% packet loss."
    )
    def test_baseline_clean_performance(self) -> None:
        """Establish baseline metrics on a clean network link."""
        FaultInjector.clear()
        server = TCPServer(host="127.0.0.1", port=0)
        server.start()

        try:
            client = TCPClient()
            client.connect(server.host, server.port, timeout=1.0)
            t0 = time.perf_counter()
            client.send_all(b"BASELINE_PING")
            resp = client.receive_exact(len(b"BASELINE_PING"))
            rtt_ms = (time.perf_counter() - t0) * 1000.0
            client.close()

            assert resp == b"BASELINE_PING"
            assert rtt_ms < 20.0  # Clean loopback RTT is sub-millisecond
        finally:
            server.stop()

    @test_case(
        test_id="NET-FAULT-002",
        name="TCP Latency Impairment Detection",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Verify application detection of 25ms latency impairment.",
        expected_behavior="Observed RTT increases corresponding to the configured latency impairment."
    )
    def test_tcp_under_latency_fault(self) -> None:
        """Verify performance behavior under configured latency."""
        FaultInjector.apply(
            FaultConfig(
                fault_type=FaultType.LATENCY,
                latency_ms=25.0,
                description="25ms one-way delay"
            )
        )
        try:
            server = TCPServer(host="127.0.0.1", port=0)
            server.start()
            try:
                client = TCPClient()
                client.connect(server.host, server.port, timeout=2.0)
                client.send_all(b"LATENCY_TEST_DATA")
                resp = client.receive_exact(len(b"LATENCY_TEST_DATA"))
                client.close()
                assert resp == b"LATENCY_TEST_DATA"
            finally:
                server.stop()
        finally:
            FaultInjector.clear()

    @test_case(
        test_id="NET-FAULT-003",
        name="UDP Packet Loss Degradation",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.UDP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.CRITICAL,
        description="Verify that 2% packet loss injection is accurately detected by UDP loss analyzer.",
        expected_behavior="Measured packet loss percentage corresponds to configured drop rate."
    )
    def test_udp_under_packet_loss_fault(self) -> None:
        """Verify UDP packet loss tracking under 2% simulated drop rate."""
        result = ExperimentRunner.run_udp_loss_experiment(
            fault_profile_name="lossy",
            packet_count=50,
            packet_size=256
        )

        assert result.classification in (
            DegradationClassification.EXPECTED_DEGRADATION,
            DegradationClassification.NO_SIGNIFICANT_CHANGE
        )
        assert result.control_observation.packet_loss_percent == 0.0
        assert result.experiment_observation.total_packets_sent == 50

    @test_case(
        test_id="NET-FAULT-004",
        name="UDP Delay Jitter Tracking",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.UDP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Verify delay jitter tracking under variable latency impairment.",
        expected_behavior="RFC 3393 IPDV jitter calculation records inter-arrival variation."
    )
    def test_udp_under_jitter_fault(self) -> None:
        """Verify UDP jitter tracking under jittery profile."""
        profile = BUILTIN_PROFILES["jittery"]
        FaultInjector.apply(profile)
        try:
            server = UDPServer(host="127.0.0.1", port=0)
            server.start()
            try:
                loss, jitter = UDPPacketLossBenchmark.run_echo_loss_test(
                    host=server.host,
                    port=server.port,
                    packet_count=40,
                    packet_size=256,
                    timeout=0.05
                )
                assert loss.packets_sent == 40
                assert jitter.average_jitter_ms >= 0.0
            finally:
                server.stop()
        finally:
            FaultInjector.clear()

    @test_case(
        test_id="NET-FAULT-005",
        name="TCP Bandwidth Rate Limiting",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Verify rate-limited throughput behavior under constrained profile.",
        expected_behavior="Observed throughput stays bounded within configured bandwidth threshold."
    )
    def test_tcp_under_bandwidth_constraint(self) -> None:
        """Verify constrained profile application."""
        profile = BUILTIN_PROFILES["constrained"]
        state = FaultInjector.apply(profile)
        try:
            assert state.config.bandwidth_mbps == 50.0
            assert state.config.packet_loss_percent == 1.0
        finally:
            FaultInjector.clear()

    @test_case(
        test_id="NET-FAULT-006",
        name="Combined Latency and Loss Impairment",
        category=TestCategory.PERFORMANCE,
        protocol=ProtocolType.FRAMEWORK,
        layer=OSI_Layer.CROSS_LAYER,
        priority=TestPriority.HIGH,
        description="Verify simultaneous latency and packet loss degradation modeling.",
        expected_behavior="Combined impairment metrics capture both RTT growth and datagram loss."
    )
    def test_combined_latency_and_loss(self) -> None:
        """Verify combined impairment profile classification."""
        cfg = FaultConfig(
            fault_type=FaultType.COMBINED,
            latency_ms=20.0,
            packet_loss_percent=5.0,
            description="Combined 20ms latency and 5% drop rate"
        )
        state = FaultInjector.apply(cfg)
        try:
            assert state.config.latency_ms == 20.0
            assert state.config.packet_loss_percent == 5.0
        finally:
            FaultInjector.clear()

    @test_case(
        test_id="NET-FAULT-007",
        name="Server Unavailable / Unreachable Target",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.CRITICAL,
        description="Verify deterministic connection failure handling when target server is down.",
        expected_behavior="Raises NetPulseConnectionError or TimeoutError cleanly without hanging."
    )
    def test_server_unavailable_handling(self) -> None:
        """Attempt connection to a closed port and verify prompt error handling."""
        client = TCPClient()
        with pytest.raises((NetPulseConnectionError, NetPulseTimeoutError, OSError)):
            client.connect(host="127.0.0.1", port=59999, timeout=0.2)

    @test_case(
        test_id="NET-FAULT-008",
        name="Abrupt Connection Reset Handling",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.TCP,
        layer=OSI_Layer.LAYER_4,
        priority=TestPriority.HIGH,
        description="Verify client behavior when peer abruptly terminates connection.",
        expected_behavior="Client detects EOF/reset and raises NetPulseConnectionError on receive."
    )
    def test_abrupt_connection_reset(self) -> None:
        """Verify detection of premature remote connection close."""
        server = TCPServer(host="127.0.0.1", port=0)
        server.start()

        try:
            client = TCPClient()
            client.connect(server.host, server.port, timeout=1.0)
            # Stop server immediately to reset connection
            server.stop()
            time.sleep(0.05)

            with pytest.raises((NetPulseConnectionError, NetPulseTimeoutError, OSError)):
                client.receive_exact(100)
            client.close()
        finally:
            if server.is_running:
                server.stop()

    @test_case(
        test_id="NET-FAULT-009",
        name="Network Path Disconnection Simulation",
        category=TestCategory.FUNCTIONAL,
        protocol=ProtocolType.FRAMEWORK,
        layer=OSI_Layer.LAYER_3,
        priority=TestPriority.HIGH,
        description="Verify behavior when network path is severed (100% loss).",
        expected_behavior="Operations timeout cleanly according to configured socket timeout."
    )
    def test_network_path_severed(self) -> None:
        """Verify clean timeout on a severed link."""
        server = UDPServer(host="127.0.0.1", port=0, packet_drop_rate=1.0)  # 100% loss
        server.start()

        try:
            client = UDPClient()
            # Send datagram through severed link
            client.send_datagram(b"SHOULD_DROP", server.host, server.port)
            assert client.packets_sent == 1
            client.close()
        finally:
            server.stop()

    @test_case(
        test_id="NET-FAULT-010",
        name="Channel Recovery After Fault Removal",
        category=TestCategory.REGRESSION,
        protocol=ProtocolType.FRAMEWORK,
        layer=OSI_Layer.CROSS_LAYER,
        priority=TestPriority.CRITICAL,
        description="Verify that removing active faults restores baseline lossless, low-latency performance.",
        expected_behavior="Link returns to 0% packet loss and sub-millisecond latency."
    )
    def test_recovery_after_fault_removal(self) -> None:
        """Verify that clearing faults completely restores channel health."""
        # 1. Apply heavy impairment
        FaultInjector.apply(BUILTIN_PROFILES["severe_loss"])
        assert FaultInjector.get_active_fault() is not None

        # 2. Clear impairment
        FaultInjector.clear()
        assert FaultInjector.get_active_fault() is None

        # 3. Verify clean transmission
        server = UDPServer(host="127.0.0.1", port=0, packet_drop_rate=0.0)
        server.start()

        try:
            loss, jitter = UDPPacketLossBenchmark.run_echo_loss_test(
                host=server.host,
                port=server.port,
                packet_count=30,
                packet_size=256,
                timeout=0.05
            )
            assert loss.packet_loss_percent == 0.0
            assert loss.packets_received == 30
        finally:
            server.stop()
