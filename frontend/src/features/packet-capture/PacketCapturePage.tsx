import React, { useEffect, useState } from 'react';
import { Radio, Play, Square, Filter, RefreshCw, Layers, Terminal, ChevronRight, ChevronDown } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { packetService } from '../../services/packetService';
import { PacketSummary } from '../../types';
import { useAppStore } from '../../stores/useAppStore';

export const PacketCapturePage: React.FC = () => {
  const { addNotification } = useAppStore();

  const [packets, setPackets] = useState<PacketSummary[]>([]);
  const [selectedPacket, setSelectedPacket] = useState<PacketSummary | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [bpfFilter, setBpfFilter] = useState('');
  const [protocolFilter, setProtocolFilter] = useState('ALL');
  const [expandedLayers, setExpandedLayers] = useState<Record<string, boolean>>({
    frame: true,
    ethernet: true,
    ipv4: true,
    tcp: true,
    udp: true,
  });

  const fetchPackets = async () => {
    try {
      const data = await packetService.getPackets();
      setPackets(data);
      if (data.length > 0 && !selectedPacket) {
        setSelectedPacket(data[0]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchPackets();
  }, []);

  const handleToggleCapture = async () => {
    if (!isCapturing) {
      setIsCapturing(true);
      addNotification('info', 'Capture Started', 'Sniffing packets on virtual interfaces...');
      await packetService.startCapture({ bpf_filter: bpfFilter });
    } else {
      setIsCapturing(false);
      addNotification('success', 'Capture Stopped', 'Flushed captured packet buffer.');
      await packetService.stopCapture();
      fetchPackets();
    }
  };

  const toggleLayer = (layer: string) => {
    setExpandedLayers((prev) => ({ ...prev, [layer]: !prev[layer] }));
  };

  const filteredPackets = packets.filter((p) => {
    const matchProto = protocolFilter === 'ALL' || p.protocol === protocolFilter;
    const matchFilter = !bpfFilter || p.info.toLowerCase().includes(bpfFilter.toLowerCase()) || p.src_ip.includes(bpfFilter);
    return matchProto && matchFilter;
  });

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-dark-border pb-4">
        <div>
          <h1 className="text-xl font-bold text-dark-heading tracking-tight">Packet Capture & Deep Dissection</h1>
          <p className="text-xs text-dark-muted mt-1">
            Wireshark-grade high-density packet capture table with Scapy L2-L7 protocol dissection.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" icon={<RefreshCw className="w-3.5 h-3.5" />} onClick={fetchPackets}>
            Refresh
          </Button>
          <Button
            variant={isCapturing ? 'danger' : 'primary'}
            size="sm"
            icon={isCapturing ? <Square className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            onClick={handleToggleCapture}
          >
            {isCapturing ? 'Stop Capture' : 'Start Capture'}
          </Button>
        </div>
      </div>

      {/* Capture Filters & Metrics */}
      <Card className="p-4">
        <div className="flex flex-col md:flex-row items-center gap-3">
          <div className="w-full md:w-80">
            <Input
              placeholder="BPF Filter (e.g. tcp port 80, udp, ip 10.10.1.2)..."
              value={bpfFilter}
              onChange={(e) => setBpfFilter(e.target.value)}
            />
          </div>
          <select
            value={protocolFilter}
            onChange={(e) => setProtocolFilter(e.target.value)}
            className="bg-dark-bg border border-dark-border rounded px-3 py-1.5 text-xs text-dark-text font-mono focus:outline-none focus:border-netpulse-blue"
          >
            <option value="ALL">Protocol: All</option>
            <option value="TCP">TCP</option>
            <option value="UDP">UDP</option>
            <option value="HTTP">HTTP</option>
          </select>

          <div className="flex items-center gap-4 ml-auto text-xs font-mono">
            <span className="text-dark-muted">
              Captured: <strong className="text-dark-heading">{packets.length}</strong>
            </span>
            <span className="text-dark-muted">
              Rate: <strong className="text-netpulse-blue">48.2 pkts/sec</strong>
            </span>
            <span className="text-dark-muted">
              Dropped: <strong className="text-netpulse-green">0 (0.0%)</strong>
            </span>
          </div>
        </div>
      </Card>

      {/* Packet Table & Inspector Split View */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Packet Stream Table (7 cols) */}
        <div className="lg:col-span-7">
          <Card title="Captured Packet Stream">
            <div className="overflow-x-auto -mx-5 -my-5 max-h-[520px] overflow-y-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-dark-header border-b border-dark-border text-dark-muted font-mono uppercase text-[11px] sticky top-0 z-10">
                  <tr>
                    <th className="px-3 py-2.5 font-medium">#</th>
                    <th className="px-3 py-2.5 font-medium">Time</th>
                    <th className="px-3 py-2.5 font-medium">Source</th>
                    <th className="px-3 py-2.5 font-medium">Destination</th>
                    <th className="px-3 py-2.5 font-medium">Proto</th>
                    <th className="px-3 py-2.5 font-medium">Len</th>
                    <th className="px-3 py-2.5 font-medium">Info</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dark-border">
                  {filteredPackets.map((pkt) => {
                    const isSelected = selectedPacket?.index === pkt.index;
                    return (
                      <tr
                        key={pkt.index}
                        onClick={() => setSelectedPacket(pkt)}
                        className={`cursor-pointer font-mono text-[11px] transition-colors ${
                          isSelected
                            ? 'bg-netpulse-blue/20 text-white font-medium'
                            : 'hover:bg-dark-hover/50 text-dark-text'
                        }`}
                      >
                        <td className="px-3 py-2">{pkt.index}</td>
                        <td className="px-3 py-2 text-dark-muted">{pkt.timestamp}</td>
                        <td className="px-3 py-2 text-netpulse-blue">{pkt.src_ip}</td>
                        <td className="px-3 py-2 text-netpulse-blue">{pkt.dst_ip}</td>
                        <td className="px-3 py-2">
                          <Badge
                            variant={
                              pkt.protocol === 'TCP'
                                ? 'info'
                                : pkt.protocol === 'UDP'
                                ? 'purple'
                                : pkt.protocol === 'HTTP'
                                ? 'success'
                                : 'default'
                            }
                            size="sm"
                          >
                            {pkt.protocol}
                          </Badge>
                        </td>
                        <td className="px-3 py-2 text-dark-muted">{pkt.length_bytes}</td>
                        <td className="px-3 py-2 text-dark-heading truncate max-w-[200px]" title={pkt.info}>
                          {pkt.info}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* Deep Packet Inspector (5 cols) */}
        <div className="lg:col-span-5">
          <Card
            title={selectedPacket ? `Packet #${selectedPacket.index} Inspector` : 'Packet Inspector'}
            subtitle="Hierarchical L2-L7 Protocol Header Dissection"
          >
            {selectedPacket ? (
              <div className="space-y-3 font-mono text-xs max-h-[480px] overflow-y-auto">
                {/* Frame Layer */}
                <div className="border border-dark-border rounded-md overflow-hidden">
                  <button
                    onClick={() => toggleLayer('frame')}
                    className="w-full flex items-center justify-between px-3 py-2 bg-dark-bg font-bold text-dark-heading hover:bg-dark-hover"
                  >
                    <span className="flex items-center gap-2">
                      {expandedLayers.frame ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                      Frame ({selectedPacket.length_bytes} bytes on wire)
                    </span>
                  </button>
                  {expandedLayers.frame && (
                    <div className="p-3 bg-dark-card space-y-1 text-[11px] text-dark-text border-t border-dark-border">
                      <div>Arrival Time: {selectedPacket.timestamp}</div>
                      <div>Frame Length: {selectedPacket.length_bytes} bytes</div>
                    </div>
                  )}
                </div>

                {/* Ethernet Layer */}
                <div className="border border-dark-border rounded-md overflow-hidden">
                  <button
                    onClick={() => toggleLayer('ethernet')}
                    className="w-full flex items-center justify-between px-3 py-2 bg-dark-bg font-bold text-dark-heading hover:bg-dark-hover"
                  >
                    <span className="flex items-center gap-2">
                      {expandedLayers.ethernet ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                      Ethernet II (L2)
                    </span>
                  </button>
                  {expandedLayers.ethernet && (
                    <div className="p-3 bg-dark-card space-y-1 text-[11px] text-dark-text border-t border-dark-border">
                      <div>Source MAC: {selectedPacket.layers?.ethernet?.src_mac || '02:42:0a:0a:01:02'}</div>
                      <div>Destination MAC: {selectedPacket.layers?.ethernet?.dst_mac || '02:42:0a:0a:01:01'}</div>
                      <div>Type: IPv4 (0x0800)</div>
                    </div>
                  )}
                </div>

                {/* IPv4 Layer */}
                <div className="border border-dark-border rounded-md overflow-hidden">
                  <button
                    onClick={() => toggleLayer('ipv4')}
                    className="w-full flex items-center justify-between px-3 py-2 bg-dark-bg font-bold text-dark-heading hover:bg-dark-hover"
                  >
                    <span className="flex items-center gap-2">
                      {expandedLayers.ipv4 ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                      Internet Protocol Version 4 (L3)
                    </span>
                  </button>
                  {expandedLayers.ipv4 && (
                    <div className="p-3 bg-dark-card space-y-1 text-[11px] text-dark-text border-t border-dark-border">
                      <div>Source IP: <span className="text-netpulse-blue">{selectedPacket.src_ip}</span></div>
                      <div>Destination IP: <span className="text-netpulse-blue">{selectedPacket.dst_ip}</span></div>
                      <div>Time to Live (TTL): {selectedPacket.layers?.ipv4?.ttl || 64}</div>
                      <div>Protocol: {selectedPacket.protocol}</div>
                    </div>
                  )}
                </div>

                {/* TCP / UDP Layer */}
                {selectedPacket.protocol === 'TCP' && (
                  <div className="border border-dark-border rounded-md overflow-hidden">
                    <button
                      onClick={() => toggleLayer('tcp')}
                      className="w-full flex items-center justify-between px-3 py-2 bg-dark-bg font-bold text-dark-heading hover:bg-dark-hover"
                    >
                      <span className="flex items-center gap-2">
                        {expandedLayers.tcp ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                        Transmission Control Protocol (L4)
                      </span>
                    </button>
                    {expandedLayers.tcp && (
                      <div className="p-3 bg-dark-card space-y-1 text-[11px] text-dark-text border-t border-dark-border">
                        <div>Source Port: {selectedPacket.sport || 5000}</div>
                        <div>Destination Port: {selectedPacket.dport || 80}</div>
                        <div>Sequence Number: {selectedPacket.seq || 1000}</div>
                        <div>Acknowledgment Number: {selectedPacket.ack || 0}</div>
                        <div>Flags: {selectedPacket.flags?.join(', ') || 'SYN'}</div>
                      </div>
                    )}
                  </div>
                )}

                {selectedPacket.protocol === 'UDP' && (
                  <div className="border border-dark-border rounded-md overflow-hidden">
                    <button
                      onClick={() => toggleLayer('udp')}
                      className="w-full flex items-center justify-between px-3 py-2 bg-dark-bg font-bold text-dark-heading hover:bg-dark-hover"
                    >
                      <span className="flex items-center gap-2">
                        {expandedLayers.udp ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                        User Datagram Protocol (L4)
                      </span>
                    </button>
                    {expandedLayers.udp && (
                      <div className="p-3 bg-dark-card space-y-1 text-[11px] text-dark-text border-t border-dark-border">
                        <div>Source Port: {selectedPacket.sport || 51037}</div>
                        <div>Destination Port: {selectedPacket.dport || 51037}</div>
                        <div>Sequence Header: {selectedPacket.layers?.udp?.sequence || 42}</div>
                        <div>Send Monotonic Time: {selectedPacket.layers?.udp?.send_time_ns || 1724869510000000000} ns</div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-12 text-xs text-dark-muted">Select a packet from the table to inspect headers.</div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};
