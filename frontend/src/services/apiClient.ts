/**
 * NetPulse Typed HTTP API Client
 */

let inMemoryMockMode = false;
let inMemoryApiUrl = '/api';

export const isMockMode = (): boolean => {
  if (typeof window !== 'undefined' && window.localStorage) {
    return (
      import.meta.env.VITE_USE_MOCK_API === 'true' ||
      window.localStorage.getItem('netpulse_mock_mode') === 'true'
    );
  }
  return inMemoryMockMode || import.meta.env.VITE_USE_MOCK_API === 'true';
};

export const setMockMode = (enabled: boolean) => {
  inMemoryMockMode = enabled;
  if (typeof window !== 'undefined' && window.localStorage) {
    window.localStorage.setItem('netpulse_mock_mode', enabled ? 'true' : 'false');
  }
};

export const getApiBaseUrl = (): string => {
  if (typeof window !== 'undefined' && window.localStorage) {
    return window.localStorage.getItem('netpulse_api_url') || '/api';
  }
  return inMemoryApiUrl;
};

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${endpoint}`;

  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  try {
    const response = await fetch(url, { ...options, headers });
    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(errorBody.detail || `HTTP Error ${response.status}: ${response.statusText}`);
    }
    return (await response.json()) as T;
  } catch (err: any) {
    console.warn(`[NetPulse API] Request to ${endpoint} failed:`, err.message);
    throw err;
  }
}
