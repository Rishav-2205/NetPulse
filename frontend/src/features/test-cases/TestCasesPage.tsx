import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileCode2, Search, Filter, Play, CheckCircle2, RefreshCw } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Modal } from '../../components/ui/Modal';
import { testService } from '../../services/testService';
import { TestCase } from '../../types';
import { useAppStore } from '../../stores/useAppStore';

export const TestCasesPage: React.FC = () => {
  const navigate = useNavigate();
  const { addNotification } = useAppStore();

  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [protocolFilter, setProtocolFilter] = useState('ALL');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [selectedTestCase, setSelectedTestCase] = useState<TestCase | null>(null);

  const fetchCases = async () => {
    setLoading(true);
    try {
      const data = await testService.getTestCases();
      setTestCases(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, []);

  const handleRunTestCase = async (tc: TestCase) => {
    setSelectedTestCase(null);
    addNotification('info', 'Executing Test Case', `Triggering ${tc.test_id}: ${tc.name}...`);
    await testService.triggerRun('all', tc.protocol.toLowerCase());
    navigate('/test-runs');
  };

  const filteredCases = testCases.filter((tc) => {
    const matchSearch =
      tc.test_id.toLowerCase().includes(search.toLowerCase()) ||
      tc.name.toLowerCase().includes(search.toLowerCase()) ||
      tc.description.toLowerCase().includes(search.toLowerCase());
    const matchProto = protocolFilter === 'ALL' || tc.protocol === protocolFilter;
    const matchCat = categoryFilter === 'ALL' || tc.category === categoryFilter;
    return matchSearch && matchProto && matchCat;
  });

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-dark-border pb-4">
        <div>
          <h1 className="text-xl font-bold text-dark-heading tracking-tight">Test Case Taxonomy Catalog</h1>
          <p className="text-xs text-dark-muted mt-1">
            Structured repository of 105 automated network verification and performance test case specifications.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" icon={<RefreshCw className="w-3.5 h-3.5" />} onClick={fetchCases} isLoading={loading}>
            Refresh
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <Card className="p-4">
        <div className="flex flex-col md:flex-row items-center gap-3">
          <div className="w-full md:w-80">
            <Input
              placeholder="Search by ID (e.g. NET-TCP-001) or description..."
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
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="bg-dark-bg border border-dark-border rounded px-3 py-1.5 text-xs text-dark-text font-mono focus:outline-none focus:border-netpulse-blue"
            >
              <option value="ALL">Category: All</option>
              <option value="FUNCTIONAL">Functional</option>
              <option value="PERFORMANCE">Performance</option>
              <option value="FAULTS">Faults</option>
              <option value="INTEGRATION">Integration</option>
              <option value="REGRESSION">Regression</option>
              <option value="UNIT">Unit</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Test Cases Table */}
      <Card>
        <div className="overflow-x-auto -mx-5 -my-5">
          <table className="w-full text-left text-xs">
            <thead className="bg-dark-header border-b border-dark-border text-dark-muted font-mono uppercase text-[11px]">
              <tr>
                <th className="px-5 py-3 font-medium">Test ID</th>
                <th className="px-4 py-3 font-medium">Test Name</th>
                <th className="px-4 py-3 font-medium">Protocol</th>
                <th className="px-4 py-3 font-medium">OSI Layer</th>
                <th className="px-4 py-3 font-medium">Priority</th>
                <th className="px-4 py-3 font-medium">Category</th>
                <th className="px-5 py-3 font-medium text-right">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-border">
              {filteredCases.map((tc) => (
                <tr
                  key={tc.test_id}
                  onClick={() => setSelectedTestCase(tc)}
                  className="hover:bg-dark-hover/50 cursor-pointer transition-colors"
                >
                  <td className="px-5 py-3 font-mono font-medium text-netpulse-blue">{tc.test_id}</td>
                  <td className="px-4 py-3 font-medium text-dark-heading">{tc.name}</td>
                  <td className="px-4 py-3">
                    <Badge variant={tc.protocol === 'TCP' ? 'info' : tc.protocol === 'UDP' ? 'purple' : 'default'}>
                      {tc.protocol}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 font-mono text-dark-muted">{tc.layer}</td>
                  <td className="px-4 py-3">
                    <Badge variant={tc.priority === 'P0' ? 'danger' : tc.priority === 'P1' ? 'warning' : 'outline'}>
                      {tc.priority}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 font-mono text-dark-muted">{tc.category}</td>
                  <td className="px-5 py-3 text-right">
                    <span className="text-dark-muted hover:text-dark-heading text-xs">View Spec →</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Test Case Detail Modal */}
      {selectedTestCase && (
        <Modal
          isOpen={!!selectedTestCase}
          onClose={() => setSelectedTestCase(null)}
          title={`Test Specification: ${selectedTestCase.test_id}`}
          footer={
            <>
              <Button variant="ghost" size="sm" onClick={() => setSelectedTestCase(null)}>
                Close
              </Button>
              <Button
                variant="primary"
                size="sm"
                icon={<Play className="w-3.5 h-3.5" />}
                onClick={() => handleRunTestCase(selectedTestCase)}
              >
                Execute Test
              </Button>
            </>
          }
        >
          <div className="space-y-4 font-sans text-xs">
            <div>
              <h3 className="font-bold text-sm text-dark-heading">{selectedTestCase.name}</h3>
              <p className="text-dark-text mt-1">{selectedTestCase.description}</p>
            </div>

            <div className="grid grid-cols-2 gap-3 p-3 bg-dark-bg rounded-lg border border-dark-border font-mono text-[11px]">
              <div><span className="text-dark-muted">Protocol:</span> <span className="text-netpulse-blue font-bold">{selectedTestCase.protocol}</span></div>
              <div><span className="text-dark-muted">OSI Layer:</span> <span className="text-dark-heading">{selectedTestCase.layer}</span></div>
              <div><span className="text-dark-muted">Priority:</span> <span className="text-dark-heading">{selectedTestCase.priority}</span></div>
              <div><span className="text-dark-muted">Category:</span> <span className="text-dark-heading">{selectedTestCase.category}</span></div>
            </div>

            <div>
              <h4 className="font-semibold text-dark-muted uppercase text-[11px] mb-1">Expected Behavior</h4>
              <div className="p-3 bg-dark-bg rounded border border-dark-border text-dark-text">
                {selectedTestCase.expected_behavior}
              </div>
            </div>

            {selectedTestCase.preconditions && selectedTestCase.preconditions.length > 0 && (
              <div>
                <h4 className="font-semibold text-dark-muted uppercase text-[11px] mb-1">Preconditions</h4>
                <ul className="list-disc list-inside space-y-1 text-dark-text p-3 bg-dark-bg rounded border border-dark-border">
                  {selectedTestCase.preconditions.map((p, idx) => (
                    <li key={idx}>{p}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
};
