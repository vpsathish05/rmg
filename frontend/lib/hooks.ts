import { useQuery } from "@tanstack/react-query";
import api from "./api";

export interface EmployeeAllocationDetail {
  project_id: string;
  client_id: string | null;
  allocation_pct: number | null;
  resourcing_status: string | null;
  start_date: string | null;
  end_date: string | null;
  is_open_ended: boolean;
  days_remaining: number | null;
}

export interface EmployeeAvailability {
  employee_id: string;
  job_name: string | null;
  canonical_role: string | null;
  department_name: string | null;
  location: string | null;
  allocated_pct: number;
  available_pct: number;
  allocation_status: string;
  billability: string | null;       // BILLABLE / SHADOW / UNBILLED
  nearest_end_date: string | null;
}

export interface ProjectHealth {
  project_id: string;
  client_id: string;
  project_status: string | null;
  proposition_coe: string | null;
  project_start_date: string | null;
  project_end_date: string | null;
  scope_status: string | null;
  schedule_status: string | null;
  quality_status: string | null;
  csat_status: string | null;
  team_status: string | null;
  overall_health: string;
  week_end: string | null;
}

export interface ProjectAlert {
  project_id: string;
  client_id: string;
  project_status: string | null;
  proposition_coe: string | null;
  project_end_date: string | null;
  days_overrun?: number;
  days_remaining?: number;
  headcount: number;
}

export interface DashboardSummary {
  total_employees: number;
  active_employees: number;
  on_bench: number;
  partially_available: number;
  fully_allocated: number;
  active_projects: number;
  red_projects: number;
  amber_projects: number;
  pipeline_requests: number;
  high_probability_pipeline: number;
}

export interface PipelineRequest {
  id: number;
  cluster: number | null;
  client_name: string | null;
  client_priority: string | null;
  deal_stage: string | null;
  solution: string | null;
  priority: string | null;
  status: string | null;
  sow_signed: boolean | null;
  probability_weight: number | null;
  role_code_raw: string | null;
  canonical_roles: string[] | null;
  allocation_pct: number | null;
  likely_start_date: string | null;
  duration_weeks: number | null;
  comments: string | null;
}

export interface OutlookMonth {
  month: string;
  total_fte: number;
  weighted_fte: number;
  roles: { role: string; request_count: number; total_fte: number; weighted_fte: number }[];
}

export function useDashboardSummary() {
  return useQuery<DashboardSummary>({
    queryKey: ["dashboard-summary"],
    queryFn: () => api.get("/api/dashboard/summary").then((r) => r.data),
  });
}

export function useAvailability(filters?: { status?: string; department?: string }) {
  const params = new URLSearchParams();
  if (filters?.status) params.set("status", filters.status);
  if (filters?.department) params.set("department", filters.department);
  return useQuery<EmployeeAvailability[]>({
    queryKey: ["availability", filters],
    queryFn: () => api.get(`/api/employees?${params}`).then((r) => r.data),
  });
}

export function useEmployeeAllocations(employeeId: string | null) {
  return useQuery<EmployeeAllocationDetail[]>({
    queryKey: ["employee-allocations", employeeId],
    queryFn: () => api.get(`/api/employees/${employeeId}/allocations`).then((r) => r.data),
    enabled: !!employeeId,
  });
}

export function useProjectHealth(filters?: { health?: string }) {
  const params = new URLSearchParams();
  if (filters?.health) params.set("health", filters.health);
  return useQuery<ProjectHealth[]>({
    queryKey: ["project-health", filters],
    queryFn: () => api.get(`/api/projects/health?${params}`).then((r) => r.data),
  });
}

export function useOverrunningProjects() {
  return useQuery<ProjectAlert[]>({
    queryKey: ["projects-overrunning"],
    queryFn: () => api.get("/api/projects/overrunning").then((r) => r.data),
  });
}

export function useRampDownProjects(days = 60) {
  return useQuery<ProjectAlert[]>({
    queryKey: ["projects-ramp-down", days],
    queryFn: () => api.get(`/api/projects/ramp-down?days=${days}`).then((r) => r.data),
  });
}

export function useForecast() {
  return useQuery<PipelineRequest[]>({
    queryKey: ["forecast"],
    queryFn: () => api.get("/api/forecast").then((r) => r.data),
  });
}

