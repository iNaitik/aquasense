import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { authApi, type AuthorityProfile } from "@/lib/api/auth";
import { getAuthToken, setAuthToken, clearAuthToken } from "@/lib/auth-storage";

interface AuthContextType {
  authority: AuthorityProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<AuthorityProfile>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [authority, setAuthority] = useState<AuthorityProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const restoreSession = useCallback(async () => {
    const token = getAuthToken();
    if (!token) {
      setAuthority(null);
      setIsLoading(false);
      return;
    }
    try {
      const profile = await authApi.getCurrent();
      setAuthority(profile);
    } catch {
      // Token is invalid or expired
      clearAuthToken();
      setAuthority(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login(email, password);
    setAuthToken(res.access_token);
    setAuthority(res.authority);
    return res.authority;
  }, []);

  const logout = useCallback(() => {
    clearAuthToken();
    setAuthority(null);
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/authority/login")) {
      window.location.href = "/authority/login";
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        authority,
        isAuthenticated: !!authority,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
