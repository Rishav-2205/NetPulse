import { ExperimentResult } from '../types';
import { mockExperiments } from '../mock/mockData';
import { apiRequest, isMockMode } from './apiClient';

export const experimentService = {
  async getExperiments(): Promise<ExperimentResult[]> {
    if (isMockMode()) return mockExperiments;
    try {
      const data = await apiRequest<ExperimentResult[]>('/experiments');
      return data.length > 0 ? data : mockExperiments;
    } catch {
      return mockExperiments;
    }
  },

  async runExperiment(params: {
    profile: string;
    packet_count: number;
    packet_size: number;
  }): Promise<ExperimentResult> {
    if (isMockMode()) {
      return {
        ...mockExperiments[0],
        experiment_id: `EXP-${Date.now().toString(16).slice(-8).toUpperCase()}`,
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
      };
    }
    return await apiRequest<ExperimentResult>('/experiments/run', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },
};
