// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: React component for the scan button in the Gmail Cleaner application.

// Import necessary modules and components
import type { ScanPhase } from "../../hooks/useScan";

// Define the props for the ScanButton component
interface Props {
  phase: ScanPhase;
  dryRun: boolean;
  onScan: () => void;
  onReset: () => void;
}

// Define the ScanButton component that renders a button for initiating a scan of the user's inbox
export function ScanButton({ phase, dryRun, onScan, onReset }: Props) {
  const isScanning = phase === "starting" || phase === "scanning";

  if (phase === "done" || phase === "error") {
    return (
      <div className="flex gap-3">
        <button
          onClick={onScan}
          className={`
            px-6 py-3 rounded-lg font-semibold text-white transition-all text-base
            ${
              isScanning
                ? "bg-blue-400 cursor-not-allowed"
                : dryRun
                  ? "bg-amber-500 hover:bg-amber-600"
                  : "bg-blue-600 hover:bg-blue-700 shadow-sm hover:shadow-md"
            }
          `}
          style={{ cursor: "pointer" }}
        >
          {dryRun ? "🧪 Scan Again (Dry Run)" : "🔍 Scan Again"}
        </button>
        <button
          onClick={onReset}
          className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-5 py-2.5 rounded-lg font-medium transition-colors"
          style={{ cursor: "pointer" }}
        >
          Clear Results
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={onScan}
      disabled={isScanning}
      className={`
      px-6 py-3 rounded-lg font-semibold text-white transition-all text-base
      ${isScanning ? "cursor-not-allowed" : "cursor-pointer"}
      ${
        dryRun
          ? "bg-amber-500 hover:bg-amber-600"
          : "bg-blue-600 hover:bg-blue-700 shadow-sm hover:shadow-md"
      }
    `}
    >
      {isScanning
        ? dryRun
          ? "🧪 Scanning..."
          : "🔍 Scanning..."
        : dryRun
          ? "🧪 Preview Scan (Dry Run)"
          : "🔍 Scan My Inbox"}
    </button>
  );
}
