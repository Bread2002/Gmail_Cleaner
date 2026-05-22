import { apiClient } from "./client";
import type { UserSettings } from "../types";

export const settingsApi = {
  get: () => apiClient.get<UserSettings>("/settings").then((r) => r.data),

  patch: (patch: Partial<UserSettings>) =>
    apiClient.patch<UserSettings>("/settings", patch).then((r) => r.data),
};
