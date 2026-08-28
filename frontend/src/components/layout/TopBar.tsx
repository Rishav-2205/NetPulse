import React, { useState } from 'react';
import {
  Search,
  Bell,
  GitBranch,
  Terminal,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Info,
} from 'lucide-react';
import { useAppStore } from '../../stores/useAppStore';

export const TopBar: React.FC = () => {
  const {
    mockMode,
    backendConnected,
    health,
    toggleCommandPalette,
    notifications,
    removeNotification,
    clearNotifications,
  } = useAppStore();

  const [showNotifications, setShowNotifications] = useState(false);

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <CheckCircle2 className="w-3.5 h-3.5 text-netpulse-green" />;
      case 'warning':
        return <AlertTriangle className="w-3.5 h-3.5 text-netpulse-yellow" />;
      case 'error':
        return <XCircle className="w-3.5 h-3.5 text-netpulse-red" />;
      default:
        return <Info className="w-3.5 h-3.5 text-netpulse-blue" />;
    }
  };

  return (
    <header className="h-14 bg-dark-header border-b border-dark-border px-6 flex items-center justify-between z-20">
      {/* Search / Command Palette Shortcut */}
      <div className="flex items-center gap-4">
        <button
          onClick={toggleCommandPalette}
          className="flex items-center gap-2.5 bg-dark-bg hover:bg-dark-card border border-dark-border rounded px-3 py-1.5 text-xs text-dark-muted transition-colors w-64 text-left"
        >
          <Search className="w-3.5 h-3.5 text-dark-muted" />
          <span>Search or type command...</span>
          <kbd className="ml-auto text-[10px] font-mono bg-dark-card border border-dark-border px-1.5 py-0.5 rounded text-dark-text">
            Ctrl+K
          </kbd>
        </button>

        {mockMode && (
          <span className="bg-netpulse-yellow/20 text-netpulse-yellow border border-netpulse-yellow/40 text-[10px] font-mono px-2 py-0.5 rounded font-semibold uppercase animate-pulse">
            DEMO DATA MODE
          </span>
        )}
      </div>

      {/* Right Environment & Status Metrics */}
      <div className="flex items-center gap-3">
        {/* Environment Pill */}
        <div className="flex items-center gap-1.5 bg-dark-bg border border-dark-border px-2.5 py-1 rounded text-xs font-mono text-dark-text">
          <Terminal className="w-3.5 h-3.5 text-netpulse-blue" />
          <span>{health?.environment || 'lab-env'}</span>
        </div>

        {/* Git Commit Hash */}
        <div className="flex items-center gap-1.5 bg-dark-bg border border-dark-border px-2.5 py-1 rounded text-xs font-mono text-dark-muted">
          <GitBranch className="w-3.5 h-3.5 text-dark-muted" />
          <span>{health?.git_commit || 'latest'}</span>
        </div>

        {/* Backend Online Status Pill */}
        <div
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded border text-xs font-mono ${
            backendConnected
              ? 'bg-netpulse-green/15 text-netpulse-green border-netpulse-green/30'
              : 'bg-netpulse-red/15 text-netpulse-red border-netpulse-red/30'
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full ${
              backendConnected ? 'bg-netpulse-green' : 'bg-netpulse-red animate-ping'
            }`}
          />
          <span>{backendConnected ? 'API CONNECTED' : 'OFFLINE'}</span>
        </div>

        {/* Notifications Center */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2 rounded text-dark-muted hover:text-dark-heading hover:bg-dark-hover transition-colors"
            title="Notifications"
          >
            <Bell className="w-4 h-4" />
            {notifications.length > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-netpulse-blue rounded-full" />
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 bg-dark-card border border-dark-border rounded-lg shadow-2xl overflow-hidden z-50">
              <div className="flex items-center justify-between px-4 py-3 border-b border-dark-border bg-dark-header">
                <span className="text-xs font-semibold text-dark-heading">Notifications</span>
                {notifications.length > 0 && (
                  <button
                    onClick={clearNotifications}
                    className="text-[11px] text-dark-muted hover:text-dark-heading"
                  >
                    Clear all
                  </button>
                )}
              </div>
              <div className="max-h-72 overflow-y-auto divide-y divide-dark-border">
                {notifications.length === 0 ? (
                  <div className="p-4 text-center text-xs text-dark-muted">No recent notifications.</div>
                ) : (
                  notifications.map((n) => (
                    <div key={n.id} className="p-3 text-xs hover:bg-dark-hover/40 transition-colors flex gap-2.5">
                      <div className="mt-0.5">{getNotificationIcon(n.type)}</div>
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold text-dark-heading text-[12px]">{n.title}</div>
                        <div className="text-dark-text text-[11px] mt-0.5">{n.message}</div>
                        <div className="text-[10px] text-dark-muted mt-1 font-mono">{n.timestamp}</div>
                      </div>
                      <button
                        onClick={() => removeNotification(n.id)}
                        className="text-dark-muted hover:text-dark-text text-xs px-1"
                      >
                        ×
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
