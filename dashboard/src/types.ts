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
}

export interface DeveloperGuide {
  introduction: string;
  how_to_read: string[];
  action_count: number;
  actions: DeveloperAction[];
}

export interface RepoDimension {
  id: string;
  name: string;
  score: number;
  band: string;
  weight: number;
  repo_aggregate: number;
  unit: string;
  summary_technical: string;
  summary_business: string;
  evidence: string[];
  evidence_symbols: string[];
  actions_in_repo: string[];
  top_contributors: Record<string, unknown>[];
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
  entities: EntityMetric[];
}
