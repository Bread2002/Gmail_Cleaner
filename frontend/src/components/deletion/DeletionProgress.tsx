// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: React component for displaying the progress of email deletion in the Gmail Cleaner application.

// Import necessary modules and types
import type { DeletionPhase } from "../../hooks/useDeletion";
import type { TrashProgressEvent, TrashCompleteEvent } from "../../types";
import { fmtNumber } from "../../utils/formatters";

// Define the Props interface for the DeletionProgress component
interface Props {
  phase: DeletionPhase;
  progress: TrashProgressEvent | null;
  result: TrashCompleteEvent | null;
  dryRun: boolean;
}

// Define the DeletionProgress component that displays the progress of email deletion based on the current phase and progress data
export function DeletionProgress({ phase, progress, result, dryRun }: Props) {
  if (phase === "idle") return null;

  if (phase === "done" && result) {
    return (
      <div
        className={`text-sm rounded-lg px-3 py-2 font-medium ${
          dryRun
            ? "bg-amber-50 text-amber-700 border border-amber-200"
            : "bg-green-50 text-green-700 border border-green-200"
        }`}
      >
        {dryRun
          ? `🧪 Would trash ${fmtNumber(result.trashed_count)}+ emails...`
          : `✅ Trashed ${fmtNumber(result.trashed_count)}+ emails...`}
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="text-sm rounded-lg px-3 py-2 bg-red-50 text-red-700 border border-red-200">
        ❌ Deletion failed...
      </div>
    );
  }

  // starting or deleting
  const pct =
    progress && progress.total > 0
      ? Math.round((progress.trashed / progress.total) * 100)
      : 0;

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-500">
        <span>{progress?.message ?? "Deleting…"}</span>
        {progress && (
          <span>
            {fmtNumber(progress.trashed)} / {fmtNumber(progress.total)}
          </span>
        )}
      </div>
      <div className="w-full bg-gray-100 rounded-full h-1.5">
        <div
          className="bg-red-500 h-1.5 rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
