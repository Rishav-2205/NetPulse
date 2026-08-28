"""
NetPulse Logical Network Topology Abstraction.

Models simulated network topologies (Client -> Router -> Server), hop-by-hop links,
path MTU, accumulated latency, and packet loss characteristics.
"""

from dataclasses import dataclass
from enum import Enum
import random
from typing import Dict, List, Optional, Set, Tuple

from app.core.exceptions import TopologyError
from app.core.logging import get_logger

logger = get_logger("topology")


class NodeType(str, Enum):
    """Classification of simulated network nodes."""
    CLIENT = "CLIENT"
    ROUTER = "ROUTER"
    SERVER = "SERVER"
    SWITCH = "SWITCH"


@dataclass
class Node:
    """Represents a simulated network node (host, router, server)."""
    name: str
    node_type: NodeType
    ip_address: str
    mac_address: str = "00:00:00:00:00:00"

    def __repr__(self) -> str:
        return f"<Node {self.name} ({self.node_type.value}) {self.ip_address}>"


@dataclass
class Link:
    """Represents a simulated point-to-point link between two nodes."""
    node_a: Node
    node_b: Node
    bandwidth_mbps: float = 1000.0
    latency_ms: float = 1.0
    packet_loss_pct: float = 0.0  # e.g., 1.5 for 1.5% loss
    mtu: int = 1500

    def connects(self, node: Node) -> bool:
        return self.node_a == node or self.node_b == node

    def other_end(self, node: Node) -> Node:
        if self.node_a == node:
            return self.node_b
        elif self.node_b == node:
            return self.node_a
        raise TopologyError(f"Node {node.name} is not connected to link ({self.node_a.name} <-> {self.node_b.name})")


@dataclass
class SimulatedTransitResult:
    """Outcome of transmitting a packet through a simulated path."""
    success: bool
    total_latency_ms: float
    path_mtu: int
    hops: List[str]
    dropped_at_hop: Optional[str] = None
    drop_reason: Optional[str] = None


