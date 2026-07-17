import { API_BASE_URL, apiFetch } from "./client";

export type ComplaintStatus =
  | "submitted"
  | "reviewed"
  | "assigned"
  | "resolved";

export type IssueType =
  | "water_leakage"
  | "low_pressure"
  | "discolored_water"
  | "unusual_flow"
  | "other";

export interface ComplaintStatusEvent {
  status: ComplaintStatus;
  label?: string;
  timestamp: string | null;
  note?: string | null;
}

export interface AdminComplaintListItem {
  reference_id: string;
  issue_type: IssueType;
  description: string;
  latitude: number;
  longitude: number;
  address?: string | null;
  image_url?: string | null;
  current_status: ComplaintStatus;
  created_at: string;
  updated_at: string;
  citizen_name?: string | null;
  phone_number?: string | null;
}

export interface AdminComplaintListResponse {
  items: AdminComplaintListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminComplaintDetail extends AdminComplaintListItem {
  timeline?: ComplaintStatusEvent[];
  status_timeline?: ComplaintStatusEvent[];
  status_history?: ComplaintStatusEvent[];
  [key: string]: unknown;
}

export interface AdminComplaintStats {
  total_complaints: number;
  submitted: number;
  reviewed: number;
  assigned: number;
  resolved: number;
  open_complaints?: number;
  [key: string]: unknown;
}

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  return apiFetch<T>(path, init, true);
}

export interface ComplaintFilters {
  page?: number;
  page_size?: number;
  current_status?: ComplaintStatus | "all";
  issue_type?: IssueType | "all";
}

export function getComplaints(filters: ComplaintFilters = {}) {
  const params = new URLSearchParams();
  const page = filters.page ?? 1;
  const pageSize = filters.page_size ?? 20;
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  if (filters.current_status && filters.current_status !== "all") {
    params.set("current_status", filters.current_status);
  }
  if (filters.issue_type && filters.issue_type !== "all") {
    params.set("issue_type", filters.issue_type);
  }
  return request<AdminComplaintListResponse>(
    `/api/v1/admin/complaints?${params.toString()}`,
  );
}

export function getComplaintStats() {
  return request<AdminComplaintStats>(`/api/v1/admin/complaints/stats/summary`);
}

export function getComplaintByReference(referenceId: string) {
  return request<AdminComplaintDetail>(
    `/api/v1/admin/complaints/${encodeURIComponent(referenceId)}`,
  );
}

export function updateComplaintStatus(
  referenceId: string,
  status: ComplaintStatus,
) {
  return request<AdminComplaintDetail>(
    `/api/v1/admin/complaints/${encodeURIComponent(referenceId)}/status`,
    {
      method: "PATCH",
      body: JSON.stringify({ status }),
    },
  );
}

export const ISSUE_TYPE_LABELS: Record<IssueType, string> = {
  water_leakage: "Water Leakage",
  low_pressure: "Low Water Pressure",
  discolored_water: "Discolored Water",
  unusual_flow: "Unusual Water Flow",
  other: "Other Pipeline Issue",
};

export const STATUS_LABELS: Record<ComplaintStatus, string> = {
  submitted: "Submitted",
  reviewed: "Reviewed",
  assigned: "Assigned",
  resolved: "Resolved",
};

export const STATUS_ORDER: ComplaintStatus[] = [
  "submitted",
  "reviewed",
  "assigned",
  "resolved",
];

export function nextStatus(current: ComplaintStatus): ComplaintStatus | null {
  const idx = STATUS_ORDER.indexOf(current);
  if (idx < 0 || idx >= STATUS_ORDER.length - 1) return null;
  return STATUS_ORDER[idx + 1];
}

export function nextStatusLabel(current: ComplaintStatus): string {
  switch (current) {
    case "submitted":
      return "Mark as Reviewed";
    case "reviewed":
      return "Assign Complaint";
    case "assigned":
      return "Mark as Resolved";
    default:
      return "Resolved";
  }
}
