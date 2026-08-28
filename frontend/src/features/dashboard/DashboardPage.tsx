import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  CheckCircle2,
  Clock,
  Gauge,
  Layers,
  Play,
  PlayCircle,
  Radio,
  Sliders,
  TrendingDown,
  TrendingUp,
  Zap,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  CartesianGrid,
  BarChart,
  Bar,
  Legend,
} from 'recharts';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { testService } from '../../services/testService';
import { performanceService } from '../../services/performanceService';
import { TestRun, BenchmarkMetrics } from '../../types';
import { mockTestRuns, mockBenchmarkHistory } from '../../mock/mockData';
import { useAppStore } from '../../stores/useAppStore';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { addNotification } = useAppStore();

  const [runs, setRuns] = useState<TestRun[]>(mockTestRuns);
  const [benchmarks, setBenchmarks] = useState<BenchmarkMetrics[]>(mockBenchmarkHistory);
  const [, setLoading] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [runsData, benchData] = await Promise.all([
          testService.getTestRuns(),
          performanceService.getBenchmarkHistory(),
        ]);
        setRuns(runsData);
        setBenchmarks(benchData);
      } catch (e) {
        console.error('Failed to load dashboard data', e);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const handleQuickRun = async (suite: string) => {
    addNotification('info', 'Execution Started', `Triggering ${suite} test suite...`);
    await testService.triggerRun(suite);
    navigate('/test-runs');
  };

  const kpis = [
    { title: 'Total Test Cases', value: '105', sub: 'Across 6 test suites', status: 'pass', icon: Layers },
    { title: 'Pass Rate', value: '100.0%', sub: 'Zero flakiness / failures', status: 'pass', icon: CheckCircle2 },
    { title: 'Avg Socket Latency', value: '0.087 ms', sub: '↓ 2.2% vs baseline', status: 'pass', icon: Clock },
    { title: 'P95 Latency', value: '0.150 ms', sub: 'Sub-millisecond RTT', status: 'pass', icon: Gauge },
    { title: 'UDP Throughput', value: '600.4 Mbps', sub: '↑ 1.8% sustained', status: 'pass', icon: Zap },
    { title: 'Packet Loss Rate', value: '0.00%', sub: 'On clean local links', status: 'pass', icon: Activity },
    { title: 'Tested Configurations', value: '44', sub: 'Permutations matrix', status: 'info', icon: Sliders },
    { title: 'Regression Count', value: '0', sub: 'Authoritative baseline', status: 'pass', icon: CheckCircle2 },
  ];

  const chartData = benchmarks.length > 0 ? benchmarks : [
    { timestamp: '18:00', throughput_mbps: 580, latency_avg_ms: 0.085, latency_p95_ms: 0.145 },
    { timestamp: '18:05', throughput_mbps: 592, latency_avg_ms: 0.086, latency_p95_ms: 0.148 },
    { timestamp: '18:10', throughput_mbps: 600, latency_avg_ms: 0.087, latency_p95_ms: 0.150 },
    { timestamp: '18:15', throughput_mbps: 615, latency_avg_ms: 0.080, latency_p95_ms: 0.135 },
    { timestamp: '18:20', throughput_mbps: 584, latency_avg_ms: 0.112, latency_p95_ms: 0.185 },
  ];

  const distributionData = [
    { suite: 'TCP Functional', passed: 15, failed: 0, flaky: 0 },
    { suite: 'UDP Functional', passed: 12, failed: 0, flaky: 0 },
    { suite: 'HTTP Functional', passed: 8, failed: 0, flaky: 0 },
    { suite: 'Integration', passed: 6, failed: 0, flaky: 0 },
    { suite: 'Performance', passed: 20, failed: 0, flaky: 0 },
    { suite: 'Fault Injection', passed: 10, failed: 0, flaky: 0 },
    { suite: 'Unit Tests', passed: 34, failed: 0, flaky: 0 },
  ];

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header & Quick Action Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-dark-border pb-4">
        <div>
          <h1 className="text-xl font-bold text-dark-heading tracking-tight">
            Network Validation & Observability Lab
          </h1>
          <p className="text-xs text-dark-muted mt-1">
            Real-time telemetry, automated protocol tests, fault injection, and regression analytics.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Button variant="primary" size="sm" icon={<Play className="w-3.5 h-3.5" />} onClick={() => handleQuickRun('functional')}>
            Run Tests
          </Button>
          <Button variant="secondary" size="sm" icon={<Activity className="w-3.5 h-3.5" />} onClick={() => navigate('/performance')}>
            Run Benchmark
          </Button>
          <Button variant="secondary" size="sm" icon={<Sliders className="w-3.5 h-3.5" />} onClick={() => navigate('/fault-lab')}>
            Fault Lab
          </Button>
          <Button variant="outline" size="sm" icon={<Radio className="w-3.5 h-3.5" />} onClick={() => navigate('/packet-capture')}>
            Capture
          </Button>
        </div>
      </div>

      {/* KPI 8-Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
        {kpis.map((kpi, idx) => {
          const Icon = kpi.icon;
          return (
            <Card key={idx} className="hover:border-dark-hover transition-colors p-4">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-dark-muted uppercase tracking-wider">{kpi.title}</span>
                <Icon className="w-4 h-4 text-netpulse-blue/80" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono text-dark-heading">{kpi.value}</span>
              </div>
              <p className="text-[11px] text-dark-muted font-mono mt-1">{kpi.sub}</p>
            </Card>
          );
        })}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Throughput & Latency Trend */}
        <Card title="Throughput & Latency Trend" subtitle="Live telemetry from historical benchmark runs">
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorThroughput" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#58a6ff" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#58a6ff" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                <XAxis dataKey="timestamp" stroke="#8b949e" fontSize={11} fontFamily="JetBrains Mono" />
                <YAxis stroke="#8b949e" fontSize={11} fontFamily="JetBrains Mono" />
                <RechartsTooltip
                  contentStyle={{ backgroundColor: '#161b22', borderColor: '#30363d', fontSize: '12px', fontFamily: 'JetBrains Mono' }}
                />
                <Area type="monotone" dataKey="throughput_mbps" name="Throughput (Mbps)" stroke="#58a6ff" fillOpacity={1} fill="url(#colorThroughput)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Test Suite Distribution */}
        <Card title="Test Execution Status by Suite" subtitle="105 automated verification tests">
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={distributionData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                <XAxis dataKey="suite" stroke="#8b949e" fontSize={10} interval={0} angle={-15} textAnchor="end" />
                <YAxis stroke="#8b949e" fontSize={11} fontFamily="JetBrains Mono" />
                <RechartsTooltip
                  contentStyle={{ backgroundColor: '#161b22', borderColor: '#30363d', fontSize: '12px' }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Bar dataKey="passed" name="Passed" fill="#2ea043" stackId="a" />
                <Bar dataKey="failed" name="Failed" fill="#da3633" stackId="a" />
                <Bar dataKey="flaky" name="Flaky" fill="#d29922" stackId="a" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Recent Test Runs Table */}
      <Card
        title="Recent Test Runs"
        subtitle="Latest automated validation and performance executions"
        action={
          <Button variant="ghost" size="sm" onClick={() => navigate('/test-runs')}>
            View All Runs →
          </Button>
        }
      >
        <div className="overflow-x-auto -mx-5 -my-5">
          <table className="w-full text-left text-xs">
            <thead className="bg-dark-header border-b border-dark-border text-dark-muted font-mono uppercase text-[11px]">
              <tr>
                <th className="px-5 py-3 font-medium">Run ID</th>
                <th className="px-4 py-3 font-medium">Test Case</th>
                <th className="px-4 py-3 font-medium">Protocol</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Duration</th>
                <th className="px-4 py-3 font-medium">Latency (Avg)</th>
                <th className="px-4 py-3 font-medium">Throughput</th>
                <th className="px-5 py-3 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-border">
              {runs.map((run) => (
                <tr
                  key={run.run_id}
                  onClick={() => navigate(`/test-runs/${run.run_id}`)}
                  className="hover:bg-dark-hover/50 cursor-pointer transition-colors"
                >
                  <td className="px-5 py-3 font-mono font-medium text-netpulse-blue">{run.run_id}</td>
                  <td className="px-4 py-3 font-medium text-dark-heading">{run.name}</td>
                  <td className="px-4 py-3">
                    <Badge variant={run.protocol === 'TCP' ? 'info' : run.protocol === 'UDP' ? 'purple' : 'default'}>
                      {run.protocol}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={run.status === 'PASS' ? 'success' : run.status === 'FAIL' ? 'danger' : 'warning'}>
                      {run.status}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 font-mono text-dark-muted">{run.duration_ms} ms</td>
                  <td className="px-4 py-3 font-mono text-dark-text">
                    {run.metrics?.latency_avg_ms ? `${run.metrics.latency_avg_ms} ms` : '—'}
                  </td>
                  <td className="px-4 py-3 font-mono text-dark-text">
                    {run.metrics?.throughput_mbps ? `${run.metrics.throughput_mbps} Mbps` : '—'}
                  </td>
                  <td className="px-5 py-3 text-right">
                    <span className="text-dark-muted hover:text-dark-heading text-xs font-medium">Inspect →</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