class NetworkTopology:
    """
    Logical representation of a multi-node network topology with route path calculation.
    """

    def __init__(self, name: str = "Simulated Topology"):
        self.name = name
        self.nodes: Dict[str, Node] = {}
        self.links: List[Link] = []

    def add_node(self, node: Node) -> Node:
        """Register a node in the topology."""
        if node.name in self.nodes:
            raise TopologyError(f"Node '{node.name}' already exists in topology")
        self.nodes[node.name] = node
        return node

    def add_link(
        self,
        node_a_name: str,
        node_b_name: str,
        bandwidth_mbps: float = 1000.0,
        latency_ms: float = 1.0,
        packet_loss_pct: float = 0.0,
        mtu: int = 1500
    ) -> Link:
        """Create a link between two registered nodes."""
        if node_a_name not in self.nodes:
            raise TopologyError(f"Node '{node_a_name}' not found")
        if node_b_name not in self.nodes:
            raise TopologyError(f"Node '{node_b_name}' not found")

        link = Link(
            node_a=self.nodes[node_a_name],
            node_b=self.nodes[node_b_name],
            bandwidth_mbps=bandwidth_mbps,
            latency_ms=latency_ms,
            packet_loss_pct=packet_loss_pct,
            mtu=mtu
        )
        self.links.append(link)
        return link

    def find_path(self, src_name: str, dst_name: str) -> List[Link]:
        """Find the shortest path of links from src to dst via Breadth-First Search."""
        if src_name not in self.nodes or dst_name not in self.nodes:
            raise TopologyError(f"Invalid source or destination: {src_name} -> {dst_name}")

        src = self.nodes[src_name]
        dst = self.nodes[dst_name]

        queue: List[Tuple[Node, List[Link]]] = [(src, [])]
        visited: Set[str] = {src.name}

        while queue:
            current_node, path = queue.pop(0)
            if current_node == dst:
                return path

            for link in self.links:
                if link.connects(current_node):
                    neighbor = link.other_end(current_node)
                    if neighbor.name not in visited:
                        visited.add(neighbor.name)
                        queue.append((neighbor, path + [link]))

        raise TopologyError(f"No path found between {src_name} and {dst_name}")

    def simulate_transmission(
        self,
        src_name: str,
        dst_name: str,
        packet_size_bytes: int,
        deterministic_rng: Optional[random.Random] = None
    ) -> SimulatedTransitResult:
        """
        Simulate packet traversal along the calculated path, applying MTU limits,
        latency accumulation, and packet loss checks.
        """
        path = self.find_path(src_name, dst_name)
        rng = deterministic_rng or random.Random()

        total_latency = 0.0
        min_mtu = 65535
        curr_node = self.nodes[src_name]
        hop_names = [curr_node.name]

        for link in path:
            next_node = link.other_end(curr_node)
            hop_names.append(next_node.name)

            # Check MTU
            if link.mtu < min_mtu:
                min_mtu = link.mtu

            if packet_size_bytes > link.mtu:
                return SimulatedTransitResult(
                    success=False,
                    total_latency_ms=total_latency,
                    path_mtu=min_mtu,
                    hops=hop_names,
                    dropped_at_hop=curr_node.name,
                    drop_reason=f"Packet size ({packet_size_bytes}B) exceeds link MTU ({link.mtu}B)"
                )

            # Check simulated packet loss
            if link.packet_loss_pct > 0:
                roll = rng.random() * 100.0
                if roll < link.packet_loss_pct:
                    return SimulatedTransitResult(
                        success=False,
                        total_latency_ms=total_latency,
                        path_mtu=min_mtu,
                        hops=hop_names,
                        dropped_at_hop=f"{curr_node.name}->{next_node.name}",
                        drop_reason=f"Simulated loss on link ({link.packet_loss_pct}% loss rate)"
                    )

            total_latency += link.latency_ms
            curr_node = next_node

        return SimulatedTransitResult(
            success=True,
            total_latency_ms=total_latency,
            path_mtu=min_mtu,
            hops=hop_names
        )

    @classmethod
    def create_point_to_point(
        cls,
        client_ip: str = "10.0.1.10",
        server_ip: str = "10.0.1.20",
        latency_ms: float = 0.5,
        mtu: int = 1500,
        loss_pct: float = 0.0
    ) -> "NetworkTopology":
        """
        Construct standard Client -> Server direct point-to-point topology.
        """
        topo = cls(name="Point-to-Point Model (Client -> Server)")
        client = Node(name="client", node_type=NodeType.CLIENT, ip_address=client_ip, mac_address="00:11:22:33:44:01")
        server = Node(name="server", node_type=NodeType.SERVER, ip_address=server_ip, mac_address="00:11:22:33:44:02")
        topo.add_node(client)
        topo.add_node(server)
        topo.add_link("client", "server", latency_ms=latency_ms, mtu=mtu, packet_loss_pct=loss_pct)
        return topo

    @classmethod
    def create_standard_three_node(
        cls,
        client_to_router_latency: float = 1.0,
        router_to_server_latency: float = 2.0,
        client_mtu: int = 1500,
        router_mtu: int = 1500,
        loss_pct: float = 0.0
    ) -> "NetworkTopology":
        """
        Construct standard Client -> Router -> Server logical topology.
        """
        topo = cls(name="Standard 3-Node Model (Client -> Router -> Server)")
        client = Node(name="client", node_type=NodeType.CLIENT, ip_address="10.0.1.10", mac_address="00:11:22:33:44:01")
        router = Node(name="router", node_type=NodeType.ROUTER, ip_address="10.0.1.1", mac_address="00:11:22:33:44:02")
        server = Node(name="server", node_type=NodeType.SERVER, ip_address="10.0.2.10", mac_address="00:11:22:33:44:03")

        topo.add_node(client)
        topo.add_node(router)
        topo.add_node(server)

        topo.add_link("client", "router", latency_ms=client_to_router_latency, mtu=client_mtu, packet_loss_pct=loss_pct)
        topo.add_link("router", "server", latency_ms=router_to_server_latency, mtu=router_mtu, packet_loss_pct=loss_pct)
        return topo

    @classmethod
    def create_multi_server(
        cls,
        client_ip: str = "10.0.1.10",
        router_ip: str = "10.0.1.1",
        server_ips: Optional[List[str]] = None,
        link_latencies: Optional[List[float]] = None
    ) -> "NetworkTopology":
        """
        Construct Client -> Router -> Multiple Servers fan-out topology.
        """
        servers = server_ips or ["10.0.2.10", "10.0.3.10", "10.0.4.10"]
        latencies = link_latencies or [1.5, 2.0, 3.0]

        topo = cls(name=f"Fan-Out Topology (Client -> Router -> {len(servers)} Servers)")
        client = Node(name="client", node_type=NodeType.CLIENT, ip_address=client_ip, mac_address="00:11:22:33:44:01")
        router = Node(name="router", node_type=NodeType.ROUTER, ip_address=router_ip, mac_address="00:11:22:33:44:02")

        topo.add_node(client)
        topo.add_node(router)
        topo.add_link("client", "router", latency_ms=1.0, mtu=1500)

        for i, s_ip in enumerate(servers):
            s_name = f"server_{i + 1}"
            s_node = Node(name=s_name, node_type=NodeType.SERVER, ip_address=s_ip, mac_address=f"00:11:22:33:55:{i + 1:02d}")
            topo.add_node(s_node)
            lat = latencies[i % len(latencies)]
            topo.add_link("router", s_name, latency_ms=lat, mtu=1500)

        return topo


