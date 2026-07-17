import { API_BASE_URL, apiFetch, ApiError } from "./client";
import { getAuthToken } from "@/lib/auth-storage";

export interface AuthorityProfile {
  id: number;
  name: string;
  email: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  authority: AuthorityProfile;
}

export interface AuthApi {
  login(email: string, password: string): Promise<LoginResponse>;
  getCurrent(): Promise<AuthorityProfile>;
}

// ---------- Real API -------------------------------------------------------

const realAuthApi: AuthApi = {
  login: (email, password) =>
    apiFetch<LoginResponse>("/api/v1/auth/authority/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  getCurrent: () =>
    apiFetch<AuthorityProfile>("/api/v1/auth/authority/me", undefined, true),
};

// ---------- Mock API (prototype demo mode) ---------------------------------

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

const mockProfile: AuthorityProfile = {
  id: 1,
  name: "Naitik Seth",
  email: "sethnaitikgg77@gmail.com",
};

const mockAuthApi: AuthApi = {
  async login(email, password) {
    await wait(600);
    const cleanEmail = email.trim().toLowerCase();
    if (cleanEmail !== "sethnaitikgg77@gmail.com" || password !== "1353") {
      throw new ApiError("Incorrect email or password.", 401);
    }
    return {
      access_token: "mock-jwt-token-aquasense-proto",
      token_type: "bearer",
      expires_in: 3600,
      authority: mockProfile,
    };
  },
  async getCurrent() {
    await wait(400);
    const token = getAuthToken();
    if (!token) {
      throw new ApiError("Not authenticated", 401);
    }
    return mockProfile;
  },
};

// ---------- Export active implementation -----------------------------------

const useReal = Boolean(API_BASE_URL);
export const authApi: AuthApi = useReal ? realAuthApi : mockAuthApi;
