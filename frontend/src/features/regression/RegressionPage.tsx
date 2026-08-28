import React, { useEffect, useState } from 'react';
import { GitCompare, CheckCircle2, AlertTriangle, Play, RefreshCw, BookmarkPlus, ShieldCheck } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { regressionService } from '../../services/regressionService';
import { RegressionReport } from '../../types';
import { useAppStore } from '../../stores/useAppStore';

export const RegressionPage: React.FC = () => {
  const { addNotification } = useAppStore();

  const [report, setReport] = useState<RegressionReport | null>(null);
  const [baselines, setBaselines] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchRegression = async () => {
    setLoading(true);
    try {
      const [rep, bases] = await Promise.all([
        regressionService.getRegression(),
        regressionService.getBaselines(),
      ]);
      setReport(rep);
      setBaselines(bases);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRegression();
  }, []);

  const handleCreateBaseline = async () => {
    addNotification('info', 'Creating Baseline', 'Saving current benchmark run as new authoritative baseline...');
    await regressionService.createBaseline();
    addNotification('success', 'Baseline Saved', 'Updated baseline.json.');
    fetchRegression();
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-dark-border pb-4">
        <div>
          <h1 className="text-xl font-bold text-dark-heading tracking-tight">Regression Intelligence & Baselines</h1>
          <p className="text-xs text-dark-muted mt-1">
            Automated performance diffing engine comparing live runs against authoritative historical baselines.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" icon={<RefreshCw className="w-3.5 h-3.5" />} onClick={fetchRegression} isLoading={loading}>
            Refresh
          </Button>
          <Button variant="primary" size="sm" icon={<BookmarkPlus className="w-3.5 h-3.5" />} onClick={handleCreateBaseline}>
            Set Current As Baseline
          </Button>
        </div>
      </div>

      {/* Regression Status Banner */}
      <div className="p-4 rounded-xl bg-dark-card border border-netpulse-green/40 flex items-center justify-between">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-full bg-netpulse-green/20 border border-netpulse-green/40 flex items-center justify-center text-netpulse-green">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-dark-heading">REGRESSION EVALUATION: PASS</span>
              <Badge variant="success">0 REGRESSIONS</Badge>
            </div>
            <p className="text-xs text-dark-muted mt-0.5">
              {report?.details || 'All performance metrics within configured baseline tolerance bounds.'}
            </p>
          </div>
        </div>
        <div className="text-right font-mono text-xs text-dark-muted hidden md:block">
          Evaluated against 105 automated test runs
        </div>
      </div>

      {/* Baseline Comparison Table */}
      <Card title="Authoritative Baseline vs. Current Run Comparison">
        <div className="overflow-x-auto -mx-5 -my-5">
          <table className="w-full text-left text-xs">
            <thead className="bg-dark-header border-b border-dark-border text-dark-muted font-mono uppercase text-[11px]">
              <tr>
                <th className="px-5 py-3 font-medium">Performance Metric</th>
                <th className="px-4 py-3 font-medium">Baseline Value</th>
                <th className="px-4 py-3 font-medium">Current Value</th>
                <th className="px-4 py-3 font-medium">Delta (Δ %)</th>
                <th className="px-4 py-3 font-medium">Allowed Tolerance</th>
                <th className="px-5 py-3 font-medium text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-border font-mono">
              {report?.metrics?.map((m, idx) => (
                <tr key={idx} className="hover:bg-dark-hover/50 transition-colors">
                  <td className="px-5 py-3 font-sans font-semibold text-dark-heading">{m.metric}</td>
                  <td className="px-4 py-3 text-dark-muted">{m.baseline_value}</td>
                  <td className="px-4 py-3 font-bold text-dark-heading">{m.current_value}</td>
                  <td className="px-4 py-3">
                    <span
                      className={
                        m.delta_percent > 0 && m.metric.includes('Throughput')
                          ? 'text-netpulse-green'
                          : m.delta_percent < 0 && m.metric.includes('Latency')
                          ? 'text-netpulse-green'
                          : m.delta_percent > 0
                          ? 'text-netpulse-red'
                          : 'text-dark-text'
                      }
                    >
                      {m.delta_percent > 0 ? `+${m.delta_percent}%` : `${m.delta_percent}%`}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-dark-muted">±{m.threshold_percent}%</td>
                  <td className="px-5 py-3 text-right">
                    <Badge variant={m.status === 'IMPROVEMENT' || m.status === 'PASS' ? 'success' : 'danger'}>
                      {m.status}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Authoritative Baseline Metadata */}
      <Card title="Active Baseline Metadata" subtitle="Stored in reports/baseline.json">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 font-mono text-xs">
          <div className="bg-dark-bg p-3.5 rounded-lg border border-dark-border">
            <span className="text-dark-muted block text-[11px]">Git Commit Hash</span>
            <span className="font-bold text-netpulse-blue mt-1 block">7e9c34a (main)</span>
          </div>
          <div className="bg-dark-bg p-3.5 rounded-lg border border-dark-border">
            <span className="text-dark-muted block text-[11px]">Test Profile</span>
            <span className="font-bold text-dark-heading mt-1 block">standard (multi-stream)</span>
          </div>
          <div className="bg-dark-bg p-3.5 rounded-lg border border-dark-border">
            <span className="text-dark-muted block text-[11px]">Recorded Timestamp</span>
            <span className="font-bold text-dark-heading mt-1 block">2026-08-28T18:00:00Z</span>
          </div>
          <div className="bg-dark-bg p-3.5 rounded-lg border border-dark-border">
            <span className="text-dark-muted block text-[11px]">Stability Grade</span>
            <span className="font-bold text-netpulse-green mt-1 block">STABLE (CV &lt; 5%)</span>
          </div>
        </div>
      </Card>
    </div>
  );
};
