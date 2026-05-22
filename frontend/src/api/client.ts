import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

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

/**
 * Build an SSE URL with the session token as a query param.
 *
 * SSE connects DIRECTLY to the backend (not through the Vite dev proxy) because
 * http-proxy buffers responses and EventSource events stop arriving in real time.
 * VITE_SSE_BASE_URL defaults to http://localhost:8000 for local dev.
 * CORS is already configured on the backend to allow the frontend origin.
 */
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
