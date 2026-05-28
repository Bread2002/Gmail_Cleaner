// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: Authentication context for managing user authentication state, including login, logout, and session persistence across the application.

// Import necessary modules and components
import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from "react";
import { authApi } from "../api/auth";

// Define the shape of the authentication state and context value
interface AuthState {
  sessionToken: string | null;
  userEmail: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// Define the shape of the authentication context value, which includes the authentication state and functions for login, logout, and token-based login
interface AuthContextValue extends AuthState {
  login: () => Promise<void>;
  loginWithToken: (token: string, email: string) => void;
  logout: () => Promise<void>;
}

// Create the authentication context with an initial value of null
const AuthContext = createContext<AuthContextValue | null>(null);

// Define the AuthProvider component that provides authentication state and functions to its children components
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    sessionToken: localStorage.getItem("session_token"),
    userEmail: localStorage.getItem("user_email"),
    isAuthenticated: !!localStorage.getItem("session_token"),
    isLoading: false,
  });

  // Verify session is still valid on mount
  useEffect(() => {
    if (state.sessionToken) {
      authApi.me().catch(() => {
        // Session expired — clear it
        localStorage.removeItem("session_token");
        localStorage.removeItem("user_email");
        setState((s) => ({
          ...s,
          sessionToken: null,
          userEmail: null,
          isAuthenticated: false,
        }));
      });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const login = useCallback(async () => {
    const { auth_url } = await authApi.getLoginUrl();
    window.location.href = auth_url;
  }, []);

  const loginWithToken = useCallback((token: string, email: string) => {
    localStorage.setItem("session_token", token);
    localStorage.setItem("user_email", email);
    setState({
      sessionToken: token,
      userEmail: email,
      isAuthenticated: true,
      isLoading: false,
    });
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Best-effort
    }
    localStorage.removeItem("session_token");
    localStorage.removeItem("user_email");
    setState({
      sessionToken: null,
      userEmail: null,
      isAuthenticated: false,
      isLoading: false,
    });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, loginWithToken, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
