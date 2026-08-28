import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Search, Filter, RefreshCw, CheckCircle2, XCircle } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Modal } from '../../components/ui/Modal';
import { testService } from '../../services/testService';
import { TestRun } from '../../types';
import { useAppStore } from '../../stores/useAppStore';

export const TestRunsPage: React.FC = () => {
  const navigate = useNavigate();
  const { addNotification } = useAppStore();

  const [runs, setRuns] = useState<TestRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [protocolFilter, setProtocolFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [isTriggerModalOpen, setIsTriggerModalOpen] = useState(false);
  const [selectedSuite, setSelectedSuite] = useState('functional');

  const fetchRuns = async () => {
    setLoading(true);
    try {
      const data = await testService.getTestRuns();
      setRuns(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
  }, []);

  const handleTriggerRun = async () => {
    setIsTriggerModalOpen(false);
    addNotification('info', 'Test Suite Queued', `Triggering suite '${selectedSuite}'...`);
    await testService.triggerRun(selectedSuite);
    fetchRuns();
  };

  const filteredRuns = runs.filter((run) => {
    const matchSearch =
      run.name.toLowerCase().includes(search.toLowerCase()) ||
      run.run_id.toLowerCase().includes(search.toLowerCase()) ||
      (run.test_id && run.test_id.toLowerCase().includes(search.toLowerCase()));
    const matchProto = protocolFilter === 'ALL' || run.protocol === protocolFilter;
    const matchStatus = statusFilter === 'ALL' || run.status === statusFilter;
    return matchSearch && matchProto && matchStatus;
  });

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-dark-border pb-4">
        <div>
          <h1 className="text-xl font-bold text-dark-heading tracking-tight">Test Runs Management</h1>
          <p className="text-xs text-dark-muted mt-1">
            Browse, filter, and inspect automated network verification and performance test executions.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" icon={<RefreshCw className="w-3.5 h-3.5" />} onClick={fetchRuns} isLoading={loading}>
            Refresh
          </Button>
          <Button variant="primary" size="sm" icon={<Play className="w-3.5 h-3.5" />} onClick={() => setIsTriggerModalOpen(true)}>
            Execute Test Suite
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <Card className="p-4">
        <div className="flex flex-col md:flex-row items-center gap-3">
          <div className="w-full md:w-80">
            <Input
              placeholder="Search by Run ID, Test ID, or name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2 w-full md:w-auto ml-auto">
            <select
              value={protocolFilter}
              onChange={(e) => setProtocolFilter(e.target.value)}
              className="bg-dark-bg border border-dark-border rounded px-3 py-1.5 text-xs text-dark-text font-mono focus:outline-none focus:border-netpulse-blue"
            >
              <option value="ALL">Protocol: All</option>
              <option value="TCP">TCP</option>
              <option value="UDP">UDP</option>
              <option value="HTTP">HTTP</option>
            </select>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-dark-bg border border-dark-border rounded px-3 py-1.5 text-xs text-dark-text font-mono focus:outline-none focus:border-netpulse-blue"
            >
              <option value="ALL">Status: All</option>
              <option value="PASS">PASS</option>
              <option value="FAIL">FAIL</option>
              <option value="SKIPPED">SKIPPED</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Runs Table */}
      <Card>
        <div className="overflow-x-auto -mx-5 -my-5">
          <table className="w-full text-left text-xs">
            <thead className="bg-dark-header border-b border-dark-border text-dark-muted font-mono uppercase text-[11px]">
              <tr>
                <th className="px-5 py-3 font-medium">Run ID</th>
                <th className="px-4 py-3 font-medium">Test ID</th>
                <th className="px-4 py-3 font-medium">Test Name</th>
                <th className="px-4 py-3 font-medium">Protocol</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Duration</th>
                <th className="px-4 py-3 font-medium">Started</th>
                <th className="px-5 py-3 font-medium text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-border">
              {filteredRuns.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-5 py-8 text-center text-dark-muted text-xs">
                    No test runs matched the selected filters.
                  </td>
                </tr>
              ) : (
                filteredRuns.map((run) => (
                  <tr
                    key={run.run_id}
                    onClick={() => navigate(`/test-runs/${run.run_id}`)}
                    className="hover:bg-dark-hover/50 cursor-pointer transition-colors"
                  >
                    <td className="px-5 py-3 font-mono font-medium text-netpulse-blue">{run.run_id}</td>
                    <td className="px-4 py-3 font-mono text-dark-muted">{run.test_id || '—'}</td>
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
                    <td className="px-4 py-3 font-mono text-dark-muted">{new Date(run.started_at).toLocaleTimeString()}</td>
                    <td className="px-5 py-3 text-right">
                      <span className="text-dark-muted hover:text-dark-heading text-xs">Inspect →</span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Trigger Run Modal */}
      <Modal
        isOpen={isTriggerModalOpen}
        onClose={() => setIsTriggerModalOpen(false)}
        title="Execute Automated Test Suite"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setIsTriggerModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" icon={<Play className="w-3.5 h-3.5" />} onClick={handleTriggerRun}>
              Start Execution
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-xs text-dark-muted">
            Select the test suite to execute against the network test laboratory:
          </p>
          <div className="space-y-2">
            {[
              { id: 'functional', title: 'Functional Protocols (TCP, UDP, HTTP)', desc: 'Validates framing, handshakes, keep-alive reuse, and echo roundtrips' },
              { id: 'performance', title: 'Performance Benchmarks', desc: 'Measures sustained throughput, latency percentiles (P95/P99), loss and jitter' },
              { id: 'faults', title: 'Fault-Injection Scenarios (NET-FAULT-001..010)', desc: 'Validates behavior under latency, packet loss, jitter, and link reset' },
              { id: 'regression', title: 'Regression Test Suite', desc: 'Validates invariants and verifies zero degradation against baseline' },
              { id: 'all', title: 'Complete 105-Test Matrix', desc: 'Executes entire end-to-end multi-layer test taxonomy' },
            ].map((suite) => (
              <label
                key={suite.id}
                className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  selectedSuite === suite.id
                    ? 'bg-netpulse-blue/10 border-netpulse-blue/40 text-dark-heading'
                    : 'bg-dark-bg border-dark-border text-dark-text hover:bg-dark-hover'
                }`}
              >
                <input
                  type="radio"
                  name="suite"
                  value={suite.id}
                  checked={selectedSuite === suite.id}
                  onChange={(e) => setSelectedSuite(e.target.value)}
                  className="mt-1 accent-netpulse-blue"
                />
                <div>
                  <div className="text-xs font-semibold">{suite.title}</div>
                  <div className="text-[11px] text-dark-muted mt-0.5">{suite.desc}</div>
                </div>
              </label>
            ))}
          </div>
        </div>
      </Modal>
    </div>
  );
};
