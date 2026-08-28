import React, { useEffect, useState } from 'react';
import { Network, Server, Shield, ArrowRight, AlertTriangle, RefreshCw, Trash2, PlusCircle, CheckCircle2 } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { topologyService } from '../../services/topologyService';
import { TopologyNode, TopologyLink, TopologyState } from '../../types';
import { useAppStore } from '../../stores/useAppStore';

export const TopologyPage: React.FC = () => {
  const { addNotification } = useAppStore();

  const [topology, setTopology] = useState<TopologyState | null>(null);
  const [selectedNode, setSelectedNode] = useState<TopologyNode | null>(null);
  const [selectedLink, setSelectedLink] = useState<TopologyLink | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchTopology = async () => {
    setLoading(true);
    try {
      const data = await topologyService.getTopology();
      setTopology(data);
      if (data.nodes.length > 0 && !selectedNode) {
        setSelectedNode(data.nodes[1]); // Default to router
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTopology();
  }, []);

  const handleCreateLab = async () => {
    addNotification('info', 'Creating Lab', 'Constructing 3-node routed Linux namespace topology...');
    const res = await topologyService.createTopology();
    if (res.success) {
      addNotification('success', 'Lab Ready', 'Routed virtual lab is active.');
      fetchTopology();
    }
  };

  const handleDestroyLab = async () => {
    addNotification('info', 'Destroying Lab', 'Tearing down virtual topology...');
    await topologyService.destroyTopology();
    addNotification('success', 'Lab Destroyed', 'Virtual interfaces cleaned.');
    fetchTopology();
  };

  const handleCleanup = async () => {
    const res = await topologyService.cleanupTopology();
    addNotification('success', 'Cleanup Complete', `Swept and cleaned ${res.cleaned_count} orphaned NetPulse items.`);
    fetchTopology();
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-dark-border pb-4">
        <div>
          <h1 className="text-xl font-bold text-dark-heading tracking-tight">
            Virtual Network Topology Laboratory
          </h1>
          <p className="text-xs text-dark-muted mt-1">
            Multi-node routed Linux network namespaces connected via veth pairs with kernel packet forwarding.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" icon={<RefreshCw className="w-3.5 h-3.5" />} onClick={fetchTopology} isLoading={loading}>
            Refresh
          </Button>
          <Button variant="secondary" size="sm" icon={<Trash2 className="w-3.5 h-3.5" />} onClick={handleCleanup}>
            Cleanup
          </Button>
          <Button variant="primary" size="sm" icon={<PlusCircle className="w-3.5 h-3.5" />} onClick={handleCreateLab}>
            Create Lab
          </Button>
        </div>
      </div>

      {/* Interactive Topology Graph Visualizer */}
      <Card title="Routed 3-Node Virtual Topology" subtitle="Click any node or link to inspect routing tables, MTU, interfaces, and active impairments">
        <div className="relative bg-dark-bg/90 border border-dark-border rounded-xl p-8 min-h-[320px] flex items-center justify-between gap-4 overflow-x-auto">
          {/* Node 1: Client */}
          <div
            onClick={() => {
              setSelectedNode(topology?.nodes[0] || null);
              setSelectedLink(null);
            }}
            className={`flex flex-col items-center p-5 rounded-xl border cursor-pointer transition-all w-60 select-none ${
              selectedNode?.id === 'netpulse-client'
                ? 'bg-netpulse-blue/15 border-netpulse-blue shadow-lg shadow-netpulse-blue/10 scale-105'
                : 'bg-dark-card border-dark-border hover:border-dark-hover'
            }`}
          >
            <div className="w-12 h-12 rounded-full bg-netpulse-blue/20 border border-netpulse-blue/40 flex items-center justify-center text-netpulse-blue mb-3">
              <Server className="w-6 h-6" />
            </div>
            <span className="font-bold text-sm text-dark-heading">netpulse-client</span>
            <span className="text-xs font-mono text-netpulse-blue mt-1">10.10.1.2/24</span>
            <div className="mt-3 flex gap-1">
              <Badge variant="success" size="sm">ACTIVE</Badge>
              <Badge variant="outline" size="sm">veth-c-r</Badge>
            </div>
          </div>

          {/* Link 1: Client <-> Router */}
          <div
            onClick={() => {
              setSelectedLink(topology?.links[0] || null);
              setSelectedNode(null);
            }}
            className={`flex-1 flex flex-col items-center justify-center p-3 rounded-lg border cursor-pointer transition-all select-none ${
              selectedLink?.id === 'link-c-r'
                ? 'bg-netpulse-blue/15 border-netpulse-blue'
                : 'border-dashed border-dark-border hover:bg-dark-hover/40'
            }`}
          >
            <div className="w-full h-0.5 bg-dark-border relative flex items-center justify-center my-3">
              <span className="bg-dark-card px-2 text-[11px] font-mono text-dark-muted border border-dark-border rounded">
                10.10.1.0/24 Link
              </span>
            </div>
            <div className="flex items-center gap-2 text-[11px] font-mono text-dark-muted">
              <span>1000 Mbps</span>
              <span>&bull;</span>
              <span>0.1 ms</span>
              <span>&bull;</span>
              <span className="text-netpulse-green">0% Loss</span>
            </div>
          </div>

          {/* Node 2: Router */}
          <div
            onClick={() => {
              setSelectedNode(topology?.nodes[1] || null);
              setSelectedLink(null);
            }}
            className={`flex flex-col items-center p-5 rounded-xl border cursor-pointer transition-all w-64 select-none ${
              selectedNode?.id === 'netpulse-router'
                ? 'bg-netpulse-purple/15 border-netpulse-purple shadow-lg shadow-netpulse-purple/10 scale-105'
                : 'bg-dark-card border-dark-border hover:border-dark-hover'
            }`}
          >
            <div className="w-12 h-12 rounded-full bg-netpulse-purple/20 border border-netpulse-purple/40 flex items-center justify-center text-netpulse-purple mb-3">
              <Network className="w-6 h-6" />
            </div>
            <span className="font-bold text-sm text-dark-heading">netpulse-router</span>
            <span className="text-xs font-mono text-netpulse-purple mt-1">10.10.1.1 &bull; 10.10.2.1</span>
            <div className="mt-3 flex gap-1">
              <Badge variant="purple" size="sm">ROUTER</Badge>
              <Badge variant="success" size="sm">ip_forward=1</Badge>
            </div>
          </div>

          {/* Link 2: Router <-> Server (With Fault Badges) */}
          <div
            onClick={() => {
              setSelectedLink(topology?.links[1] || null);
              setSelectedNode(null);
            }}
            className={`flex-1 flex flex-col items-center justify-center p-3 rounded-lg border cursor-pointer transition-all select-none ${
              selectedLink?.id === 'link-r-s'
                ? 'bg-netpulse-yellow/15 border-netpulse-yellow'
                : 'border-dashed border-netpulse-yellow/40 bg-netpulse-yellow/5 hover:bg-netpulse-yellow/10'
            }`}
          >
            <div className="w-full h-0.5 bg-netpulse-yellow/50 relative flex items-center justify-center my-3">
              <span className="bg-dark-card px-2 text-[11px] font-mono text-netpulse-yellow border border-netpulse-yellow/40 rounded flex items-center gap-1">
                <AlertTriangle className="w-3 h-3 text-netpulse-yellow" />
                10.10.2.0/24 (Impaired)
              </span>
            </div>
            <div className="flex items-center gap-2 text-[11px] font-mono text-netpulse-yellow">
              <span>50 Mbps Limit</span>
              <span>&bull;</span>
              <span>+20 ms</span>
              <span>&bull;</span>
              <span>2% Loss</span>
            </div>
          </div>

          {/* Node 3: Server */}
          <div
            onClick={() => {
              setSelectedNode(topology?.nodes[2] || null);
              setSelectedLink(null);
            }}
            className={`flex flex-col items-center p-5 rounded-xl border cursor-pointer transition-all w-60 select-none ${
              selectedNode?.id === 'netpulse-server'
                ? 'bg-netpulse-blue/15 border-netpulse-blue shadow-lg shadow-netpulse-blue/10 scale-105'
                : 'bg-dark-card border-dark-border hover:border-dark-hover'
            }`}
          >
            <div className="w-12 h-12 rounded-full bg-netpulse-blue/20 border border-netpulse-blue/40 flex items-center justify-center text-netpulse-blue mb-3">
              <Server className="w-6 h-6" />
            </div>
            <span className="font-bold text-sm text-dark-heading">netpulse-server</span>
            <span className="text-xs font-mono text-netpulse-blue mt-1">10.10.2.2/24</span>
            <div className="mt-3 flex gap-1">
              <Badge variant="success" size="sm">ACTIVE</Badge>
              <Badge variant="outline" size="sm">veth-s-r</Badge>
            </div>
          </div>
        </div>
      </Card>

      {/* Inspector Panel */}
      {selectedNode && (
        <Card title={`Node Inspector: ${selectedNode.name}`} subtitle={`Linux Namespace: ${selectedNode.id}`}>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-dark-bg p-4 rounded-lg border border-dark-border">
              <span className="text-xs font-semibold text-dark-muted uppercase">IP Configuration</span>
              <div className="mt-2 space-y-1">
                {selectedNode.ip_addresses.map((ip, idx) => (
                  <div key={idx} className="font-mono text-xs font-medium text-netpulse-blue">
                    {ip}
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-dark-bg p-4 rounded-lg border border-dark-border">
              <span className="text-xs font-semibold text-dark-muted uppercase">Network Interfaces</span>
              <div className="mt-2 space-y-1">
                {selectedNode.interfaces.map((iface, idx) => (
                  <div key={idx} className="font-mono text-xs font-medium text-dark-heading">
                    {iface} (MTU: 1500)
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-dark-bg p-4 rounded-lg border border-dark-border">
              <span className="text-xs font-semibold text-dark-muted uppercase">Kernel Routing Table</span>
              <div className="mt-2 space-y-1">
                {selectedNode.routes?.map((r, idx) => (
                  <div key={idx} className="font-mono text-[11px] text-dark-text">
                    {r.destination} via {r.gateway} dev {r.interface}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}

      {selectedLink && (
        <Card title={`Link Inspector: ${selectedLink.id}`} subtitle={`Connecting ${selectedLink.source} ↔ ${selectedLink.target}`}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-dark-bg p-4 rounded-lg border border-dark-border">
              <span className="text-xs font-semibold text-dark-muted uppercase">Configured Bandwidth</span>
              <div className="mt-2 text-xl font-bold font-mono text-dark-heading">{selectedLink.bandwidth_mbps} Mbps</div>
            </div>
            <div className="bg-dark-bg p-4 rounded-lg border border-dark-border">
              <span className="text-xs font-semibold text-dark-muted uppercase">Transit Latency</span>
              <div className="mt-2 text-xl font-bold font-mono text-dark-heading">{selectedLink.latency_ms} ms</div>
            </div>
            <div className="bg-dark-bg p-4 rounded-lg border border-dark-border">
              <span className="text-xs font-semibold text-dark-muted uppercase">Packet Loss Rate</span>
              <div className="mt-2 text-xl font-bold font-mono text-dark-heading">{selectedLink.packet_loss_percent}%</div>
            </div>
            <div className="bg-dark-bg p-4 rounded-lg border border-dark-border">
              <span className="text-xs font-semibold text-dark-muted uppercase">Jitter Variation</span>
              <div className="mt-2 text-xl font-bold font-mono text-dark-heading">±{selectedLink.jitter_ms} ms</div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};
