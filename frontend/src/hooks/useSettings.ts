import { useState, useEffect, useCallback, useRef } from "react";
import { settingsApi } from "../api/settings";
import type { UserSettings } from "../types";

const DEFAULTS: UserSettings = {
  consecutive_unread_threshold: 20,
  max_senders: 10,
  max_messages_per_sender: 100,
  dry_run_by_default: false,
};

export function useSettings() {
  const [settings, setSettings] = useState<UserSettings>(DEFAULTS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    settingsApi
      .get()
      .then(setSettings)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

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
