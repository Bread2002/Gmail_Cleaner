// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: Action buttons for sender management, including trashing emails and blocking senders.

// Import necessary modules and components
import { useState } from "react";
import { sendersApi } from "../../api/senders";
import type { DeletionPhase } from "../../hooks/useDeletion";

// Define the props for the ActionButtons component
interface Props {
  senderId: string;
  phase: DeletionPhase;
  dryRun: boolean;
  blocked: boolean;
  onTrash: () => void;
  onSkip: () => void;
  onBlockComplete: () => void;
}

// Define the ActionButtons component that renders action buttons for managing senders
export function ActionButtons({
  senderId,
  phase,
  dryRun,
  blocked,
  onTrash,
  onSkip,
  onBlockComplete,
}: Props) {
  const [blocking, setBlocking] = useState(false);

  const handleBlock = async () => {
    if (dryRun) {
      onBlockComplete();
      return;
    }
    setBlocking(true);
    try {
      await sendersApi.block(senderId);
      onBlockComplete();
    } catch {
      // Show error inline if needed
    } finally {
      setBlocking(false);
    }
  };

  const isActive = phase === "starting" || phase === "deleting";

  if (phase === "done") {
    return (
      <div className="flex gap-2 flex-wrap mt-2">
        {!blocked ? (
          <>
            <button
              onClick={handleBlock}
              disabled={blocking}
              className="text-xs bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 px-3 py-1.5 rounded-md transition-colors disabled:opacity-50"
            >
              {blocking
                ? "Blocking…"
                : dryRun
                  ? "🚫 Would Block"
                  : "🚫 Block Sender"}
            </button>
            <button
              onClick={onSkip}
              className="text-xs bg-gray-50 hover:bg-gray-100 text-gray-500 border border-gray-200 px-3 py-1.5 rounded-md transition-colors"
            >
              ⏭ Skip
            </button>
          </>
        ) : (
          <span className="text-xs text-red-600 font-medium px-3 py-1.5">
            {dryRun ? "🧪 Would be Blocked" : "🚫 Blocked"}
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="flex gap-2 flex-wrap">
      <button
        onClick={onTrash}
        disabled={isActive}
        className={`text-xs px-3 py-1.5 rounded-md font-medium transition-colors
          ${
            dryRun
              ? "bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200"
              : "bg-red-50 hover:bg-red-100 text-red-700 border border-red-200"
          } disabled:opacity-40 disabled:cursor-not-allowed`}
      >
        {dryRun ? "🧪 Preview Trash" : "🗑️ Trash All"}
      </button>

      <button
        onClick={handleBlock}
        disabled={isActive || blocking}
        className="text-xs bg-orange-50 hover:bg-orange-100 text-orange-700 border border-orange-200 px-3 py-1.5 rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {blocking
          ? "Blocking…"
          : blocked
            ? "✅ Blocked"
            : dryRun
              ? "🧪 Preview Block"
              : "🚫 Block Sender"}
      </button>

      <button
        onClick={onSkip}
        disabled={isActive}
        className="text-xs bg-gray-50 hover:bg-gray-100 text-gray-500 border border-gray-200 px-3 py-1.5 rounded-md transition-colors disabled:opacity-40"
      >
        ⏭ Skip
      </button>
    </div>
  );
}
