"""
NetPulse Linux Traffic Control (tc netem) Fault Controller.

Applies, updates, and clears Linux kernel traffic-control queueing disciplines (qdisc)
using netem and tbf (Token Bucket Filter) for real kernel-level packet delay, loss, jitter,
and bandwidth rate-limiting on virtual Ethernet interfaces.
"""

import subprocess
from typing import Optional

from app.core.logging import get_logger
from app.faults.models import FaultConfig
from app.topology.namespace import NetworkNamespaceManager, has_net_admin_capability

logger = get_logger("faults.tc_netem")


class TCNetemController:
    """
    Manages Linux Traffic Control (tc) qdisc operations for kernel-level network fault injection.
    """

    @classmethod
    def apply_fault(cls, iface: str, config: FaultConfig, ns_name: Optional[str] = None) -> bool:
        """
        Apply tc netem / tbf rules to an interface (optionally inside a network namespace).
        """
        if not has_net_admin_capability():
            logger.warning("Unprivileged: cannot apply kernel tc netem rules.")
            return False

        # First clear any existing qdisc on the interface
        cls.clear_fault(iface, ns_name=ns_name)

        if config.is_clean():
            logger.info(f"Interface '{iface}' set to clean (no active qdisc).")
            return True

        # Build tc netem arguments
        netem_args = ["netem"]

        if config.latency_ms > 0:
            netem_args.extend(["delay", f"{config.latency_ms}ms"])
            if config.jitter_ms > 0:
                netem_args.append(f"{config.jitter_ms}ms")
                if config.correlation_pct > 0:
                    netem_args.append(f"{config.correlation_pct}%")

        if config.packet_loss_percent > 0:
            netem_args.extend(["loss", f"{config.packet_loss_percent}%"])

        if config.corruption_percent > 0:
            netem_args.extend(["corrupt", f"{config.corruption_percent}%"])

        # Execute tc command
        if config.bandwidth_mbps and config.bandwidth_mbps > 0:
            # Handle rate limiting via tbf or netem rate
            netem_args.extend(["rate", f"{config.bandwidth_mbps}mbit"])

        cmd = ["tc", "qdisc", "add", "dev", iface, "root"] + netem_args

        if ns_name:
            if not NetworkNamespaceManager.namespace_exists(ns_name):
                logger.debug(f"Namespace '{ns_name}' does not exist. Skipping kernel tc netem.")
                return False
            code, _, stderr = NetworkNamespaceManager.exec_in_namespace(ns_name, cmd)
        else:
            res = subprocess.run(cmd, capture_output=True, text=True)
            code, stderr = res.returncode, res.stderr

        if code != 0:
            logger.warning(f"tc netem command failed on '{iface}': {stderr.strip()}")
            return False

        logger.info(f"Applied tc netem to '{iface}' (ns={ns_name}): {' '.join(netem_args)}")
        return True

    @classmethod
    def clear_fault(cls, iface: str, ns_name: Optional[str] = None) -> bool:
        """Remove root qdisc from an interface, restoring unconstrained operation."""
        if not has_net_admin_capability():
            return False

        cmd = ["tc", "qdisc", "del", "dev", iface, "root"]
        if ns_name:
            if not NetworkNamespaceManager.namespace_exists(ns_name):
                return True
            code, _, _ = NetworkNamespaceManager.exec_in_namespace(ns_name, cmd)
            return code == 0
        else:
            res = subprocess.run(cmd, capture_output=True, text=True)
            return res.returncode == 0

    @classmethod
    def get_current_qdisc(cls, iface: str, ns_name: Optional[str] = None) -> str:
        """Inspect active qdisc configuration on an interface."""
        if not has_net_admin_capability():
            return "unknown (unprivileged)"

        cmd = ["tc", "qdisc", "show", "dev", iface]
        if ns_name:
            code, stdout, _ = NetworkNamespaceManager.exec_in_namespace(ns_name, cmd)
            return stdout.strip() if code == 0 else ""
        else:
            res = subprocess.run(cmd, capture_output=True, text=True)
            return res.stdout.strip() if res.returncode == 0 else ""
