// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: Action buttons for sender management. Provides "Move to Trash" (recoverable),
//              "Delete Forever" (two-click confirm, permanent), "Block Sender", and "Skip".

// Import necessary modules and components
import { useState, useRef, useEffect } from "react";
import { sendersApi } from "../../api/senders";
import type { DeletionPhase } from "../../hooks/useDeletion";

// Define the props for the ActionButtons component
interface Props {
  senderId: string;
  phase: DeletionPhase;
  dryRun: boolean;
  blocked: boolean;
  onMoveToTrash: () => void;
  onDeleteForever: () => void;
  onSkip: () => void;
  onBlockComplete: () => void;
}

// Define the ActionButtons component that renders action buttons for managing senders
export function ActionButtons({
  senderId,
  phase,
  dryRun,
  blocked,
  onMoveToTrash,
  onDeleteForever,
  onSkip,
  onBlockComplete,
}: Props) {
  const [blocking, setBlocking] = useState(false);
  // Two-click confirm state for "Delete Forever"
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const confirmTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auto-reset the confirm state after 3 seconds if the user doesn't click again
  useEffect(() => {
    return () => {
      if (confirmTimerRef.current) clearTimeout(confirmTimerRef.current);
    };
  }, []);

  const handleDeleteClick = () => {
    if (dryRun) {
      onDeleteForever();
      return;
    }
    if (!deleteConfirm) {
      setDeleteConfirm(true);
      confirmTimerRef.current = setTimeout(() => setDeleteConfirm(false), 3000);
    } else {
      clearTimeout(confirmTimerRef.current!);
      setDeleteConfirm(false);
      onDeleteForever();
    }
  };

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
              style={{ cursor: "pointer" }}
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
              style={{ cursor: "pointer" }}
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
      {/* Move to Trash — single click, recoverable via Gmail for 30 days */}
      <button
        onClick={onMoveToTrash}
        disabled={isActive}
        className={`text-xs px-3 py-1.5 rounded-md font-medium transition-colors
          ${
            dryRun
              ? "bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200"
              : "bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200"
          } disabled:opacity-40 disabled:cursor-not-allowed`}
        style={{ cursor: "pointer" }}
      >
        {dryRun ? "🧪 Preview Trash" : "🗑️ Move to Trash"}
      </button>

      {/* Delete Forever — two-click confirm on first click to prevent accidents */}
      <button
        onClick={handleDeleteClick}
        disabled={isActive}
        className={`text-xs px-3 py-1.5 rounded-md font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed
          ${
            dryRun
              ? "bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200"
              : deleteConfirm
                ? "bg-red-600 hover:bg-red-700 text-white border border-red-600 animate-pulse"
                : "bg-red-50 hover:bg-red-100 text-red-700 border border-red-200"
          }`}
        style={{ cursor: "pointer" }}
      >
        {dryRun
          ? "🧪 Preview Delete"
          : deleteConfirm
            ? "⚠️ Confirm Delete?"
            : "✕ Delete Forever"}
      </button>

      <button
        onClick={handleBlock}
        disabled={isActive || blocking}
        className="text-xs bg-orange-50 hover:bg-orange-100 text-orange-700 border border-orange-200 px-3 py-1.5 rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        style={{ cursor: "pointer" }}
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
        style={{ cursor: "pointer" }}
      >
        ⏭ Skip
      </button>
    </div>
  );
}
