// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: Bulk action bar for managing multiple senders at once. Provides "Move to Trash"
//              (recoverable), "Delete Forever" (two-click confirm), "Block Selected", and "Skip Selected".

// Import necessary modules and components
import { useState, useRef, useEffect } from "react";
import { sendersApi } from "../../api/senders";
import type { DeletionAction } from "../../hooks/useDeletion";

// Define the props for the BulkActionBar component
interface Props {
  selectedIds: string[];
  totalCount: number;
  dryRun: boolean;
  /**
   * IDs of senders whose emails have already been actioned (moved to trash or deleted).
   * The bulk action buttons are suppressed when every selected sender is in this set.
   */
  actionedIds: Set<string>;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  /** Called after bulk skip/block completes with the IDs that were successfully actioned. */
  onBulkComplete: (ids: string[]) => void;
  /**
   * Called when a real (non-dry-run) bulk action request returns job IDs.
   * Senders stay visible; each SenderCard monitors its own SSE stream and
   * self-dismisses when the job finishes.
   */
  onBulkActionStarted: (
    jobs: { sender_id: string; job_id: string }[],
    action: DeletionAction,
  ) => void;
}

// Define the BulkActionBar component that renders bulk action buttons for managing multiple senders
export function BulkActionBar({
  selectedIds,
  totalCount,
  dryRun,
  actionedIds,
  onSelectAll,
  onDeselectAll,
  onBulkComplete,
  onBulkActionStarted,
}: Props) {
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  // Two-click confirm state for "Delete Forever Selected"
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const confirmTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (confirmTimerRef.current) clearTimeout(confirmTimerRef.current);
    };
  }, []);

  if (totalCount === 0) return null;

  // Only operate on senders that haven't been actioned yet.
  const actionableIds = selectedIds.filter((id) => !actionedIds.has(id));
  const allSelectedActioned =
    selectedIds.length > 0 && actionableIds.length === 0;

  const handleBulkMoveToTrash = async () => {
    const ids = actionableIds;
    if (ids.length === 0) return;
    setLoading(true);
    setStatus(null);
    try {
      const { jobs } = await sendersApi.bulkMoveToTrash(ids, dryRun);
      if (dryRun) {
        setStatus(
          `🧪 Would move emails from ${jobs.length} sender(s) to the trash`,
        );
        onBulkComplete(jobs.map((j) => j.sender_id));
      } else {
        setStatus(`🗑️ Moving ${jobs.length} sender(s) to the trash…`);
        onBulkActionStarted(jobs, "moveToTrash");
      }
    } catch (e: any) {
      setStatus(`❌ ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleBulkDeleteClick = async () => {
    if (dryRun) {
      const ids = actionableIds;
      if (ids.length === 0) return;
      setLoading(true);
      setStatus(null);
      try {
        const { jobs } = await sendersApi.bulkDeleteForever(ids, dryRun);
        setStatus(
          `🧪 Would permanently delete emails from ${jobs.length} sender(s)`,
        );
        onBulkComplete(jobs.map((j) => j.sender_id));
      } catch (e: any) {
        setStatus(`❌ ${e.message}`);
      } finally {
        setLoading(false);
      }
      return;
    }

    if (!deleteConfirm) {
      setDeleteConfirm(true);
      confirmTimerRef.current = setTimeout(() => setDeleteConfirm(false), 3000);
      return;
    }

    // Second click — execute
    clearTimeout(confirmTimerRef.current!);
    setDeleteConfirm(false);

    const ids = actionableIds;
    if (ids.length === 0) return;
    setLoading(true);
    setStatus(null);
    try {
      const { jobs } = await sendersApi.bulkDeleteForever(ids, false);
      setStatus(`✕ Permanently deleting ${jobs.length} sender(s)…`);
      onBulkActionStarted(jobs, "deleteForever");
    } catch (e: any) {
      setStatus(`❌ ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleBulkBlock = async () => {
    const ids = [...selectedIds];
    if (ids.length === 0) return;
    setLoading(true);
    setStatus(null);
    try {
      const { blocked, failed } = await sendersApi.bulkBlock(ids);
      setStatus(
        dryRun
          ? `🧪 Would block ${ids.length} sender(s)`
          : `🚫 Blocked ${blocked.length} sender(s)${failed.length ? `, ${failed.length} failed` : ""}`,
      );
      onBulkComplete(ids);
    } catch (e: any) {
      setStatus(`❌ ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleBulkSkip = async () => {
    const ids = [...selectedIds];
    if (ids.length === 0) return;
    setLoading(true);
    setStatus(null);
    try {
      const { skipped, failed } = await sendersApi.bulkSkip(ids);
      setStatus(
        `⏭ Skipped ${skipped.length} sender(s)${failed.length ? `, ${failed.length} not found` : ""}`,
      );
      onBulkComplete(skipped);
    } catch (e: any) {
      setStatus(`❌ ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-3 flex flex-wrap items-center gap-3 shadow-sm">
      {/* Select controls */}
      <div className="flex items-center gap-2 text-sm text-gray-600">
        <button
          onClick={onSelectAll}
          className="text-blue-600 hover:underline text-xs"
          style={{ cursor: "pointer" }}
        >
          Select All
        </button>
        <span className="text-gray-300">|</span>
        <button
          onClick={onDeselectAll}
          className="text-gray-500 hover:underline text-xs"
          style={{ cursor: "pointer" }}
        >
          None
        </button>
        <span className="font-medium text-gray-800">
          {selectedIds.length} / {totalCount} selected
        </span>
      </div>

      <div className="flex gap-2 ml-auto flex-wrap">
        {/* Move to Trash — single click, recoverable via Gmail for 30 days */}
        <button
          onClick={handleBulkMoveToTrash}
          disabled={selectedIds.length === 0 || loading || allSelectedActioned}
          title={
            allSelectedActioned
              ? "All selected senders have already been actioned"
              : undefined
          }
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

        {/* Delete Forever — two-click confirm to prevent accidents */}
        <button
          onClick={handleBulkDeleteClick}
          disabled={selectedIds.length === 0 || loading || allSelectedActioned}
          title={
            allSelectedActioned
              ? "All selected senders have already been actioned"
              : deleteConfirm
                ? "Click again to permanently delete"
                : undefined
          }
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
          onClick={handleBulkBlock}
          disabled={selectedIds.length === 0 || loading}
          className="text-xs bg-orange-50 hover:bg-orange-100 text-orange-700 border border-orange-200 px-3 py-1.5 rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          style={{ cursor: "pointer" }}
        >
          🚫 Block Selected
        </button>

        <button
          onClick={handleBulkSkip}
          disabled={selectedIds.length === 0 || loading}
          className="text-xs bg-gray-50 hover:bg-gray-100 text-gray-500 border border-gray-200 px-3 py-1.5 rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          style={{ cursor: "pointer" }}
        >
          ⏭ Skip Selected
        </button>
      </div>

      {status && (
        <p className="w-full text-xs text-gray-600 bg-gray-50 rounded px-2 py-1">
          {status}
        </p>
      )}
    </div>
  );
}
