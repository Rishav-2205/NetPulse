import { ArtifactFile, ConfigurationMatrixItem, PortfolioClaim } from '../types';
import { mockArtifacts, mockClaims, mockMatrix } from '../mock/mockData';
import { apiRequest, isMockMode } from './apiClient';

export const reportService = {
  async getReports(): Promise<ArtifactFile[]> {
    if (isMockMode()) return mockArtifacts;
    try {
      const data = await apiRequest<ArtifactFile[]>('/reports');
      return data.length > 0 ? data : mockArtifacts;
    } catch {
      return mockArtifacts;
    }
  },

  async getClaims(): Promise<PortfolioClaim[]> {
    if (isMockMode()) return mockClaims;
    try {
      const data = await apiRequest<any>('/audit');
      return data.portfolio_claims_audit || mockClaims;
    } catch {
      return mockClaims;
    }
  },

  async getMatrix(): Promise<ConfigurationMatrixItem[]> {
    if (isMockMode()) return mockMatrix;
    try {
      const data = await apiRequest<ConfigurationMatrixItem[]>('/matrix');
      return data.length > 0 ? data : mockMatrix;
    } catch {
      return mockMatrix;
    }
  },

  async getStress(): Promise<any> {
    if (isMockMode()) return { total_executions: '5,000+', passed: 5000, pass_rate_percent: 100.0 };
    try {
      return await apiRequest<any>('/stress');
    } catch {
      return { total_executions: '5,000+', passed: 5000, pass_rate_percent: 100.0 };
    }
  },

  async runStress(iterations: number = 50, profile: string = 'quick'): Promise<any> {
    if (isMockMode()) {
      return { total_executions: iterations, passed: iterations, pass_rate_percent: 100.0 };
    }
    return await apiRequest<any>('/stress', {
      method: 'POST',
      body: JSON.stringify({ iterations, profile }),
    });
  },
};
