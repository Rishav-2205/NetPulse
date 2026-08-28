"""
NetPulse Topology Emergency Cleanup & Signal Safety Handler.

Registers atexit hooks and OS signal handlers (SIGINT, SIGTERM) to guarantee
that network namespaces, veth interfaces, and routing rules are reliably destroyed
even on test failures or aborts.
"""

import atexit
import signal
import sys
from typing import List

from app.core.logging import get_logger
from app.topology.namespace import NetworkNamespaceManager, has_net_admin_capability

logger = get_logger("topology.cleanup")

_cleanup_registered = False
_registered_labs: List[any] = []


def register_topology_for_cleanup(lab: any) -> None:
    """Register a VirtualTopologyLab instance for guaranteed teardown."""
    if lab not in _registered_labs:
        _registered_labs.append(lab)
    ensure_signal_handlers()


def cleanup_registered_topologies() -> None:
    """Destroy all registered active network topology labs."""
    for lab in list(_registered_labs):
        try:
            if hasattr(lab, "destroy_topology"):
                lab.destroy_topology()
        except Exception as e:
            logger.warning(f"Error during automatic topology cleanup: {e}")
    _registered_labs.clear()


def manual_cleanup_all() -> int:
    """
    Scan for any orphaned netpulse-* namespaces and interfaces on the host and remove them.
    """
    if not has_net_admin_capability():
        logger.warning("Unprivileged: cannot perform host namespace cleanup.")
        return 0

    count = 0
    all_ns = NetworkNamespaceManager.list_namespaces()
    for ns in all_ns:
        if ns.startswith("netpulse") or ns in ("client", "router", "server"):
            if NetworkNamespaceManager.delete_namespace(ns):
                count += 1
    logger.info(f"Cleaned up {count} orphaned NetPulse network namespaces.")
    return count


def _signal_handler(signum, frame):
    """Handle termination signals safely."""
    sig_name = signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
    logger.warning(f"Received termination signal {sig_name}. Executing emergency topology cleanup...")
    cleanup_registered_topologies()
    manual_cleanup_all()
    sys.exit(128 + signum)


def ensure_signal_handlers() -> None:
    """Ensure atexit and signal handlers are attached."""
    global _cleanup_registered
    if _cleanup_registered:
        return

    atexit.register(cleanup_registered_topologies)

    if sys.platform != "win32":
        try:
            signal.signal(signal.SIGINT, _signal_handler)
            signal.signal(signal.SIGTERM, _signal_handler)
        except Exception as e:
            logger.debug(f"Could not attach signal handlers: {e}")

    _cleanup_registered = True
