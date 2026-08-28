import React, { useEffect, useState } from 'react';
import { FileBarChart, Download, ExternalLink, CheckCircle2, ShieldCheck, RefreshCw, FileText, Table as TableIcon } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Tabs } from '../../components/ui/Tabs';
import { reportService } from '../../services/reportService';
import { ArtifactFile, ConfigurationMatrixItem, PortfolioClaim } from '../../types';

export const ReportsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('claims');
  const [artifacts, setArtifacts] = useState<ArtifactFile[]>([]);
  const [claims, setClaims] = useState<PortfolioClaim[]>([]);
  const [matrix, setMatrix] = useState<ConfigurationMatrixItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const [arts, clms, mtx] = await Promise.all([
        reportService.getReports(),
        reportService.getClaims(),
        reportService.getMatrix(),
      ]);
      setArtifacts(arts);
      setClaims(clms);
      setMatrix(mtx);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const tabs = [
    { id: 'claims', label: 'Portfolio Claims Audit', count: claims.length },
    { id: 'matrix', label: 'Configuration Matrix (44)', count: matrix.length },
    { id: 'artifacts', label: 'Report Artifacts', count: artifacts.length },
  ];

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-dark-border pb-4">
        <div>
          <h1 className="text-xl font-bold text-dark-heading tracking-tight">Reports & Evidence Portfolio</h1>
          <p className="text-xs text-dark-muted mt-1">
            Authoritative system audit, configuration matrix, and verified portfolio claims backed by raw evidence files.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" icon={<RefreshCw className="w-3.5 h-3.5" />} onClick={fetchReports} isLoading={loading}>
            Refresh
          </Button>
        </div>
      </div>

      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {/* Tab 1: Portfolio Claims Audit */}
      {activeTab === 'claims' && (
        <Card
          title="Evidence-Based Portfolio Claims Audit"
          subtitle="Strict zero-fabrication metrics validated against real socket benchmarks and test runs"
        >
          <div className="overflow-x-auto -mx-5 -my-5">
            <table className="w-full text-left text-xs">
              <thead className="bg-dark-header border-b border-dark-border text-dark-muted font-mono uppercase text-[11px]">
                <tr>
                  <th className="px-5 py-3 font-medium">Engineering Claim</th>
                  <th className="px-4 py-3 font-medium">Measured Value</th>
                  <th className="px-4 py-3 font-medium">Verification Method</th>
                  <th className="px-4 py-3 font-medium">Sample Size</th>
                  <th className="px-4 py-3 font-medium">Evidence File</th>
                  <th className="px-5 py-3 font-medium text-right">Resume Safe</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-border">
                {claims.map((c, idx) => (
                  <tr key={idx} className="hover:bg-dark-hover/50 transition-colors">
                    <td className="px-5 py-3 font-semibold text-dark-heading">{c.metric}</td>
                    <td className="px-4 py-3 font-mono font-bold text-netpulse-blue">
                      {c.value} {c.unit}
                    </td>
                    <td className="px-4 py-3 text-dark-text text-[11px]">{c.measurement_method}</td>
                    <td className="px-4 py-3 font-mono text-dark-muted text-[11px]">{c.sample_size}</td>
                    <td className="px-4 py-3 font-mono text-dark-muted text-[11px]">{c.evidence_file}</td>
                    <td className="px-5 py-3 text-right">
                      <Badge variant="success" size="sm">
                        {c.resume_safe}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Tab 2: Configuration Matrix */}
      {activeTab === 'matrix' && (
        <Card title="Combinatorial Configuration Matrix" subtitle="44 distinct L4-L7 network parameter permutations">
          <div className="overflow-x-auto -mx-5 -my-5 max-h-[500px] overflow-y-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-dark-header border-b border-dark-border text-dark-muted uppercase text-[11px] sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3 font-medium">ID</th>
                  <th className="px-3 py-3 font-medium">Proto</th>
                  <th className="px-3 py-3 font-medium">Buffer Size</th>
                  <th className="px-3 py-3 font-medium">Workers</th>
                  <th className="px-3 py-3 font-medium">Timeout</th>
                  <th className="px-3 py-3 font-medium">Retries</th>
                  <th className="px-3 py-3 font-medium">Fault Profile</th>
                  <th className="px-4 py-3 font-medium">Target Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-border text-[11px]">
                {matrix.map((m, idx) => (
                  <tr key={idx} className="hover:bg-dark-hover/50 transition-colors">
                    <td className="px-4 py-2.5 text-netpulse-blue font-bold">{m.matrix_id}</td>
                    <td className="px-3 py-2.5 font-bold text-dark-heading">{m.protocol}</td>
                    <td className="px-3 py-2.5 text-dark-muted">{m.buffer_size_bytes} B</td>
                    <td className="px-3 py-2.5 text-dark-muted">{m.concurrency_workers}</td>
                    <td className="px-3 py-2.5 text-dark-muted">{m.timeout_seconds}s</td>
                    <td className="px-3 py-2.5 text-dark-muted">{m.retry_count}</td>
                    <td className="px-3 py-2.5">
                      <Badge variant={m.fault_profile === 'clean' ? 'outline' : 'warning'} size="sm">
                        {m.fault_profile}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5 text-dark-text font-sans">{m.target_description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Tab 3: Artifacts */}
      {activeTab === 'artifacts' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {artifacts.map((art, idx) => (
            <Card key={idx} className="p-4 flex flex-col justify-between space-y-4">
              <div>
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-netpulse-blue" />
                  <span className="font-semibold text-xs text-dark-heading">{art.name}</span>
                </div>
                <p className="font-mono text-[11px] text-dark-muted mt-1">{art.path}</p>
              </div>
              <div className="flex items-center justify-between pt-3 border-t border-dark-border">
                <Badge variant={art.available ? 'success' : 'outline'} size="sm">
                  {art.available ? 'AVAILABLE' : 'PENDING'}
                </Badge>
                <a
                  href={`/api/reports/download/${art.path.replace('reports/', '')}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-netpulse-blue hover:underline flex items-center gap-1"
                >
                  <Download className="w-3.5 h-3.5" />
                  Open File
                </a>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
