"""
NetPulse Linux Network Namespace Manager.

Provides robust, exception-safe management of Linux network namespaces (netns),
IP address assignments, interface state transitions, routing table entries,
and process execution within isolated network namespaces.
"""

import os
import platform
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple

from app.core.exceptions import TopologyError
from app.core.logging import get_logger

logger = get_logger("topology.namespace")


def has_net_admin_capability() -> bool:
    """
    Check if current process has root privileges or Linux CAP_NET_ADMIN capability.
    """
    if platform.system().lower() != "linux":
        return False
    try:
        # Check EUID or capability
        if os.geteuid() == 0:
            return True
        # Check capsh if available
        capsh = shutil.which("capsh")
        if capsh:
            res = subprocess.run([capsh, "--print"], capture_output=True, text=True, timeout=1.0)
            if "cap_net_admin" in res.stdout.lower():
                return True
    except Exception:
        pass
    return False


class NetworkNamespaceManager:
    """
    Manages creation, configuration, execution, and deletion of Linux network namespaces.
    """

    _active_namespaces: List[str] = []

    @classmethod
    def require_capability(cls) -> None:
        """Raise TopologyError if running unprivileged on Linux without required capabilities."""
        if not has_net_admin_capability():
            raise TopologyError(
                "Linux network namespace operations require root privileges or CAP_NET_ADMIN.\n"
                "Run command with: sudo netpulse topology <action>"
            )

    @classmethod
    def create_namespace(cls, name: str) -> bool:
        """Create a new network namespace."""
        cls.require_capability()
        if cls.namespace_exists(name):
            logger.debug(f"Namespace '{name}' already exists.")
            return True

        cmd = ["ip", "netns", "add", name]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise TopologyError(f"Failed to create network namespace '{name}': {res.stderr.strip()}")

        if name not in cls._active_namespaces:
            cls._active_namespaces.append(name)

        # Automatically bring loopback UP
        cls.bring_interface_up(name, "lo")
        logger.info(f"Created Linux network namespace: '{name}'")
        return True

    @classmethod
    def delete_namespace(cls, name: str) -> bool:
        """Delete a network namespace."""
        if not has_net_admin_capability():
            return False

        if not cls.namespace_exists(name):
            return True

        cmd = ["ip", "netns", "del", name]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if name in cls._active_namespaces:
            cls._active_namespaces.remove(name)

        if res.returncode == 0:
            logger.info(f"Deleted Linux network namespace: '{name}'")
            return True
        logger.warning(f"Failed to delete namespace '{name}': {res.stderr.strip()}")
        return False

    @classmethod
    def list_namespaces(cls) -> List[str]:
        """List all active network namespaces on the host."""
        if not has_net_admin_capability():
            return []
        try:
            res = subprocess.run(["ip", "netns", "list"], capture_output=True, text=True)
            if res.returncode == 0:
                lines = res.stdout.strip().splitlines()
                return [line.split()[0] for line in lines if line.strip()]
        except Exception:
            pass
        return []

    @classmethod
    def namespace_exists(cls, name: str) -> bool:
        """Check if namespace exists."""
        return name in cls.list_namespaces()

    @classmethod
    def exec_in_namespace(cls, ns_name: str, command: List[str], timeout: Optional[float] = None) -> Tuple[int, str, str]:
        """Execute a command inside a specific network namespace."""
        cls.require_capability()
        full_cmd = ["ip", "netns", "exec", ns_name] + command
        try:
            res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
            return res.returncode, res.stdout, res.stderr
        except subprocess.TimeoutExpired:
            raise TopologyError(f"Command timed out in namespace '{ns_name}': {' '.join(command)}")
        except Exception as e:
            raise TopologyError(f"Failed to exec in namespace '{ns_name}': {e}")

    @classmethod
    def assign_ip(cls, ns_name: str, iface: str, ip_cidr: str) -> bool:
        """Assign an IP address with subnet CIDR to an interface in a namespace."""
        cls.require_capability()
        code, stdout, stderr = cls.exec_in_namespace(ns_name, ["ip", "addr", "add", ip_cidr, "dev", iface])
        if code != 0 and "File exists" not in stderr:
            raise TopologyError(f"Failed to assign IP {ip_cidr} to {iface} in namespace {ns_name}: {stderr}")
        logger.info(f"Assigned IP {ip_cidr} to interface '{iface}' in namespace '{ns_name}'")
        return True

    @classmethod
    def bring_interface_up(cls, ns_name: str, iface: str) -> bool:
        """Bring a network interface UP within a namespace."""
        cls.require_capability()
        code, stdout, stderr = cls.exec_in_namespace(ns_name, ["ip", "link", "set", iface, "up"])
        if code != 0:
            raise TopologyError(f"Failed to bring interface '{iface}' UP in namespace '{ns_name}': {stderr}")
        logger.debug(f"Brought interface '{iface}' UP in namespace '{ns_name}'")
        return True

    @classmethod
    def configure_route(cls, ns_name: str, dest_cidr: str, via_ip: str) -> bool:
        """Add a static routing table entry in a namespace."""
        cls.require_capability()
        cmd = ["ip", "route", "add", dest_cidr, "via", via_ip]
        code, stdout, stderr = cls.exec_in_namespace(ns_name, cmd)
        if code != 0 and "File exists" not in stderr:
            raise TopologyError(f"Failed to add route to {dest_cidr} via {via_ip} in {ns_name}: {stderr}")
        logger.info(f"Configured route in '{ns_name}': {dest_cidr} via {via_ip}")
        return True

    @classmethod
    def enable_ip_forwarding(cls, ns_name: str) -> bool:
        """Enable IPv4 routing/packet forwarding inside a namespace."""
        cls.require_capability()
        cmd = ["sysctl", "-w", "net.ipv4.ip_forward=1"]
        code, stdout, stderr = cls.exec_in_namespace(ns_name, cmd)
        if code != 0:
            raise TopologyError(f"Failed to enable IPv4 forwarding in {ns_name}: {stderr}")
        logger.info(f"Enabled IPv4 forwarding in namespace '{ns_name}'")
        return True

    @classmethod
    def get_namespace_status(cls, ns_name: str) -> Dict[str, any]:
        """Retrieve interface, IP, and routing status for a namespace."""
        if not cls.namespace_exists(ns_name):
            return {"exists": False, "name": ns_name}

        code_links, links_out, _ = cls.exec_in_namespace(ns_name, ["ip", "-brief", "link", "show"])
        code_addrs, addrs_out, _ = cls.exec_in_namespace(ns_name, ["ip", "-brief", "addr", "show"])
        code_routes, routes_out, _ = cls.exec_in_namespace(ns_name, ["ip", "route", "show"])

        return {
            "exists": True,
            "name": ns_name,
            "interfaces": addrs_out.strip().splitlines() if code_addrs == 0 else [],
            "routes": routes_out.strip().splitlines() if code_routes == 0 else [],
        }
