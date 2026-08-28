import { RegressionReport } from '../types';
import { mockRegressionReport } from '../mock/mockData';
import { apiRequest, isMockMode } from './apiClient';

export const regressionService = {
  async getRegression(): Promise<RegressionReport> {
    if (isMockMode()) return mockRegressionReport;
    try {
      const data = await apiRequest<RegressionReport>('/regression');
      return data.status ? data : mockRegressionReport;
    } catch {
      return mockRegressionReport;
    }
  },

  async getBaselines(): Promise<any[]> {
    if (isMockMode()) return [{ timestamp: '2026-08-28T18:00:00Z', profile: 'standard', git_commit: '7e9c34a' }];
    try {
      return await apiRequest<any[]>('/baselines');
    } catch {
      return [{ timestamp: '2026-08-28T18:00:00Z', profile: 'standard', git_commit: '7e9c34a' }];
    }
  },

  async createBaseline(): Promise<{ status: string }> {
    if (isMockMode()) return { status: 'created' };
    return await apiRequest<{ status: string }>('/baselines', { method: 'POST' });
  },
};
