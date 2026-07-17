import { apiFetch } from "./client";

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
  pipe_age_years?: number;
  diameter?: number;
  diameter_mm?: number;
  length?: number;
  length_m?: number;
  previous_failures?: number;
  days_since_last_maintenance?: number;
  complaints_last_30_days?: number;
  leakage_complaints_last_30_days?: number;
  leakage_complaints_30d?: number;
  failure_probability?: number;
  [key: string]: unknown;
}

export interface PipelineStats {
  total_pipelines: number;
  high_risk: number;
  medium_risk: number;
  low_risk: number;
  average_risk_score: number;
  risk_distribution?: Record<string, number>;
  [key: string]: unknown;
}

export async function fetchPipelines(riskLevel?: RiskLevel): Promise<PipelineListItem[]> {
  const qs = riskLevel ? `?risk_level=${riskLevel}` : "";
  return apiFetch<PipelineListItem[]>(`/api/v1/pipelines${qs}`, undefined, true);
}

export async function fetchPipelineDetail(id: string): Promise<PipelineDetail> {
  const d = await apiFetch<any>(`/api/v1/pipelines/${encodeURIComponent(id)}`, undefined, true);
  return {
    ...d,
    pipe_age: d.pipe_age ?? d.pipe_age_years,
    diameter: d.diameter ?? d.diameter_mm,
    length: d.length ?? d.length_m,
    leakage_complaints_last_30_days: d.leakage_complaints_last_30_days ?? d.leakage_complaints_30d,
  };
}

export async function fetchPipelineStats(): Promise<PipelineStats> {
  const raw = await apiFetch<any>(`/api/v1/pipelines/stats/summary`, undefined, true);
  return {
    ...raw,
    high_risk: raw.high_risk ?? raw.risk_distribution?.HIGH ?? 0,
    medium_risk: raw.medium_risk ?? raw.risk_distribution?.MEDIUM ?? 0,
    low_risk: raw.low_risk ?? raw.risk_distribution?.LOW ?? 0,
  };
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
