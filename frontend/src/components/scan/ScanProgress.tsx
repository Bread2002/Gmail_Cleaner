// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: React component for displaying the progress of the email scanning process in the Gmail Cleaner application.

// Import necessary modules and types
import type { ScanPhase } from "../../hooks/useScan";
import type { ScanProgressEvent } from "../../types";

// Define the Props interface for the ScanProgress component
interface Props {
  phase: ScanPhase;
  progress: ScanProgressEvent | null;
  sendersFound: number;
  eventLog: string[];
}

// Define the ScanProgress component that displays the progress of the email scanning process
export function ScanProgress({
  phase,
  progress,
  sendersFound,
  eventLog,
}: Props) {
  if (phase === "idle") return null;
  if (phase === "done" || phase === "error") return null;

  const pct =
    progress?.total && progress.current
      ? Math.round((progress.current / progress.total) * 100)
      : null;

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 space-y-3 w-full">
      {/* Status row */}
      <div className="flex items-center gap-2">
        <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin flex-shrink-0" />
        <p className="text-sm font-medium text-blue-800 truncate">
          {phase === "starting"
            ? "Connecting to Gmail…"
            : (progress?.message ?? "Scanning…")}
        </p>
      </div>

      {/* Progress bar — determinate when total is known */}
      <div className="w-full bg-blue-100 rounded-full h-1.5 overflow-hidden">
        {pct !== null ? (
          <div
            className="h-full bg-blue-500 rounded-full transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        ) : (
          <div className="h-full bg-blue-400 rounded-full animate-pulse w-2/3" />
        )}
      </div>

      {/* Stats row */}
      <div className="flex items-center justify-between text-xs text-blue-600">
        {sendersFound > 0 && (
          <span className="font-semibold text-blue-700 bg-blue-100 px-2 py-0.5 rounded-full">
            {sendersFound} sender{sendersFound !== 1 ? "s" : ""} flagged
          </span>
        )}
      </div>

      {/* Live activity log — last 5 events */}
      {eventLog.length > 0 && (
        <div className="border-t border-blue-100 pt-2 space-y-0.5">
          {eventLog.slice(-5).map((line, i) => (
            <p
              key={i}
              className={`text-xs font-mono truncate ${
                i === eventLog.slice(-5).length - 1
                  ? "text-blue-700"
                  : "text-blue-400"
              }`}
            >
              {line}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
