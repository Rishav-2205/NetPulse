/**
 * NetPulse Frontend Core TypeScript Type Definitions
 */

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'offline';
  version: string;
  environment: string;
  os: string;
  python_version: string;
  git_commit: string;
  capabilities: {
    cap_net_admin?: boolean;
    cap_net_raw?: boolean;
    linux_namespaces?: boolean;
    [key: string]: boolean | undefined;
  };
  active_fault?: FaultConfig | null;
}

export interface TestCase {
  test_id: string;
  name: string;
  description: string;
  category: 'FUNCTIONAL' | 'INTEGRATION' | 'PERFORMANCE' | 'REGRESSION' | 'UNIT' | 'FAULTS' | string;
  protocol: 'TCP' | 'UDP' | 'HTTP' | 'IP' | 'ETHERNET' | 'ALL' | string;
  layer: 'LAYER_2' | 'LAYER_3' | 'LAYER_4' | 'LAYER_7' | string;
  priority: 'P0' | 'P1' | 'P2' | 'P3' | string;
  expected_behavior: string;
  preconditions: string[];
}

export interface TestRunStep {
  name: string;
  status: 'PASS' | 'FAIL' | 'ERROR' | 'SKIPPED';
  duration_ms: number;
  timestamp: string;
  error?: string;
}

export interface TestRun {
  run_id: string;
  test_id?: string;
  name: string;
  protocol: string;
  category: string;
  status: 'PASS' | 'FAIL' | 'ERROR' | 'SKIPPED' | 'FLAKY';
  duration_ms: number;
  started_at: string;
  steps?: TestRunStep[];
  metrics?: {
    throughput_mbps?: number;
    latency_avg_ms?: number;
    latency_p95_ms?: number;
    packet_loss_percent?: number;
    jitter_avg_ms?: number;
    packets_sent?: number;
    packets_received?: number;
    bytes_sent?: number;
    bytes_received?: number;
    [key: string]: any;
  };
  logs?: string[];
  error_message?: string;
  stack_trace?: string;
}

export interface BenchmarkMetrics {
  protocol: string;
  throughput_mbps?: number;
  latency_avg_ms?: number;
  latency_min_ms?: number;
  latency_max_ms?: number;
  latency_p50_ms?: number;
  latency_p90_ms?: number;
  latency_p95_ms?: number;
  latency_p99_ms?: number;
  packet_loss_percent?: number;
  jitter_avg_ms?: number;
  jitter_p95_ms?: number;
  packets_sent?: number;
  packets_received?: number;
  bytes_transferred?: number;
  duration_seconds?: number;
  concurrency?: number;
  packet_size?: number;
  timestamp: string;
}

export interface TopologyNode {
  id: string;
  name: string;
  type: 'client' | 'router' | 'server';
  ip_addresses: string[];
  interfaces: string[];
  status: 'active' | 'inactive' | 'degraded';
  routes?: Array<{ destination: string; gateway: string; interface: string }>;
  is_forwarding?: boolean;
}

export interface TopologyLink {
  id: string;
  source: string;
  target: string;
  source_interface: string;
  target_interface: string;
  bandwidth_mbps: number;
  latency_ms: number;
  packet_loss_percent: number;
  jitter_ms: number;
  status: 'clean' | 'impaired' | 'down';
  active_fault?: FaultConfig;
}

export interface TopologyState {
  is_active: boolean;
  is_simulated: boolean;
  nodes: TopologyNode[];
  links: TopologyLink[];
}

export interface FaultConfig {
  fault_type?: string;
  latency_ms: number;
  jitter_ms: number;
  packet_loss_percent: number;
  bandwidth_mbps?: number | null;
  correlation_pct?: number;
  corruption_percent?: number;
  description?: string;
}

export interface FaultProfile {
  name: string;
  config: FaultConfig;
}

export interface ExperimentObservation {
  latency_avg_ms?: number;
  packet_loss_percent?: number;
  jitter_avg_ms?: number;
  throughput_mbps?: number;
  total_packets_sent: number;
  total_packets_received: number;
  duration_seconds: number;
}

export interface ExperimentImpact {
  latency_delta_ms?: number;
  loss_delta_pct?: number;
  jitter_delta_ms?: number;
  throughput_delta_pct?: number;
}

export interface ExperimentResult {
  experiment_id: string;
  protocol: string;
  fault_profile: string;
  applied_fault: FaultConfig;
  control_observation: ExperimentObservation;
  experiment_observation: ExperimentObservation;
  impact: ExperimentImpact;
  classification: 'EXPECTED_DEGRADATION' | 'UNEXPECTED_REGRESSION';
  details: string;
  started_at: string;
  completed_at: string;
}

export interface PacketSummary {
  index: number;
  timestamp: string;
  src_ip: string;
  dst_ip: string;
  protocol: 'TCP' | 'UDP' | 'HTTP' | 'ICMP' | 'OTHER' | string;
  length_bytes: number;
  sport?: number;
  dport?: number;
  flags?: string[];
  seq?: number;
  ack?: number;
  info: string;
  layers?: {
    frame?: { length: number; timestamp: string };
    ethernet?: { src_mac: string; dst_mac: string };
    ipv4?: { src: string; dst: string; ttl: number; protocol: string };
    tcp?: { sport: number; dport: number; seq: number; ack: number; flags: string[] };
    udp?: { sport: number; dport: number; length: number; sequence?: number; send_time_ns?: number };
  };
}

export interface RegressionComparisonItem {
  metric: string;
  baseline_value: number;
  current_value: number;
  delta_percent: number;
  threshold_percent: number;
  status: 'PASS' | 'REGRESSION' | 'IMPROVEMENT';
}

export interface RegressionReport {
  status: 'PASS' | 'FAIL' | 'REGRESSION';
  timestamp: string;
  total_tests: number;
  regressions_count: number;
  metrics: RegressionComparisonItem[];
  details: string;
}

export interface PortfolioClaim {
  metric: string;
  value: string;
  unit: string;
  measurement_method: string;
  sample_size: string;
  evidence_file: string;
  resume_safe: 'YES' | 'NO';
}

export interface ArtifactFile {
  name: string;
  path: string;
  available: boolean;
}

export interface ConfigurationMatrixItem {
  matrix_id: string;
  protocol: string;
  layer: string;
  buffer_size_bytes: number;
  concurrency_workers: number;
  timeout_seconds: number;
  retry_count: number;
  fault_profile: string;
  target_description: string;
}