class LinuxNamespaceTopology:
    """
    Helper for configuring and documenting Linux network namespace (netns) test topologies
    using veth pairs and traffic control (tc netem) for hardware-isolated performance validation.
    """

    @staticmethod
    def generate_setup_script(
        ns_client: str = "netpulse_cli",
        ns_server: str = "netpulse_srv",
        veth_client: str = "veth-cli",
        veth_server: str = "veth-srv",
        client_ip: str = "10.200.1.1/24",
        server_ip: str = "10.200.1.2/24",
        latency_ms: float = 10.0,
        loss_pct: Optional[float] = None,
        loss_percent: Optional[float] = None
    ) -> str:
        """
        Generate bash script commands to create isolated Linux network namespaces with veth and tc netem.
        """
        actual_loss = loss_percent if loss_percent is not None else (loss_pct if loss_pct is not None else 1.0)
        return f"""#!/bin/bash
# NetPulse Linux Namespace & Virtual Ethernet Setup
set -e

echo "[NetPulse] Creating network namespaces: {ns_client}, {ns_server}"
ip netns add {ns_client}
ip netns add {ns_server}

echo "[NetPulse] Creating veth pair ({veth_client} <--> {veth_server})"
ip link add {veth_client} type veth peer name {veth_server}

echo "[NetPulse] Assigning veth endpoints to namespaces"
ip link set {veth_client} netns {ns_client}
ip link set {veth_server} netns {ns_server}

echo "[NetPulse] Configuring IP addresses and bringing interfaces up"
ip netns exec {ns_client} ip addr add {client_ip} dev {veth_client}
ip netns exec {ns_client} ip link set {veth_client} up
ip netns exec {ns_client} ip link set lo up

ip netns exec {ns_server} ip addr add {server_ip} dev {veth_server}
ip netns exec {ns_server} ip link set {veth_server} up
ip netns exec {ns_server} ip link set lo up

echo "[NetPulse] Applying Traffic Control (tc netem): delay {latency_ms}ms, loss {actual_loss}%"
ip netns exec {ns_client} tc qdisc add dev {veth_client} root netem delay {latency_ms}ms loss {actual_loss}%

echo "[NetPulse] Setup Complete. Run tests with: ip netns exec {ns_client} python -m netpulse benchmark"
"""

    @staticmethod
    def generate_teardown_script(
        ns_client: str = "netpulse_cli",
        ns_server: str = "netpulse_srv"
    ) -> str:
        """Generate bash script to tear down Linux network namespaces."""
        return f"""#!/bin/bash
# NetPulse Linux Namespace Teardown
ip netns del {ns_client} 2>/dev/null || true
ip netns del {ns_server} 2>/dev/null || true
echo "[NetPulse] Cleaned up namespaces: {ns_client}, {ns_server}"
"""
