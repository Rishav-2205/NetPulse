import { FaultConfig, FaultProfile } from '../types';
import { mockFaultProfiles } from '../mock/mockData';
import { apiRequest, isMockMode } from './apiClient';

export const faultService = {
  async getProfiles(): Promise<FaultProfile[]> {
    if (isMockMode()) return mockFaultProfiles;
    try {
      const data = await apiRequest<FaultProfile[]>('/faults/profiles');
      return data.length > 0 ? data : mockFaultProfiles;
    } catch {
      return mockFaultProfiles;
    }
  },

  async applyFault(params: {
    profile?: string;
    latency_ms?: number;
    jitter_ms?: number;
    packet_loss_percent?: number;
    bandwidth_mbps?: number | null;
    interface?: string;
    namespace?: string;
  }): Promise<{ status: string; config: FaultConfig }> {
    if (isMockMode()) {
      return {
        status: 'applied',
        config: {
          latency_ms: params.latency_ms || 20,
          jitter_ms: params.jitter_ms || 5,
          packet_loss_percent: params.packet_loss_percent || 2,
          bandwidth_mbps: params.bandwidth_mbps || 50,
          description: 'Simulated Fault',
        },
      };
    }
    return await apiRequest<{ status: string; config: FaultConfig }>('/faults/apply', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  async clearFault(): Promise<{ status: string }> {
    if (isMockMode()) return { status: 'cleared' };
    return await apiRequest<{ status: string }>('/faults/clear', { method: 'POST' });
  },
};
