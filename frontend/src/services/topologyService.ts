import { TopologyState } from '../types';
import { mockTopology } from '../mock/mockData';
import { apiRequest, isMockMode } from './apiClient';

export const topologyService = {
  async getTopology(): Promise<TopologyState> {
    if (isMockMode()) return mockTopology;
    try {
      const data = await apiRequest<TopologyState>('/topology');
      return data.nodes && data.nodes.length > 0 ? data : mockTopology;
    } catch {
      return mockTopology;
    }
  },

  async createTopology(): Promise<{ success: boolean; status: string }> {
    if (isMockMode()) return { success: true, status: 'active' };
    return await apiRequest<{ success: boolean; status: string }>('/topology/create', { method: 'POST' });
  },

  async destroyTopology(): Promise<{ success: boolean; status: string }> {
    if (isMockMode()) return { success: true, status: 'destroyed' };
    return await apiRequest<{ success: boolean; status: string }>('/topology/destroy', { method: 'POST' });
  },

  async cleanupTopology(): Promise<{ cleaned_count: number }> {
    if (isMockMode()) return { cleaned_count: 3 };
    return await apiRequest<{ cleaned_count: number }>('/topology/cleanup', { method: 'POST' });
  },
};
