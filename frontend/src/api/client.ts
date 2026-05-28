// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 26th, 2026
// Description: API module for client configuration and utilities in the Gmail Cleaner frontend application.

// Import necessary modules and components
import axios from "axios"; // Axios is used for making HTTP requests to the backend API

// Define the base URL for the API (defaults to "/api" for relative paths)
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

// Create an Axios instance with the base URL and default headers
export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach session token from localStorage to every request
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("session_token");
  if (token) {
    config.headers["Authorization"] = `Bearer ${token}`;
  }
  return config;
});

// On 401, clear the session and redirect to login
apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("session_token");
      localStorage.removeItem("user_email");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  },
);

// Define a helper function to construct Server-Sent Events (SSE) URLs with the session token
export function sseUrl(path: string): string {
  const token = localStorage.getItem("session_token") ?? "";
  // Prefer explicit SSE base, then fall back to API base, then direct backend
  const base =
    import.meta.env.VITE_SSE_BASE_URL ??
    (import.meta.env.VITE_API_BASE_URL?.startsWith("http")
      ? import.meta.env.VITE_API_BASE_URL
      : "http://localhost:8000");
  return `${base}${path}?token=${encodeURIComponent(token)}`;
}
