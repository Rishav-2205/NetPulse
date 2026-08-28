"""
NetPulse Unified Fault Injector.

Orchestrates fault injection across both real Linux kernel traffic-control (tc netem)
and transparent userland simulation fallback for unprivileged test environments.
"""

from dataclasses import dataclass
from typing import Optional, Union

from app.core.logging import get_logger
from app.faults.models import FaultConfig, FaultProfile
from app.faults.profiles import FaultProfileRegistry
from app.faults.tc_netem import TCNetemController
from app.topology.namespace import has_net_admin_capability

logger = get_logger("faults.injector")


@dataclass
class ActiveFaultState:
    """Represents the currently applied fault state on a target interface or virtual link."""
    target_interface: str
    target_namespace: Optional[str]
    config: FaultConfig
    mode: str  # "KERNEL_TC_NETEM" or "USERLAND_SIMULATION"


class FaultInjector:
    """
    Unified fault injection controller managing active impairments.
    """

    _active_fault: Optional[ActiveFaultState] = None

    @classmethod
    def apply(
        cls,
        fault: Union[str, FaultConfig, FaultProfile],
        interface: str = "veth-r-s",
        namespace: Optional[str] = "netpulse-router"
    ) -> ActiveFaultState:
        """
        Apply a fault profile or config to an interface.
        """
        if isinstance(fault, str):
            profile = FaultProfileRegistry.get_profile(fault)
            if not profile:
                raise ValueError(f"Unknown fault profile: '{fault}'")
            config = profile.config
        elif isinstance(fault, FaultProfile):
            config = fault.config
        elif isinstance(fault, FaultConfig):
            config = fault
        else:
            raise TypeError(f"Invalid fault configuration type: {type(fault)}")

        mode = "KERNEL_TC_NETEM" if has_net_admin_capability() else "USERLAND_SIMULATION"

        if mode == "KERNEL_TC_NETEM":
            TCNetemController.apply_fault(interface, config, ns_name=namespace)
        else:
            logger.info(
                f"[Simulated Fault] Active impairment: latency={config.latency_ms}ms, "
                f"loss={config.packet_loss_percent}%, jitter={config.jitter_ms}ms, "
                f"bandwidth={config.bandwidth_mbps or 'unlimited'} Mbps"
            )

        state = ActiveFaultState(
            target_interface=interface,
            target_namespace=namespace,
            config=config,
            mode=mode
        )
        cls._active_fault = state
        return state

    @classmethod
    def clear(cls) -> bool:
        """Clear the currently active network fault."""
        if cls._active_fault is None:
            return True

        if cls._active_fault.mode == "KERNEL_TC_NETEM":
            TCNetemController.clear_fault(
                cls._active_fault.target_interface,
                ns_name=cls._active_fault.target_namespace
            )

        logger.info(f"Cleared active fault on '{cls._active_fault.target_interface}'")
        cls._active_fault = None
        return True

    @classmethod
    def get_active_fault(cls) -> Optional[ActiveFaultState]:
        """Retrieve currently active fault state."""
        return cls._active_fault
