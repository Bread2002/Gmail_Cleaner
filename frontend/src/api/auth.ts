import { apiClient } from "./client";
import type {
  LoginResponse,
  CallbackRequest,
  CallbackResponse,
  MeResponse,
} from "../types";

export const authApi = {
  getLoginUrl: () =>
    apiClient.get<LoginResponse>("/auth/login").then((r) => r.data),

  callback: (body: CallbackRequest) =>
    apiClient
      .post<CallbackResponse>("/auth/callback", body)
      .then((r) => r.data),

  logout: () => apiClient.post("/auth/logout").then(() => undefined),

  me: () => apiClient.get<MeResponse>("/auth/me").then((r) => r.data),
};
