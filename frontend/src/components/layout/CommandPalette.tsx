import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  LayoutDashboard,
  PlayCircle,
  Activity,
  Network,
  Radio,
  FileCode2,
  GitCompare,
  Sliders,
  FileBarChart,
  Settings,
  Zap,
} from 'lucide-react';
import { useAppStore } from '../../stores/useAppStore';
import { testService } from '../../services/testService';

export const CommandPalette: React.FC = () => {
  const { isCommandPaletteOpen, setCommandPaletteOpen, addNotification, mockMode, setMockMode } =
    useAppStore();
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(!isCommandPaletteOpen);
      }
      if (e.key === 'Escape' && isCommandPaletteOpen) {
        setCommandPaletteOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isCommandPaletteOpen, setCommandPaletteOpen]);

  if (!isCommandPaletteOpen) return null;

  const actions = [
    {
      id: 'dash',
      title: 'Go to Dashboard',
      category: 'Navigation',
      icon: LayoutDashboard,
      run: () => navigate('/dashboard'),
    },
    {
      id: 'runs',
      title: 'View Test Runs',
      category: 'Navigation',
      icon: PlayCircle,
      run: () => navigate('/test-runs'),
    },
    {
      id: 'perf',
      title: 'Open Performance Lab',
      category: 'Navigation',
      icon: Activity,
      run: () => navigate('/performance'),
    },
    {
      id: 'topo',
      title: 'View Network Topology',
      category: 'Navigation',
      icon: Network,
      run: () => navigate('/topology'),
    },
    {
      id: 'pcap',
      title: 'Inspect Packet Capture',
      category: 'Navigation',
      icon: Radio,
      run: () => navigate('/packet-capture'),
    },
    {
      id: 'cases',
      title: 'Browse Test Case Catalog',
      category: 'Navigation',
      icon: FileCode2,
      run: () => navigate('/test-cases'),
    },
    {
      id: 'reg',
      title: 'View Regression Intelligence',
      category: 'Navigation',
      icon: GitCompare,
      run: () => navigate('/regression'),
    },
    {
      id: 'fault',
      title: 'Open Fault Injection Lab',
      category: 'Navigation',
      icon: Sliders,
      run: () => navigate('/fault-lab'),
    },
    {
      id: 'reports',
      title: 'Explore Reports & Matrix',
      category: 'Navigation',
      icon: FileBarChart,
      run: () => navigate('/reports'),
    },
    {
      id: 'settings',
      title: 'System Settings',
      category: 'Navigation',
      icon: Settings,
      run: () => navigate('/settings'),
    },
    {
      id: 'run-func',
      title: 'Action: Run Functional Protocol Tests',
      category: 'Quick Actions',
      icon: Zap,
      run: async () => {
        addNotification('info', 'Test Suite Queued', 'Triggering functional tests suite...');
        await testService.triggerRun('functional');
        navigate('/test-runs');
      },
    },
    {
      id: 'run-reg',
      title: 'Action: Run Full Regression Suite',
      category: 'Quick Actions',
      icon: Zap,
      run: async () => {
        addNotification('info', 'Regression Queued', 'Triggering regression tests...');
        await testService.triggerRun('regression');
        navigate('/regression');
      },
    },
    {
      id: 'toggle-mock',
      title: `Toggle Demo / Mock Mode (${mockMode ? 'Active' : 'Disabled'})`,
      category: 'Developer',
      icon: Zap,
      run: () => {
        setMockMode(!mockMode);
        addNotification('info', 'Mock Mode Toggled', `Demo data mode is now ${!mockMode ? 'ON' : 'OFF'}`);
      },
    },
  ];

  const filtered = actions.filter(
    (a) =>
      a.title.toLowerCase().includes(query.toLowerCase()) ||
      a.category.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="w-full max-w-xl bg-dark-card border border-dark-border rounded-xl shadow-2xl overflow-hidden flex flex-col">
        <div className="flex items-center px-4 py-3.5 border-b border-dark-border bg-dark-header">
          <Search className="w-4 h-4 text-dark-muted mr-3" />
          <input
            type="text"
            placeholder="Search commands, tests, runs, or navigation..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
            className="bg-transparent text-dark-heading text-sm placeholder-dark-muted/60 focus:outline-none w-full font-mono"
          />
          <kbd className="text-[10px] font-mono bg-dark-bg border border-dark-border px-1.5 py-0.5 rounded text-dark-muted">
            ESC
          </kbd>
        </div>

        <div className="max-h-80 overflow-y-auto p-2 divide-y divide-dark-border/40">
          {filtered.length === 0 ? (
            <div className="p-4 text-center text-xs text-dark-muted">No matching commands found.</div>
          ) : (
            filtered.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    item.run();
                    setCommandPaletteOpen(false);
                  }}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-md hover:bg-dark-hover transition-colors text-left group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded bg-dark-bg border border-dark-border flex items-center justify-center text-dark-muted group-hover:text-netpulse-blue">
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <span className="text-xs font-medium text-dark-heading">{item.title}</span>
                  </div>
                  <span className="text-[10px] font-mono text-dark-muted uppercase bg-dark-bg px-2 py-0.5 rounded border border-dark-border">
                    {item.category}
                  </span>
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
