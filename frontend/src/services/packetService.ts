import { PacketSummary } from '../types';
import { mockPackets } from '../mock/mockData';
import { apiRequest, isMockMode } from './apiClient';

export const packetService = {
  async getPackets(): Promise<PacketSummary[]> {
    if (isMockMode()) return mockPackets;
    try {
      const data = await apiRequest<PacketSummary[]>('/packets');
      return data.length > 0 ? data : mockPackets;
    } catch {
      return mockPackets;
    }
  },

  async startCapture(params: {
    interface?: string;
    bpf_filter?: string;
    packet_limit?: number;
    timeout?: number;
  }): Promise<{ status: string }> {
    if (isMockMode()) return { status: 'started' };
    return await apiRequest<{ status: string }>('/capture/start', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  async stopCapture(): Promise<{ status: string; packets_captured: number }> {
    if (isMockMode()) return { status: 'stopped', packets_captured: mockPackets.length };
    return await apiRequest<{ status: string; packets_captured: number }>('/capture/stop', { method: 'POST' });
  },
};
