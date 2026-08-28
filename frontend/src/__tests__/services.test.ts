import { describe, it, expect } from 'vitest';
import { testService } from '../services/testService';
import { faultService } from '../services/faultService';
import { topologyService } from '../services/topologyService';
import { setMockMode } from '../services/apiClient';

describe('NetPulse Frontend Services (Mock & Fallback Engine)', () => {
  setMockMode(true);

  it('retrieves test cases catalog with proper schema', async () => {
    const cases = await testService.getTestCases();
    expect(cases).toBeDefined();
    expect(cases.length).toBeGreaterThan(0);
    expect(cases[0].test_id).toBeDefined();
    expect(cases[0].protocol).toBeDefined();
  });

  it('retrieves test runs history with metrics', async () => {
    const runs = await testService.getTestRuns();
    expect(runs).toBeDefined();
    expect(runs.length).toBeGreaterThan(0);
    expect(runs[0].status).toBe('PASS');
  });

  it('loads fault injection presets', async () => {
    const profiles = await faultService.getProfiles();
    expect(profiles.length).toBeGreaterThan(0);
    expect(profiles.some((p) => p.name === 'lossy')).toBe(true);
  });

  it('loads 3-node routed virtual topology', async () => {
    const topo = await topologyService.getTopology();
    expect(topo.nodes.length).toBe(3);
    expect(topo.links.length).toBe(2);
    expect(topo.nodes.some((n) => n.id === 'netpulse-router')).toBe(true);
  });
});