export function useForecastOutlook() {
  return useQuery<OutlookMonth[]>({
    queryKey: ["forecast-outlook"],
    queryFn: () => api.get("/api/forecast/outlook").then((r) => r.data),
  });
}

// ── RMG Engine ────────────────────────────────────────────────────────────────

export interface PipelineRole {
  id: number;
  role_code_raw: string | null;
  canonical_roles: string[] | null;
  allocation_pct: number | null;
  duration_weeks: number | null;
  required_skills: string | null;
  status: string | null;
  comments: string | null;
}

export interface PipelineProject {
  client_name: string;
  client_priority: string | null;
  deal_stage: string | null;
  solution: string | null;
  likely_start_date: string | null;
  probability_weight: number | null;
  sow_signed: boolean;
  em_name: string | null;
  role_count: number;
  roles: PipelineRole[];
}

export interface ExtensionProject {
  project_id: string;
  client_id: string;
  proposition_coe: string | null;
  project_end_date: string | null;
  max_alloc_end_date: string | null;
  days_extended: number;
  headcount: number;
  resourcing_statuses: string | null;
}

export interface EmailRequestItem {
  id: string;
  source_email: string | null;
  received_at: string | null;
  request_type: string | null;
  parsed_json: Record<string, unknown> | null;
  status: string | null;
}

export interface KbProof {
  project_id: string;
  client_id: string | null;
  coe: string | null;
  status: string | null;
  start_date: string | null;
  end_date: string | null;
  similarity: number;
}

export interface RmgCandidate {
  employee_id: string;
  job_name: string | null;
  canonical_role: string | null;
  location: string | null;
  department_name: string | null;
  current_allocated_pct: number;
  available_pct: number;
  category: string;
  total_score: number;
  skill_score: number;
  comp_score: number | null;
  avail_score: number;
  prod_score: number;
  has_competency: boolean;
  rationale: string | null;
  kb_proof: KbProof[];
}

export interface RoleRecommendResult {
  available: RmgCandidate[];
  best_match: RmgCandidate[];
  no_resource: boolean;
  hire_signal: string | null;
  kb_active: boolean;
  total_evaluated: number;
}

export function useRmgPipeline() {
  return useQuery<PipelineProject[]>({
    queryKey: ["rmg-pipeline"],
    queryFn: () => api.get("/api/rmg/pipeline").then((r) => r.data),
  });
}

export function useRmgExtensions() {
  return useQuery<{ allocation_extensions: ExtensionProject[]; email_extensions: EmailRequestItem[] }>({
    queryKey: ["rmg-extensions"],
    queryFn: () => api.get("/api/rmg/extensions").then((r) => r.data),
  });
}

export function useRmgEmailRequests() {
  return useQuery<EmailRequestItem[]>({
    queryKey: ["rmg-email-requests"],
    queryFn: () => api.get("/api/rmg/email-requests").then((r) => r.data),
  });
}

export function useKbStatus() {
  return useQuery<{ embeddings: number; kb_active: boolean }>({
    queryKey: ["kb-status"],
    queryFn: () => api.get("/api/rmg/kb/status").then((r) => r.data),
  });
}

export interface CachedRoleRecommendation {
  coe: string | null;
  available: RmgCandidate[];
  best_match: RmgCandidate[];
  no_resource: boolean;
  hire_signal: string | null;
  kb_active: boolean;
  total_evaluated: number;
  computed_at: string | null;
  status: string;
}

export interface RecCacheStatus {
  done_count: number;
  error_count: number;
  last_computed_at: string | null;
  is_running: boolean;
}

/** Returns all pre-computed role recommendations keyed by pipeline_role_id (as string). */
export function useRmgRecommendations() {
  return useQuery<Record<string, CachedRoleRecommendation>>({
    queryKey: ["rmg-recommendations"],
    queryFn: () => api.get("/api/rmg/recommendations").then((r) => r.data),
    staleTime: 5 * 60 * 1000, // treat as fresh for 5 min — it's nightly data
  });
}

export function useRecCacheStatus() {
  return useQuery<RecCacheStatus>({
    queryKey: ["rec-cache-status"],
    queryFn: () => api.get("/api/rmg/recommendations/status").then((r) => r.data),
    refetchInterval: (q) =>
      q.state.data?.is_running ? 10_000 : false, // poll every 10s while running
  });
}
