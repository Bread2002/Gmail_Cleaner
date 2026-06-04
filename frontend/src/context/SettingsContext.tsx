// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: June 4th, 2026
// Description: Shared context for user settings so all components read from a single source of truth.

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
} from "react";
import type { ReactNode } from "react";
import { settingsApi } from "../api/settings";
import type { UserSettings } from "../types";

export const DEFAULTS: UserSettings = {
  consecutive_unread_threshold: 20,
  max_senders: 10,
  max_messages_per_sender: 100,
  dry_run_by_default: false,
};

interface SettingsContextValue {
  settings: UserSettings;
  update: (patch: Partial<UserSettings>) => void;
  loading: boolean;
  error: string | null;
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
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
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      settingsApi.patch(patch).catch((e) => setError(e.message));
    }, 500);
  }, []);

  return (
    <SettingsContext.Provider value={{ settings, update, loading, error }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettingsContext(): SettingsContextValue {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error("useSettings must be used within SettingsProvider");
  return ctx;
}
