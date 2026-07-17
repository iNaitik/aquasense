export type IssueType =
  | "water_leakage"
  | "low_pressure"
  | "discolored_water"
  | "unusual_flow"
  | "other";

export const ISSUE_TYPE_LABELS: Record<IssueType, string> = {
  water_leakage: "Water Leakage",
  low_pressure: "Low Water Pressure",
  discolored_water: "Discolored Water",
  unusual_flow: "Unusual Water Flow",
  other: "Other Pipeline Issue",
};

export interface ComplaintLocation {
  latitude: number | null;
  longitude: number | null;
  address: string;
}

export interface CreateComplaintRequest {
  citizen_name: string;
  phone_number: string;
  issue_type: IssueType;
  description: string;
  latitude: number | null;
  longitude: number | null;
  address?: string;
  photo?: File | null;
}

export interface CreateComplaintResponse {
  reference_id: string;
  created_at: string;
}

export type ComplaintStatus = "submitted" | "reviewed" | "assigned" | "resolved";

export interface ComplaintStatusEvent {
  status: ComplaintStatus;
  label: string;
  timestamp: string | null;
  note?: string;
}

export interface ComplaintDetail {
  reference_id: string;
  issue_type: IssueType;
  description: string;
  address?: string;
  image_url?: string | null;
  current_status: ComplaintStatus;
  timeline: ComplaintStatusEvent[];
}
