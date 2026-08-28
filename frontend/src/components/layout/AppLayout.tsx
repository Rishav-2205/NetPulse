import React, { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { CommandPalette } from './CommandPalette';
import { useAppStore } from '../../stores/useAppStore';
import { systemService } from '../../services/systemService';

export const AppLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const { setHealth, setBackendConnected, setActiveFault } = useAppStore();

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const health = await systemService.getHealth();
        setHealth(health);
        setBackendConnected(true);
        setActiveFault(health.active_fault || null);
      } catch (e) {
        setBackendConnected(false);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 5000);
    return () => clearInterval(interval);
  }, [setHealth, setBackendConnected, setActiveFault]);

  return (
    <div className="flex h-screen w-screen bg-dark-bg text-dark-text overflow-hidden font-sans">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopBar />

        <main className="flex-1 overflow-y-auto p-6 bg-dark-bg">
          <div className="max-w-7xl mx-auto space-y-6">
            <Outlet />
          </div>
        </main>
      </div>

      <CommandPalette />
    </div>
  );
};
