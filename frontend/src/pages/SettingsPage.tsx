// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: The main entry point for the settings page.
//              Users can customize how the scanning process identifies senders for cleanup, such as adjusting thresholds and toggling dry run mode.

// Import necessary modules and components
import { useSettings } from "../hooks/useSettings";

// Define the SettingsPage component that renders the settings interface for the Gmail Cleaner application
export function SettingsPage() {
  const { settings, update, loading, error } = useSettings();

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 text-sm mt-1">
          Customize how Gmail Cleaner scans your inbox
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm divide-y divide-gray-100">
        {/* Consecutive unread threshold */}
        <div className="p-5 space-y-3">
          <div className="flex justify-between items-center">
            <div>
              <p className="font-medium text-gray-800">
                Consecutive Unread Threshold
              </p>
              <p className="text-xs text-gray-500">
                Flag senders who have this many unread in a row
              </p>
            </div>
            <span className="text-lg font-bold text-blue-600 w-10 text-right">
              {settings.consecutive_unread_threshold}
            </span>
          </div>
          <input
            type="range"
            min={5}
            max={100}
            step={5}
            value={settings.consecutive_unread_threshold}
            onChange={(e) =>
              update({ consecutive_unread_threshold: Number(e.target.value) })
            }
            className="w-full accent-blue-600"
          />
          <div className="flex justify-between text-xs text-gray-400">
            <span>5 (aggressive)</span>
            <span>100 (lenient)</span>
          </div>
        </div>

        {/* Max senders */}
        <div className="p-5 space-y-3">
          <div className="flex justify-between items-center">
            <div>
              <p className="font-medium text-gray-800">Max Senders per Scan</p>
              <p className="text-xs text-gray-500">
                Stop after finding this many flagged senders
              </p>
            </div>
            <span className="text-lg font-bold text-blue-600 w-10 text-right">
              {settings.max_senders}
            </span>
          </div>
          <input
            type="range"
            min={1}
            max={50}
            step={1}
            value={settings.max_senders}
            onChange={(e) => update({ max_senders: Number(e.target.value) })}
            className="w-full accent-blue-600"
          />
          <div className="flex justify-between text-xs text-gray-400">
            <span>1</span>
            <span>50</span>
          </div>
        </div>

        {/* Max messages per sender */}
        <div className="p-5 space-y-3">
          <div className="flex justify-between items-center">
            <div>
              <p className="font-medium text-gray-800">
                Messages Inspected per Sender
              </p>
              <p className="text-xs text-gray-500">
                How many of each sender's messages to check for consecutive
                unread
              </p>
            </div>
            <span className="text-lg font-bold text-blue-600 w-12 text-right">
              {settings.max_messages_per_sender}
            </span>
          </div>
          <input
            type="range"
            min={20}
            max={500}
            step={20}
            value={settings.max_messages_per_sender}
            onChange={(e) =>
              update({ max_messages_per_sender: Number(e.target.value) })
            }
            className="w-full accent-blue-600"
          />
          <div className="flex justify-between text-xs text-gray-400">
            <span>20 (fast)</span>
            <span>500 (thorough)</span>
          </div>
        </div>

        {/* Dry run toggle */}
        <div className="p-5">
          <div className="flex items-start gap-4">
            <div className="relative mt-0.5">
              <input
                id="dry-run-toggle"
                type="checkbox"
                checked={settings.dry_run_by_default}
                onChange={(e) =>
                  update({ dry_run_by_default: e.target.checked })
                }
                className="sr-only"
              />
              <label
                htmlFor="dry-run-toggle"
                className={`block w-10 h-6 rounded-full transition-colors cursor-pointer ${
                  settings.dry_run_by_default ? "bg-amber-400" : "bg-gray-200"
                }`}
              >
                <div
                  className={`w-4 h-4 bg-white rounded-full shadow absolute top-1 transition-transform ${
                    settings.dry_run_by_default
                      ? "translate-x-5"
                      : "translate-x-1"
                  }`}
                />
              </label>
            </div>
            <div>
              <p className="font-medium text-gray-800">
                Dry Run Mode
                {settings.dry_run_by_default && (
                  <span className="ml-2 text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
                    ON
                  </span>
                )}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">
                When enabled, scans show what <em>would</em> be deleted without
                actually making changes. Great for previewing before committing.
              </p>
            </div>
          </div>
        </div>
      </div>

      <p className="text-xs text-center text-gray-400">
        Settings are saved automatically. Changes apply on the next scan.
      </p>
    </div>
  );
}
