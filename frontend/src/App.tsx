import React from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from './components/layout/AppLayout';
import { DashboardPage } from './features/dashboard/DashboardPage';
import { TestRunsPage } from './features/test-runs/TestRunsPage';
import { TestRunDetailPage } from './features/test-runs/TestRunDetailPage';
import { PerformanceLabPage } from './features/performance/PerformanceLabPage';
import { TopologyPage } from './features/topology/TopologyPage';
import { PacketCapturePage } from './features/packet-capture/PacketCapturePage';
import { TestCasesPage } from './features/test-cases/TestCasesPage';
import { RegressionPage } from './features/regression/RegressionPage';
import { FaultLabPage } from './features/fault-lab/FaultLabPage';
import { ReportsPage } from './features/reports/ReportsPage';
import { SettingsPage } from './features/settings/SettingsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="test-runs" element={<TestRunsPage />} />
            <Route path="test-runs/:id" element={<TestRunDetailPage />} />
            <Route path="performance" element={<PerformanceLabPage />} />
            <Route path="topology" element={<TopologyPage />} />
            <Route path="packet-capture" element={<PacketCapturePage />} />
            <Route path="test-cases" element={<TestCasesPage />} />
            <Route path="regression" element={<RegressionPage />} />
            <Route path="fault-lab" element={<FaultLabPage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </HashRouter>
    </QueryClientProvider>
  );
};
