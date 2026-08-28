"""
NetPulse Virtual Ethernet (veth) Pair Manager.

Manages creation, namespace movement, MTU configuration, and deletion of Linux veth interface pairs.
"""

from dataclasses import dataclass
import subprocess
from typing import Optional

from app.core.exceptions import TopologyError
from app.core.logging import get_logger
from app.topology.namespace import NetworkNamespaceManager, has_net_admin_capability

logger = get_logger("topology.veth")


@dataclass
class VethPair:
    """Represents a virtual Ethernet peer-to-peer link."""
    iface_a: str
    iface_b: str
    ns_a: Optional[str] = None
    ns_b: Optional[str] = None
    mtu: int = 1500

    @classmethod
    def create(cls, iface_a: str, iface_b: str, mtu: int = 1500) -> "VethPair":
        """Create a new veth interface pair in the root namespace."""
        NetworkNamespaceManager.require_capability()
        cmd = ["ip", "link", "add", iface_a, "type", "veth", "peer", "name", iface_b]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 and "File exists" not in res.stderr:
            raise TopologyError(f"Failed to create veth pair ({iface_a} <-> {iface_b}): {res.stderr.strip()}")

        if mtu != 1500:
            subprocess.run(["ip", "link", "set", iface_a, "mtu", str(mtu)], capture_output=True)
            subprocess.run(["ip", "link", "set", iface_b, "mtu", str(mtu)], capture_output=True)

        logger.info(f"Created veth pair: {iface_a} <--> {iface_b} (MTU: {mtu})")
        return cls(iface_a=iface_a, iface_b=iface_b, mtu=mtu)

    def move_to_namespace(self, iface: str, target_ns: str) -> None:
        """Move one endpoint of the veth pair into a target network namespace."""
        NetworkNamespaceManager.require_capability()
        cmd = ["ip", "link", "set", iface, "netns", target_ns]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise TopologyError(f"Failed to move interface '{iface}' to namespace '{target_ns}': {res.stderr.strip()}")

        if iface == self.iface_a:
            self.ns_a = target_ns
        elif iface == self.iface_b:
            self.ns_b = target_ns

        logger.info(f"Moved interface '{iface}' into namespace '{target_ns}'")

    @classmethod
    def delete(cls, iface: str, ns_name: Optional[str] = None) -> bool:
        """Delete a veth pair (deleting one endpoint automatically tears down the peer)."""
        if not has_net_admin_capability():
            return False

        if ns_name:
            code, _, stderr = NetworkNamespaceManager.exec_in_namespace(ns_name, ["ip", "link", "del", iface])
            return code == 0

        cmd = ["ip", "link", "del", iface]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0
