import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, XCircle, Clock, Activity, Terminal, Shield } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Tabs } from '../../components/ui/Tabs';
import { testService } from '../../services/testService';
import { TestRun } from '../../types';

export const TestRunDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [run, setRun] = useState<TestRun | null>(null);
  const [activeTab, setActiveTab] = useState('steps');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDetail = async () => {
      if (!id) return;
      setLoading(true);
      try {
        const data = await testService.getTestRunById(id);
        setRun(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchDetail();
  }, [id]);

  if (!run && !loading) {
    return (
      <div className="p-8 text-center space-y-3">
        <p className="text-sm text-dark-muted">Test run not found.</p>
        <Button variant="outline" size="sm" onClick={() => navigate('/test-runs')}>
          Back to Test Runs
        </Button>
      </div>
    );
  }

  const tabs = [
    { id: 'steps', label: 'Step Execution Flow', count: run?.steps?.length },
    { id: 'metrics', label: 'Telemetry & Metrics' },
    { id: 'logs', label: 'Structured Logs', count: run?.logs?.length },
  ];

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Back button and Header */}
      <div>
        <Button
          variant="ghost"
          size="sm"
          icon={<ArrowLeft className="w-3.5 h-3.5" />}
          onClick={() => navigate('/test-runs')}
          className="mb-3"
        >
          Back to Runs
        </Button>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-dark-border pb-4">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="font-mono text-sm text-netpulse-blue font-bold">{run?.test_id || 'NET-RUN'}</span>
              <Badge variant={run?.status === 'PASS' ? 'success' : 'danger'}>{run?.status || 'UNKNOWN'}</Badge>
              <Badge variant="outline">{run?.protocol || 'TCP'}</Badge>
            </div>
            <h1 className="text-xl font-bold text-dark-heading tracking-tight mt-1">{run?.name}</h1>
            <p className="text-xs text-dark-muted font-mono mt-0.5">
              Run ID: {run?.run_id} &bull; Started: {run ? new Date(run.started_at).toLocaleString() : ''} &bull; Total Duration: {run?.duration_ms} ms
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {/* Tab 1: Steps */}
      {activeTab === 'steps' && (
        <Card title="Execution Lifecycle Steps" subtitle="Detailed step transitions during socket lifecycle">
          <div className="space-y-3">
            {run?.steps && run.steps.length > 0 ? (
              run.steps.map((step, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-3.5 rounded-lg border border-dark-border bg-dark-bg/60 hover:bg-dark-hover/30 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    {step.status === 'PASS' ? (
                      <CheckCircle2 className="w-4 h-4 text-netpulse-green flex-shrink-0" />
                    ) : (
                      <XCircle className="w-4 h-4 text-netpulse-red flex-shrink-0" />
                    )}
                    <div>
                      <div className="text-xs font-semibold text-dark-heading">{step.name}</div>
                      <div className="text-[11px] font-mono text-dark-muted mt-0.5">Timestamp: {step.timestamp}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="font-mono text-xs font-medium text-dark-text">{step.duration_ms} ms</span>
                    <Badge variant={step.status === 'PASS' ? 'success' : 'danger'} size="sm" className="ml-2">
                      {step.status}
                    </Badge>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-dark-muted text-center py-6">No granular step telemetry recorded for this execution.</p>
            )}
          </div>
        </Card>
      )}

      {/* Tab 2: Metrics */}
      {activeTab === 'metrics' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card title="Throughput & Rate">
            <div className="text-2xl font-bold font-mono text-dark-heading">
              {run?.metrics?.throughput_mbps ? `${run.metrics.throughput_mbps} Mbps` : 'N/A'}
            </div>
            <p className="text-xs text-dark-muted font-mono mt-1">Sustained payload rate</p>
          </Card>

          <Card title="Average Latency (RTT)">
            <div className="text-2xl font-bold font-mono text-dark-heading">
              {run?.metrics?.latency_avg_ms ? `${run.metrics.latency_avg_ms} ms` : 'N/A'}
            </div>
            <p className="text-xs text-dark-muted font-mono mt-1">
              P95: {run?.metrics?.latency_p95_ms ? `${run.metrics.latency_p95_ms} ms` : '—'}
            </p>
          </Card>

          <Card title="Packet Loss & Jitter">
            <div className="text-2xl font-bold font-mono text-dark-heading">
              {run?.metrics?.packet_loss_percent !== undefined ? `${run.metrics.packet_loss_percent}%` : '0.00%'}
            </div>
            <p className="text-xs text-dark-muted font-mono mt-1">
              Jitter: {run?.metrics?.jitter_avg_ms ? `${run.metrics.jitter_avg_ms} ms` : '—'}
            </p>
          </Card>
        </div>
      )}

      {/* Tab 3: Logs */}
      {activeTab === 'logs' && (
        <Card title="Runtime Socket Logs" subtitle="Monotonic execution timestamps and trace output">
          <div className="bg-dark-bg border border-dark-border rounded-lg p-4 font-mono text-xs text-dark-text space-y-1.5 overflow-x-auto max-h-96">
            {run?.logs && run.logs.length > 0 ? (
              run.logs.map((log, idx) => (
                <div key={idx} className="leading-relaxed">
                  <span className="text-dark-muted select-none mr-3">{idx + 1}</span>
                  <span>{log}</span>
                </div>
              ))
            ) : (
              <div className="text-dark-muted">No raw logs attached to this test record.</div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
};
