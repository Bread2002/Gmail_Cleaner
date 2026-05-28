// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: React component for displaying a summary of the email scanning results in the Gmail Cleaner application.

// Import necessary modules and hooks
import { useState, useEffect } from "react";

// Define the Props interface for the ScanSummary component
interface Props {
  totalFound: number;
  dryRun: boolean;
}

// Define the ScanSummary component that displays a summary of the email scanning results
export function ScanSummary({ totalFound, dryRun }: Props) {
  const [visible, setVisible] = useState(true);

  // Auto-hide the "found N senders" banner after 10 s.
  // The "clean inbox" variant stays visible indefinitely.
  useEffect(() => {
    if (totalFound === 0) return;
    const timer = setTimeout(() => setVisible(false), 10_000);
    return () => clearTimeout(timer);
  }, [totalFound]);

  if (totalFound === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <p className="text-5xl mb-3">✅</p>
        <p className="text-lg font-medium text-gray-600">
          Your inbox looks clean!
        </p>
        <p className="text-sm mt-1">
          No senders with excessive unread emails were found.
        </p>
      </div>
    );
  }

  if (!visible) return null;

  return (
    <div
      className={`rounded-xl px-4 py-3 text-sm font-medium flex items-center gap-2 ${
        dryRun
          ? "bg-amber-50 border border-amber-200 text-amber-800"
          : "bg-green-50 border border-green-200 text-green-800"
      }`}
    >
      <span>{dryRun ? "🧪" : "✅"}</span>
      <span>
        Found <strong>{totalFound}</strong> flagged sender
        {totalFound !== 1 ? "s" : ""}.
        {dryRun
          ? " (Dry run — no changes made)"
          : " Review and take action below."}
      </span>
    </div>
  );
}
