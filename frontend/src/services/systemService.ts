import { SystemHealth } from '../types';
import { mockHealth } from '../mock/mockData';
import { apiRequest, isMockMode } from './apiClient';

export const systemService = {
  async getHealth(): Promise<SystemHealth> {
    if (isMockMode()) return mockHealth;
    try {
      return await apiRequest<SystemHealth>('/health');
    } catch {
      return mockHealth;
    }
  },
};
