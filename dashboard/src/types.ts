export interface RunRecord {
  id: string;
  target: string;
  repo_display: string;
  github_url: string | null;
  repo_key: string;
  run_number: number;
  rerun_of: string | null;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
  completed_at: string | null;
  error: string | null;
  omega_index: number | null;
  quality_grade: string | null;
  file_count: number | null;
  total_loc: number | null;
  output_dir: string | null;
}

export interface RepoSummary {
  repo_key: string;
  repo_display: string;
  target: string;
  github_url: string | null;
  run_count: number;
  latest_run_id: string;
  latest_status: string;
  latest_created_at: string;
  latest_omega_index: number | null;
  latest_quality_grade: string | null;
}

export interface RunHistoryResponse {
  repo_key: string;
  repo_display: string;
  target: string;
  github_url: string | null;
  current_run_id: string;
  run_count: number;
  runs: RunRecord[];
}

export interface FileMetric {
  path: string;
  language: string;
  omega_local: number;
  risk_band: string;
  business_note: string;
  loc: number;
  cyclomatic: number;
  nesting_depth: number;
  h_struct: number;
  h_text: number;
  coupling_out: number;
  coupling_in: number;
  compression_ratio: number;
}

export interface EntityMetric {
  entity_type: string;
  qualified_name: string;
  file_path: string;
  line_start: number;
  line_end: number;
  loc: number;
  cyclomatic: number;
  nesting_depth: number;
  omega_local: number;
  risk_band: string;
  parent_class: string | null;
  parameter_count: number;
  method_count: number;
  field_count: number;
  improvement_areas: string[];
  improvement_areas_business: string[];
  implementation_plan: string[];
  implementation_summary: string[];
  implementation_diffs?: ImplementationDiff[];
}

export interface ImplementationDiff {
  title: string;
  location: string;
  description: string;
  before: string;
  after: string;
  language: string;
  business_outcome: string;
  /** Plain-language one-liner for non-experts */
  simple_summary?: string;
  /** Numbered steps: open file → replace code → test */
  steps?: string[];
}

export interface ImprovementItem {
  entity_type: string;
  qualified_name: string;
  file_path: string;
  lines: string;
  omega_local: number;
  risk_band: string;
  cyclomatic: number;
  nesting_depth: number;
  improvement_areas: string[];
  improvement_areas_business: string[];
  implementation_plan: string[];
  implementation_summary: string[];
  implementation_diffs?: ImplementationDiff[];
}

export interface GroupedFileRow {
  path: string;
  omega_local: number;
  risk_band: string;
  cyclomatic: number;
  nesting_depth: number;
}

export interface DeveloperAction {
  priority: number;
  category: string;
  title: string;
  location: string;
  risk_band: string;
  symbol: string | null;
  metrics: Record<string, number>;
  why_risky: string;
  what_to_do: string[];
  implementation_plan: string[];
  implementation_diffs?: ImplementationDiff[];
  action_tier?: "sprint" | "backlog" | "summary";
  grouped_files?: GroupedFileRow[];
}

export interface DeveloperGuide {
  introduction: string;
  how_to_read: string[];
  action_count: number;
  actions: DeveloperAction[];
  guide_version?: number;
  sprint_count?: number;
  module_group_count?: number;
}

export interface RepoDimension {
  id: string;
  name: string;
  score: number;
  band: string;
  weight: number;
  repo_aggregate: number;
  unit: string;
  family?: string;
  /** False when this repo/service does not qualify for this lens (omitted from API output). */
  applicable?: boolean;
  /** Always false: letter grade comes from Ω index only. */
  contributes_to_grade?: boolean;
  qualification?: string;
  summary_technical: string;
  summary_business: string;
  evidence: string[];
  evidence_symbols: string[];
  actions_in_repo: string[];
  top_contributors: Record<string, unknown>[];
}

export interface LanguageStackEntry {
  language: string;
  file_count: number;
  share_pct: number;
  worker_id: string;
  strategy: string;
  capabilities: string[];
}

export interface WorkerSpec {
  worker_id: string;
  language: string;
  strategy: string;
  file_count: number;
  capabilities: string[];
}

export interface WorkerResult {
  worker_id: string;
  language: string;
  strategy: string;
  status: string;
  files_analyzed: number;
  entities_found: number;
  duration_ms: number;
  error?: string | null;
  capabilities?: string[];
}

export interface AgentManifest {
  root: string;
  total_files: number;
  total_bytes: number;
  primary_language: string;
  tech_stack: LanguageStackEntry[];
  workers_planned: WorkerSpec[];
  worker_results?: WorkerResult[];
  orchestration_plan: string[];
}

export interface MetricRecord {
  id: string;
  name: string;
  category: string;
  value: number;
  unit: string;
  formula: string;
  band: string;
  weight: number;
  summary_technical: string;
  summary_business: string;
  evidence: string[];
  related_service?: string | null;
  edge_kind?: string | null;
}

export interface ServiceContext {
  service_name: string;
  service_role: string;
  business_domains: string[];
  deployment_artifacts: string[];
  entry_points: string[];
  config_source: string;
  description_technical: string;
  description_business: string;
}

export interface EcosystemNode {
  name: string;
  kind: string;
  direction: string;
  evidence: string[];
  metadata?: Record<string, unknown>;
}

export interface MetricSuite {
  suite_version: number;
  metric_count: number;
  service_context: ServiceContext;
  ecosystem: {
    upstream: EcosystemNode[];
    downstream: EcosystemNode[];
    upstream_count: number;
    downstream_count: number;
    graph_summary_technical: string;
    graph_summary_business: string;
  };
  metrics: MetricRecord[];
  by_category: Record<string, MetricRecord[]>;
  impact_summary: Record<string, number | null>;
}

export interface FullReport {
  repository: string;
  repo_display: string;
  github_url: string | null;
  analyzed_at: string;
  omega_index: number;
  quality_grade: string;
  bayesian_quality: number;
  epistemic_uncertainty: number;
  scorecard?: {
    code_quality: number;
    security: number;
    performance: number;
    architecture: number;
    technical_debt: number;
  };
  health_summary_technical: string;
  health_summary_business: string;
  file_count: number;
  total_loc: number;
  pillars: Record<string, number>;
  dimensions: RepoDimension[];
  developer_guide: DeveloperGuide;
  hotspots: string[];
  languages: Record<string, number>;
  recommendations_technical: string[];
  recommendations_business: string[];
  business_report: Record<string, string | string[]>;
  technical_report: Record<string, string | string[]>;
  files: FileMetric[];
  entity_summary: Record<string, number>;
  entity_hotspots: string[];
  improvement_plan: ImprovementItem[];
  suggested_refactorings?: string[];
  entities: EntityMetric[];
  agent_manifest?: AgentManifest;
  metric_suite?: MetricSuite;
}
