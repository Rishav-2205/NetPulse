import { BenchmarkMetrics } from '../types';
import { mockBenchmarkHistory } from '../mock/mockData';
import { apiRequest, isMockMode } from './apiClient';

export const performanceService = {
  async getBenchmarkHistory(): Promise<BenchmarkMetrics[]> {
    if (isMockMode()) return mockBenchmarkHistory;
    try {
      const history = await apiRequest<BenchmarkMetrics[]>('/benchmarks/history');
      return history.length > 0 ? history : mockBenchmarkHistory;
    } catch {
      return mockBenchmarkHistory;
    }
  },

  async triggerBenchmark(params: {
    profile: string;
    protocol: string;
    concurrency: number;
    packet_size: number;
    duration: number;
  }): Promise<{ benchmark_id: string; status: string }> {
    if (isMockMode()) {
      return { benchmark_id: `BM-${Date.now().toString().slice(-4)}`, status: 'RUNNING' };
    }
    return await apiRequest<{ benchmark_id: string; status: string }>('/benchmarks', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },
};
