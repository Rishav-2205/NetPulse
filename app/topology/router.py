"""
NetPulse Multi-Node Virtual Topology Laboratory.

Orchestrates a 3-node routed Linux namespace testbed:
  [ netpulse-client ] (10.10.1.2/24)
         │  veth-c-r
  [ netpulse-router ] (10.10.1.1/24 & 10.10.2.1/24) -- [ip_forward=1]
         │  veth-r-s
  [ netpulse-server ] (10.10.2.2/24)
"""

from dataclasses import dataclass
from typing import Dict, Optional

from app.core.logging import get_logger
from app.topology.namespace import NetworkNamespaceManager, has_net_admin_capability
from app.topology.veth import VethPair

logger = get_logger("topology.lab")


@dataclass
class TopologyConfig:
    """Addressing and naming specifications for the 3-node network laboratory."""
    client_ns: str = "netpulse-client"
    router_ns: str = "netpulse-router"
    server_ns: str = "netpulse-server"

    client_ip: str = "10.10.1.2/24"
    router_client_side_ip: str = "10.10.1.1/24"

    router_server_side_ip: str = "10.10.2.1/24"
    server_ip: str = "10.20.2.2/24" or "10.10.2.2/24"

    client_veth: str = "veth-c"
    router_veth_c: str = "veth-r-c"

    router_veth_s: str = "veth-r-s"
    server_veth: str = "veth-s"

    mtu: int = 1500


class VirtualTopologyLab:
    """
    Constructs and manages the 3-node virtual routed Linux network laboratory.
    """

    def __init__(self, config: Optional[TopologyConfig] = None):
        self.config = config or TopologyConfig()
        self.is_active = False

    def create_topology(self) -> bool:
        """
        Build the entire 3-node routed namespace topology.
        """
        cfg = self.config
        NetworkNamespaceManager.require_capability()
        logger.info("Initializing NetPulse 3-Node Routed Linux Network Laboratory...")

        try:
            # 1. Create 3 namespaces
            NetworkNamespaceManager.create_namespace(cfg.client_ns)
            NetworkNamespaceManager.create_namespace(cfg.router_ns)
            NetworkNamespaceManager.create_namespace(cfg.server_ns)

            # 2. Create Client <--> Router veth pair
            VethPair.create(cfg.client_veth, cfg.router_veth_c, mtu=cfg.mtu)
            veth_cr = VethPair(iface_a=cfg.client_veth, iface_b=cfg.router_veth_c, mtu=cfg.mtu)
            veth_cr.move_to_namespace(cfg.client_veth, cfg.client_ns)
            veth_cr.move_to_namespace(cfg.router_veth_c, cfg.router_ns)

            # 3. Create Router <--> Server veth pair
            VethPair.create(cfg.router_veth_s, cfg.server_veth, mtu=cfg.mtu)
            veth_rs = VethPair(iface_a=cfg.router_veth_s, iface_b=cfg.server_veth, mtu=cfg.mtu)
            veth_rs.move_to_namespace(cfg.router_veth_s, cfg.router_ns)
            veth_rs.move_to_namespace(cfg.server_veth, cfg.server_ns)

            # 4. Assign IP addresses
            NetworkNamespaceManager.assign_ip(cfg.client_ns, cfg.client_veth, "10.10.1.2/24")
            NetworkNamespaceManager.assign_ip(cfg.router_ns, cfg.router_veth_c, "10.10.1.1/24")
            NetworkNamespaceManager.assign_ip(cfg.router_ns, cfg.router_veth_s, "10.10.2.1/24")
            NetworkNamespaceManager.assign_ip(cfg.server_ns, cfg.server_veth, "10.10.2.2/24")

            # 5. Bring all interfaces UP
            NetworkNamespaceManager.bring_interface_up(cfg.client_ns, cfg.client_veth)
            NetworkNamespaceManager.bring_interface_up(cfg.router_ns, cfg.router_veth_c)
            NetworkNamespaceManager.bring_interface_up(cfg.router_ns, cfg.router_veth_s)
            NetworkNamespaceManager.bring_interface_up(cfg.server_ns, cfg.server_veth)

            # 6. Enable IPv4 forwarding on the router
            NetworkNamespaceManager.enable_ip_forwarding(cfg.router_ns)

            # 7. Configure static routes
            # Client routes to 10.10.2.0/24 via 10.10.1.1
            NetworkNamespaceManager.configure_route(cfg.client_ns, "10.10.2.0/24", "10.10.1.1")
            # Server routes to 10.10.1.0/24 via 10.10.2.1
            NetworkNamespaceManager.configure_route(cfg.server_ns, "10.10.1.0/24", "10.10.2.1")

            self.is_active = True
            logger.info("Successfully established 3-node routed Linux network laboratory!")
            return True

        except Exception as e:
            logger.error(f"Failed to create network laboratory: {e}")
            self.destroy_topology()
            raise

    def destroy_topology(self) -> bool:
        """
        Tear down all namespaces and associated veth pairs.
        """
        if not has_net_admin_capability():
            return False

        cfg = self.config
        logger.info("Tearing down NetPulse network laboratory...")
        NetworkNamespaceManager.delete_namespace(cfg.client_ns)
        NetworkNamespaceManager.delete_namespace(cfg.router_ns)
        NetworkNamespaceManager.delete_namespace(cfg.server_ns)
        self.is_active = False
        logger.info("Cleaned up network laboratory namespaces.")
        return True

    def get_topology_status(self) -> Dict[str, any]:
        """
        Check health and configuration status of the virtual laboratory.
        """
        if not has_net_admin_capability():
            return {"active": False, "reason": "Unprivileged / Non-Linux environment"}

        cfg = self.config
        c_stat = NetworkNamespaceManager.get_namespace_status(cfg.client_ns)
        r_stat = NetworkNamespaceManager.get_namespace_status(cfg.router_ns)
        s_stat = NetworkNamespaceManager.get_namespace_status(cfg.server_ns)

        all_exist = c_stat["exists"] and r_stat["exists"] and s_stat["exists"]
        return {
            "active": all_exist,
            "namespaces": {
                "client": c_stat,
                "router": r_stat,
                "server": s_stat,
            },
            "subnets": {
                "client_to_router": "10.10.1.0/24",
                "router_to_server": "10.10.2.0/24"
            }
        }
