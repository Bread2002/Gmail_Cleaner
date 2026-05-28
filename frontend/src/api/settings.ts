// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: API module for settings-related endpoints in the Gmail Cleaner application.

// Import necessary modules and components
import { apiClient } from "./client";
import type { UserSettings } from "../types";

// Define the settingsApi object that contains methods for settings-related API calls
export const settingsApi = {
  // Method to retrieve the current user settings
  get: () => apiClient.get<UserSettings>("/settings").then((r) => r.data),

  // Method to update user settings with a partial patch object
  patch: (patch: Partial<UserSettings>) =>
    apiClient.patch<UserSettings>("/settings", patch).then((r) => r.data),
};
