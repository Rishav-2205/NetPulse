import React, { useState } from 'react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { useAppStore } from '../../stores/useAppStore';

export const SettingsPage: React.FC = () => {
  const { mockMode, setMockMode, health, backendConnected, addNotification } = useAppStore();

  const [apiUrl, setApiUrl] = useState(localStorage.getItem('netpulse_api_url') || '/api');
  const [logLevel, setLogLevel] = useState('INFO');
  const [pollInterval, setPollInterval] = useState('5');

  const handleSaveApiUrl = () => {
    localStorage.setItem('netpulse_api_url', apiUrl);
    addNotification('success', 'Settings Saved', `API Base URL updated to ${apiUrl}`);
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-dark-border pb-4">
        <div>
          <h1 className="text-xl font-bold text-dark-heading tracking-tight">System Settings & Configuration</h1>
          <p className="text-xs text-dark-muted mt-1">
            Configure backend connection endpoints, mock demo modes, telemetry preferences, and kernel capabilities.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Backend Endpoint Settings */}
        <Card title="Backend API Connection" subtitle="Configure REST and WebSocket server endpoints">
          <div className="space-y-4">
            <Input
              label="REST API Base URL"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              helperText="Default: /api (proxied to http://127.0.0.1:8000)"
            />
            <div className="flex justify-end">
              <Button variant="primary" size="sm" onClick={handleSaveApiUrl}>
                Save URL
              </Button>
            </div>

            <div className="pt-4 border-t border-dark-border flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-dark-heading block">Offline Demo / Mock Mode</span>
                <span className="text-[11px] text-dark-muted">
                  Use built-in realistic mock data if backend server is not reachable
                </span>
              </div>
              <Button
                variant={mockMode ? 'primary' : 'outline'}
                size="sm"
                onClick={() => {
                  setMockMode(!mockMode);
                  addNotification('info', 'Mode Switched', `Demo Mode is now ${!mockMode ? 'Active' : 'Disabled'}`);
                }}
              >
                {mockMode ? 'DEMO MODE ON' : 'DISABLED'}
              </Button>
            </div>
          </div>
        </Card>

        {/* Kernel Capabilities & Runtime */}
        <Card title="Kernel Capabilities & Runtime" subtitle="Authoritative environment capability inspection">
          <div className="space-y-3 font-mono text-xs">
            <div className="flex justify-between items-center p-2.5 bg-dark-bg rounded border border-dark-border">
              <span className="text-dark-muted">Operating System:</span>
              <span className="text-dark-heading font-bold">{health?.os || 'Windows/Linux x86_64'}</span>
            </div>
            <div className="flex justify-between items-center p-2.5 bg-dark-bg rounded border border-dark-border">
              <span className="text-dark-muted">Python Version:</span>
              <span className="text-dark-heading font-bold">Python {health?.python_version || '3.12.3'}</span>
            </div>
            <div className="flex justify-between items-center p-2.5 bg-dark-bg rounded border border-dark-border">
              <span className="text-dark-muted">CAP_NET_ADMIN (Namespaces/tc):</span>
              <Badge variant={health?.capabilities?.cap_net_admin ? 'success' : 'warning'}>
                {health?.capabilities?.cap_net_admin ? 'AVAILABLE' : 'UNPRIVILEGED'}
              </Badge>
            </div>
            <div className="flex justify-between items-center p-2.5 bg-dark-bg rounded border border-dark-border">
              <span className="text-dark-muted">CAP_NET_RAW (Promiscuous Sniffing):</span>
              <Badge variant={health?.capabilities?.cap_net_raw ? 'success' : 'outline'}>
                {health?.capabilities?.cap_net_raw ? 'AVAILABLE' : 'SIMULATED'}
              </Badge>
            </div>
          </div>
        </Card>

        {/* Telemetry & UI Preferences */}
        <Card title="Observability Preferences" subtitle="Telemetry polling frequency and logging verbosity">
          <div className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-dark-muted uppercase tracking-wider block mb-1.5">
                Telemetry Polling Interval
              </label>
              <select
                value={pollInterval}
                onChange={(e) => setPollInterval(e.target.value)}
                className="w-full bg-dark-bg border border-dark-border rounded px-3 py-1.5 text-xs text-dark-text font-mono focus:outline-none focus:border-netpulse-blue"
              >
                <option value="2">2 seconds (High Frequency)</option>
                <option value="5">5 seconds (Standard)</option>
                <option value="15">15 seconds (Low Overhead)</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-dark-muted uppercase tracking-wider block mb-1.5">
                Log Verbosity Level
              </label>
              <select
                value={logLevel}
                onChange={(e) => setLogLevel(e.target.value)}
                className="w-full bg-dark-bg border border-dark-border rounded px-3 py-1.5 text-xs text-dark-text font-mono focus:outline-none focus:border-netpulse-blue"
              >
                <option value="DEBUG">DEBUG (Detailed tracing)</option>
                <option value="INFO">INFO (Production standard)</option>
                <option value="WARNING">WARNING (Anomalies only)</option>
                <option value="ERROR">ERROR (Failures only)</option>
              </select>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};
