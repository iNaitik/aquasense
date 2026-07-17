/**
 * Thin fetch client. Kept intentionally minimal so it can be swapped for
 * a generated client (openapi-fetch, orval, etc.) later without touching
 * feature code.
 */

const viteBase = (import.meta as unknown as { env?: Record<string, string> }).env
  ?.VITE_API_BASE_URL;
const nodeBase =
  typeof process !== "undefined" ? process.env?.NEXT_PUBLIC_API_BASE_URL : undefined;
export const API_BASE_URL: string = viteBase ?? nodeBase ?? "";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

import { getAuthToken, clearAuthToken } from "@/lib/auth-storage";

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
  requiresAuth = false,
): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const token = requiresAuth ? getAuthToken() : null;

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      /* ignore */
    }

    if (res.status === 401 && requiresAuth) {
      clearAuthToken();
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/authority/login")) {
        window.location.href = "/authority/login";
      }
    }

    let errorMsg = `Request failed: ${res.status}`;
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail?: unknown }).detail;
      if (typeof detail === "string") {
        errorMsg = detail;
      } else if (Array.isArray(detail)) {
        errorMsg = detail
          .map((d) => (typeof d === "object" && d && "msg" in d ? String(d.msg).replace(/^Value error,\s*/i, "") : JSON.stringify(d)))
          .join("; ");
      } else {
        errorMsg = JSON.stringify(detail);
      }
    }

    throw new ApiError(errorMsg, res.status, body);
  }

  return (await res.json()) as T;
}
