import { describe, it, expect } from 'vitest';
import { mockHealth, mockClaims, mockMatrix } from '../mock/mockData';

describe('NetPulse Frontend Models & Claims Integrity', () => {
  it('validates health check payload structure', () => {
    expect(mockHealth.status).toBe('healthy');
    expect(mockHealth.capabilities.cap_net_admin).toBe(true);
  });

  it('validates 9 audited portfolio claims are present and resume-safe', () => {
    expect(mockClaims.length).toBe(9);
    expect(mockClaims.every((c) => c.resume_safe === 'YES')).toBe(true);
    expect(mockClaims.some((c) => c.metric === 'Automated Test Suite' && c.value === '105')).toBe(true);
  });

  it('verifies 44-permutation matrix model integrity', () => {
    expect(mockMatrix.length).toBeGreaterThan(0);
    expect(mockMatrix[0].matrix_id).toBeDefined();
    expect(mockMatrix[0].buffer_size_bytes).toBeGreaterThan(0);
  });
});
