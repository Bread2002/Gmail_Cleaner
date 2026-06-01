// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: The main entry point for the login page.
//              Users can sign in with their Google account to start using the Gmail Cleaner application.

// Import necessary modules and components
import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Footer } from "../components/layout/Footer";

// Define the LoginPage component that renders the login interface for the Gmail Cleaner application
export function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const error = params.get("error");

  useEffect(() => {
    if (isAuthenticated) navigate("/", { replace: true });
  }, [isAuthenticated, navigate]);

  return (
    <div className="relative min-h-screen bg-gradient-to-br from-cyan-200 to-blue-400 flex flex-col">
      <div className="flex-1 flex items-center justify-center px-2 py-6">
        <div className="bg-white rounded-2xl shadow-xl p-5 sm:p-10 w-full max-w-md text-center space-y-6">
          {/* Logo */}
          <div className="flex flex-col items-center gap-2">
            <img
              src="/logo.png"
              alt="Gmail Cleaner"
              className="h-32 w-32 sm:h-60 sm:w-60 rounded-2xl object-contain shadow-md"
            />
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
              Gmail Cleaner
            </h1>
            <p className="text-gray-500 font-bold text-sm">
              Automatically find and remove unwanted email senders
            </p>
          </div>

          {/* Error banner */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
              Authentication failed. Please try again.
            </div>
          )}

          {/* Features */}
          <ul className="text-left text-sm text-gray-600 space-y-2">
            {[
              "🔍 Scan for senders with excessive unread emails",
              "🗑️ Batch-trash all emails from a sender",
              "✖️ Permanently delete all messages from a sender",
              "🚫 Block unwanted/ spam senders",
              "🧪 Dry-run mode to preview before deleting",
            ].map((feature) => (
              <li key={feature} className="flex items-start gap-2">
                <span>{feature}</span>
              </li>
            ))}
          </ul>

          {/* Sign in button */}
          <button
            onClick={login}
            className="w-full flex items-center justify-center gap-3 bg-white border-2 border-gray-200 hover:border-blue-400 hover:shadow-md rounded-xl px-5 py-3 text-gray-700 font-semibold transition-all"
          >
            <svg width="20" height="20" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Sign in with Google
          </button>

          <p className="text-xs text-gray-400">
            Only accesses your Gmail. No data is stored permanently.
          </p>
        </div>
      </div>
      <Footer />
    </div>
  );
}
