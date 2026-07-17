import type {
  ComplaintDetail,
  CreateComplaintRequest,
  CreateComplaintResponse,
} from "@/types/complaint";
import { API_BASE_URL, apiFetch, ApiError } from "./client";

/**
 * Feature-level API service for complaints.
 *
 * Two implementations live behind the same interface:
 *   - realComplaintsApi  → hits the FastAPI backend when NEXT_PUBLIC_API_BASE_URL
 *     (or VITE_API_BASE_URL) is configured.
 *   - mockComplaintsApi  → in-memory simulator used for the current prototype.
 *
 * Components should ONLY import `complaintsApi`. Swapping to the real backend
 * is a one-line change here.
 */

export interface ComplaintsApi {
  create(input: CreateComplaintRequest): Promise<CreateComplaintResponse>;
  getByReference(referenceId: string): Promise<ComplaintDetail>;
}

// ---------- Real API (future) ----------------------------------------------

export const realComplaintsApi: ComplaintsApi = {
  create: (input) => {
    const formData = new FormData();
    formData.append("citizen_name", input.citizen_name);
    formData.append("phone_number", input.phone_number);
    formData.append("issue_type", input.issue_type);
    formData.append("description", input.description);
    if (input.latitude != null) formData.append("latitude", String(input.latitude));
    if (input.longitude != null) formData.append("longitude", String(input.longitude));
    if (input.address) formData.append("address", input.address);
    if (input.photo) formData.append("photo", input.photo);

    return apiFetch<CreateComplaintResponse>("/api/v1/complaints", {
      method: "POST",
      body: formData,
    });
  },
  getByReference: (referenceId) =>
    apiFetch<ComplaintDetail>(
      `/api/v1/complaints/${encodeURIComponent(referenceId)}`,
    ),
};

// ---------- Mock API (prototype) -------------------------------------------

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

const mockImages: Record<string, string> = {};
let counter = 1;
function nextReference(): string {
  const year = new Date().getFullYear();
  const padded = String(counter++).padStart(4, "0");
  return `AQS-${year}-${padded}`;
}

const sampleTimeline = (referenceId: string): ComplaintDetail => ({
  reference_id: referenceId,
  issue_type: "water_leakage",
  description:
    "Water leaking continuously near the main road junction, causing water logging.",
  address: "Sample address, Ward 12",
  current_status: "assigned",
  timeline: [
    {
      status: "submitted",
      label: "Submitted",
      timestamp: "2026-07-14T09:12:00Z",
      note: "Complaint received via citizen portal.",
    },
    {
      status: "reviewed",
      label: "Reviewed",
      timestamp: "2026-07-14T11:40:00Z",
      note: "Verified by municipal control room.",
    },
    {
      status: "assigned",
      label: "Assigned",
      timestamp: "2026-07-15T08:05:00Z",
      note: "Assigned to Zone-3 maintenance crew.",
    },
    {
      status: "resolved",
      label: "Resolved",
      timestamp: null,
    },
  ],
});

export const mockComplaintsApi: ComplaintsApi = {
  async create(input) {
    await wait(700);
    if (!input.citizen_name?.trim()) {
      throw new ApiError("Full name is required", 400);
    }
    if (!input.phone_number?.trim()) {
      throw new ApiError("Mobile number is required", 400);
    }
    if (!input.description?.trim()) {
      throw new ApiError("Description is required", 400);
    }

    const reference_id = nextReference();
    if (input.photo) {
      mockImages[reference_id] = URL.createObjectURL(input.photo);
    }
    return {
      reference_id,
      created_at: new Date().toISOString(),
    };
  },
  async getByReference(referenceId) {
    await wait(500);
    const normalized = referenceId.trim().toUpperCase();
    if (!/^AQS-\d{4}-\d{3,}$/.test(normalized)) {
      throw new ApiError("Invalid complaint reference", 404);
    }
    const base = sampleTimeline(normalized);
    return {
      ...base,
      image_url: mockImages[normalized] ?? null,
    };
  },
};

// ---------- Export the active implementation --------------------------------

const useReal = Boolean(API_BASE_URL);
export const complaintsApi: ComplaintsApi = useReal
  ? realComplaintsApi
  : mockComplaintsApi;
