/**
 * Utility for persisting and managing the authority JSON Web Token (JWT).
 *
 * NOTE: For this prototype, localStorage is used to persist the JWT so authority
 * officers do not get logged out on page refresh. In production systems, evaluate
 * more secure cookie-based authentication (HttpOnly, Secure, SameSite cookies)
 * to mitigate XSS risks and ensure secure storage.
 */

const TOKEN_KEY = "aquasense_authority_jwt";

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* ignore storage quota or private window errors */
  }
}

export function clearAuthToken(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}
