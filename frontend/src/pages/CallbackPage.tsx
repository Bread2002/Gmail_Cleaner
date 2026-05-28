// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: The main entry point for handling the OAuth callback after the user authenticates with Google.
//              It processes the authorization code, exchanges it for a session token, and logs the user in.
//              If any step fails, it redirects back to the login page with an error message.

// Import necessary modules and components
import { useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { authApi } from "../api/auth";
import { useAuth } from "../hooks/useAuth";

// Define the CallbackPage component that handles the OAuth callback logic
export function CallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { loginWithToken } = useAuth();
  const called = useRef(false); // prevent double-invoke in React StrictMode

  useEffect(() => {
    if (called.current) return;
    called.current = true;

    const code = params.get("code");
    const state = params.get("state");
    const error = params.get("error");

    if (error || !code || !state) {
      navigate("/login?error=auth_failed", { replace: true });
      return;
    }

    authApi
      .callback({ code, state })
      .then(({ session_token, user_email }) => {
        loginWithToken(session_token, user_email);
        navigate("/", { replace: true });
      })
      .catch(() => {
        navigate("/login?error=auth_failed", { replace: true });
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="min-h-screen bg-blue-50 flex items-center justify-center">
      <div className="text-center space-y-4">
        <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-gray-600 font-medium">Signing you in…</p>
      </div>
    </div>
  );
}
