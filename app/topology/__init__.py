"""
NetPulse Network Topology Subsystem.
"""

from app.topology.model import (
    Node,
    NodeType,
    Link,
    NetworkTopology,
    SimulatedTransitResult,
)
from app.topology.namespace import NetworkNamespaceManager, has_net_admin_capability
from app.topology.veth import VethPair
from app.topology.router import VirtualTopologyLab, TopologyConfig
from app.topology.cleanup import (
    register_topology_for_cleanup,
    cleanup_registered_topologies,
    manual_cleanup_all,
)

__all__ = [
    "Node",
    "NodeType",
    "Link",
    "NetworkTopology",
    "SimulatedTransitResult",
    "NetworkNamespaceManager",
    "has_net_admin_capability",
    "VethPair",
    "VirtualTopologyLab",
    "TopologyConfig",
    "register_topology_for_cleanup",
    "cleanup_registered_topologies",
    "manual_cleanup_all",
]
