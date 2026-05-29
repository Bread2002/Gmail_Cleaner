// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: The main entry point for the dashboard page.
//              Users can initiate scans of their Gmail inbox, view progress, and see results.

// Import necessary modules and components
import { useScan } from "../hooks/useScan";
import { useSettings } from "../hooks/useSettings";
import { ScanButton } from "../components/scan/ScanButton";
import { ScanProgress } from "../components/scan/ScanProgress";
import { ScanSummary } from "../components/scan/ScanSummary";
import { SenderList } from "../components/senders/SenderList";

// Define the DashboardPage component that renders the main dashboard interface for the Gmail Cleaner application
export function DashboardPage() {
  const { settings } = useSettings();
  const scan = useScan();

  const handleScan = () => {
    scan.startScan({
      dryRun: settings.dry_run_by_default,
      consecutiveUnreadThreshold: settings.consecutive_unread_threshold,
      maxSenders: settings.max_senders,
      maxMessagesPerSender: settings.max_messages_per_sender,
    });
  };

  return (
    <div className="space-y-6">
      {/* Hero */}
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold text-gray-900">
          Cleanse Your Inbox...
        </h1>
        <p className="text-gray-500 text-sm">
          Finds senders with{" "}
          <strong>{settings.consecutive_unread_threshold}+</strong> consecutive
          unread emails and lets you trash, delete, or block them.
        </p>
      </div>

      {/* Scan control */}
      <div className="flex flex-col items-center gap-4 w-full">
        <ScanButton
          phase={scan.phase}
          dryRun={settings.dry_run_by_default}
          onScan={handleScan}
          onReset={scan.reset}
        />
        <div className="w-full max-w-xl">
          <ScanProgress
            phase={scan.phase}
            progress={scan.progress}
            sendersFound={scan.senders.length}
            eventLog={scan.eventLog}
          />
        </div>
      </div>

      {/* Post-scan event log (collapsed summary when done) */}
      {scan.phase === "done" && scan.eventLog.length > 0 && (
        <details className="max-w-xl mx-auto">
          <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600">
            Show scan log ({scan.eventLog.length} events)
          </summary>
          <div className="mt-2 bg-gray-50 border border-gray-200 rounded-lg p-3 space-y-0.5 max-h-40 overflow-y-auto">
            {scan.eventLog.map((line, i) => (
              <p key={i} className="text-xs font-mono text-gray-600">
                {line}
              </p>
            ))}
          </div>
        </details>
      )}

      {/* Results */}
      {scan.phase === "done" && (
        <ScanSummary
          totalFound={scan.totalFound}
          dryRun={settings.dry_run_by_default}
        />
      )}

      {scan.phase === "error" && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          ❌ <strong>Scan failed:</strong> {scan.error}
        </div>
      )}

      {scan.senders.length > 0 && (
        <SenderList
          senders={scan.senders}
          dryRun={settings.dry_run_by_default}
        />
      )}
    </div>
  );
}
