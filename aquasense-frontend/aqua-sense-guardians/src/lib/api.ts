export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";

export interface PipelineListItem {
  pipeline_id: string;
  risk_score: number;
  risk_level: RiskLevel;
  start_latitude: number;
  start_longitude: number;
  end_latitude: number;
  end_longitude: number;
}

export interface PipelineDetail extends PipelineListItem {
  material?: string;
  pipe_age?: number;
  diameter?: number;
  length?: number;
  previous_failures?: number;
  days_since_last_maintenance?: number;
  complaints_last_30_days?: number;
  leakage_complaints_last_30_days?: number;
  failure_probability?: number;
  [key: string]: unknown;
}

export interface PipelineStats {
  total_pipelines: number;
  high_risk: number;
  medium_risk: number;
  low_risk: number;
  average_risk_score: number;
  [key: string]: unknown;
}

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ||
  "http://localhost:8000";

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Request failed (${res.status}): ${path}`);
  }
  return (await res.json()) as T;
}

export function fetchPipelines(riskLevel?: RiskLevel) {
  const qs = riskLevel ? `?risk_level=${riskLevel}` : "";
  return apiGet<PipelineListItem[]>(`/api/v1/pipelines${qs}`);
}

export function fetchPipelineDetail(id: string) {
  return apiGet<PipelineDetail>(`/api/v1/pipelines/${encodeURIComponent(id)}`);
}

export function fetchPipelineStats() {
  return apiGet<PipelineStats>(`/api/v1/pipelines/stats/summary`);
}

export function riskColor(level: RiskLevel): string {
  switch (level) {
    case "HIGH":
      return "#dc2626";
    case "MEDIUM":
      return "#f59e0b";
    case "LOW":
    default:
      return "#16a34a";
  }
}
