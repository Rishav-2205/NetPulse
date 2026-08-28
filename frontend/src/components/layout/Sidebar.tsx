import React from 'react';
import { NavLink } from 'react-router-dom';
import {
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
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { useAppStore } from '../../stores/useAppStore';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ collapsed, onToggle }) => {
  const { backendConnected, activeFault } = useAppStore();

  const navItems = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/test-runs', label: 'Test Runs', icon: PlayCircle },
    { to: '/performance', label: 'Performance Lab', icon: Activity },
    { to: '/topology', label: 'Topology', icon: Network },
    { to: '/packet-capture', label: 'Packet Capture', icon: Radio },
    { to: '/test-cases', label: 'Test Cases', icon: FileCode2 },
    { to: '/regression', label: 'Regression & Baseline', icon: GitCompare },
    { to: '/fault-lab', label: 'Fault Injection Lab', icon: Sliders },
    { to: '/reports', label: 'Reports & Matrix', icon: FileBarChart },
    { to: '/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside
      className={`bg-dark-header border-r border-dark-border flex flex-col transition-all duration-300 select-none z-30 ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="h-14 px-4 flex items-center justify-between border-b border-dark-border">
        {!collapsed && (
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded bg-netpulse-blue/20 border border-netpulse-blue/40 flex items-center justify-center text-netpulse-blue">
              <Zap className="w-4 h-4" />
            </div>
            <div>
              <span className="font-bold text-sm text-dark-heading tracking-tight">NetPulse</span>
              <span className="text-[10px] text-dark-muted font-mono block -mt-0.5">LAB v1.0</span>
            </div>
          </div>
        )}
        {collapsed && (
          <div className="w-full flex justify-center">
            <div className="w-7 h-7 rounded bg-netpulse-blue/20 border border-netpulse-blue/40 flex items-center justify-center text-netpulse-blue">
              <Zap className="w-4 h-4" />
            </div>
          </div>
        )}
        <button
          onClick={onToggle}
          className="text-dark-muted hover:text-dark-heading p-1 rounded hover:bg-dark-hover transition-colors"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-2.5 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded text-xs font-medium transition-colors ${
                  isActive
                    ? 'bg-netpulse-blue/15 text-netpulse-blue border border-netpulse-blue/30 font-semibold'
                    : 'text-dark-text hover:bg-dark-hover hover:text-dark-heading'
                } ${collapsed ? 'justify-center px-0' : ''}`
              }
              title={collapsed ? item.label : undefined}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          );
        })}
      </nav>

      {/* Active Fault / System Health Footnote */}
      <div className="p-3 border-t border-dark-border bg-dark-bg/60">
        {!collapsed ? (
          <div className="space-y-2">
            {activeFault && (
              <div className="bg-netpulse-yellow/10 border border-netpulse-yellow/30 rounded p-2 text-[11px] text-netpulse-yellow flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-netpulse-yellow animate-pulse" />
                <span className="font-mono truncate">Fault: +{activeFault.latency_ms}ms / {activeFault.packet_loss_percent}%</span>
              </div>
            )}
            <div className="flex items-center justify-between text-[11px] text-dark-muted">
              <span className="flex items-center gap-1.5 font-mono">
                <span
                  className={`w-2 h-2 rounded-full ${
                    backendConnected ? 'bg-netpulse-green' : 'bg-netpulse-red'
                  }`}
                />
                {backendConnected ? 'SYSTEM ONLINE' : 'API DISCONNECTED'}
              </span>
              <ShieldCheck className="w-3.5 h-3.5 text-dark-muted" />
            </div>
          </div>
        ) : (
          <div className="flex justify-center">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                backendConnected ? 'bg-netpulse-green' : 'bg-netpulse-red'
              }`}
              title={backendConnected ? 'Backend Connected' : 'API Disconnected'}
            />
          </div>
        )}
      </div>
    </aside>
  );
};
