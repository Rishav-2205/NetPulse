import { TestCase, TestRun } from '../types';
import { mockTestCases, mockTestRuns } from '../mock/mockData';
import { apiRequest, isMockMode } from './apiClient';

export const testService = {
  async getTestCases(): Promise<TestCase[]> {
    if (isMockMode()) return mockTestCases;
    try {
      return await apiRequest<TestCase[]>('/tests');
    } catch {
      return mockTestCases;
    }
  },

  async getTestRuns(): Promise<TestRun[]> {
    if (isMockMode()) return mockTestRuns;
    try {
      const runs = await apiRequest<TestRun[]>('/runs');
      return runs.length > 0 ? runs : mockTestRuns;
    } catch {
      return mockTestRuns;
    }
  },

  async getTestRunById(runId: string): Promise<TestRun | null> {
    if (isMockMode()) {
      return mockTestRuns.find((r) => r.run_id === runId || r.test_id === runId) || mockTestRuns[0];
    }
    try {
      return await apiRequest<TestRun>(`/runs/${runId}`);
    } catch {
      return mockTestRuns.find((r) => r.run_id === runId || r.test_id === runId) || mockTestRuns[0];
    }
  },

  async triggerRun(suite: string = 'functional', marker?: string): Promise<{ run_id: string; status: string }> {
    if (isMockMode()) {
      return { run_id: `TR-${Date.now().toString().slice(-4)}`, status: 'QUEUED' };
    }
    return await apiRequest<{ run_id: string; status: string }>('/runs', {
      method: 'POST',
      body: JSON.stringify({ suite, marker }),
    });
  },
};
