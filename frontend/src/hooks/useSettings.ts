// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: Contains the useSettings hook for accessing and updating user settings in the Gmail Cleaner application.

// Import necessary modules and components
import { useState, useEffect, useCallback, useRef } from "react";
import { settingsApi } from "../api/settings";
import type { UserSettings } from "../types";

// Define default settings values to use before the actual settings are loaded from the API
const DEFAULTS: UserSettings = {
  consecutive_unread_threshold: 20,
  max_senders: 10,
  max_messages_per_sender: 100,
  dry_run_by_default: false,
};

// Define the useSettings hook that manages user settings state, loading, and error handling
export function useSettings() {
  const [settings, setSettings] = useState<UserSettings>(DEFAULTS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Effect hook to load user settings from the API when the component mounts, and handle loading state and errors
  useEffect(() => {
    settingsApi
      .get()
      .then(setSettings)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  // Callback function to update user settings with a partial patch object
  const update = useCallback((patch: Partial<UserSettings>) => {
    setSettings((prev) => ({ ...prev, ...patch }));

    // Debounce the PATCH so we don't hammer the API on every slider tick
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      settingsApi.patch(patch).catch((e) => setError(e.message));
    }, 500);
  }, []);

  return { settings, update, loading, error };
}
