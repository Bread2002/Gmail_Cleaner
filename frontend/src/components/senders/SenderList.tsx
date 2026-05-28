// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: Sender list component that renders a list of senders with bulk action capabilities, including selection, and bulk trashing.

// Import necessary modules and components
import { useState, useCallback, useMemo } from "react";
import type { FlaggedSender } from "../../types";
import { SenderCard } from "./SenderCard";
import { BulkActionBar } from "./BulkActionBar";

// Define the props for the SenderList component
interface Props {
  senders: FlaggedSender[];
  dryRun: boolean;
}

// Define the SenderList component that renders a list of senders
interface BulkTrashJob {
  sender_id: string;
  job_id: string;
}

// Define the SenderList component that renders a list of senders with bulk action capabilities, including selection, and bulk trashing
export function SenderList({ senders, dryRun }: Props) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  // Tracks senders removed from the visible list (skipped, blocked, or bulk-trash done).
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());
  // Tracks senders whose emails have been permanently deleted (real runs only).
  // Used to suppress the Bulk Trash button for already-trashed senders.
  const [trashedIds, setTrashedIds] = useState<Set<string>>(new Set());

  // --- Bulk-trash queue -------------------------------------------------
  // Jobs are processed one at a time. `bulkTrashActiveIdx` points to the
  // currently active job; cards at higher indices show "Queued…".
  const [bulkTrashQueue, setBulkTrashQueue] = useState<BulkTrashJob[]>([]);
  const [bulkTrashActiveIdx, setBulkTrashActiveIdx] = useState(-1);

  // Derived: which job is currently active, and which sender IDs are still waiting.
  const activeBulkJob = bulkTrashQueue[bulkTrashActiveIdx] ?? null;
  const queuedSenderIds = useMemo(
    () =>
      new Set(
        bulkTrashQueue.slice(bulkTrashActiveIdx + 1).map((j) => j.sender_id),
      ),
    [bulkTrashQueue, bulkTrashActiveIdx],
  );
  // ----------------------------------------------------------------------

  // Remove a sender from the visible list and deselect them.
  const handleDismiss = useCallback((id: string) => {
    setDismissedIds((prev) => new Set(prev).add(id));
    setSelectedIds((prev) => {
      if (!prev.has(id)) return prev;
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }, []);

  // Dismiss a batch of senders after a bulk skip/block action completes.
  const handleBulkComplete = useCallback((ids: string[]) => {
    if (ids.length === 0) return;
    setDismissedIds((prev) => {
      const next = new Set(prev);
      ids.forEach((id) => next.add(id));
      return next;
    });
    setSelectedIds((prev) => {
      const next = new Set(prev);
      ids.forEach((id) => next.delete(id));
      return next;
    });
  }, []);

  /**
   * Called when a real (non-dry-run) bulk-trash request returns job IDs.
   * Populates the queue and starts the first job; subsequent jobs become
   * "Queued…" until each preceding job finishes.
   */
  const handleBulkTrashStarted = useCallback((jobs: BulkTrashJob[]) => {
    if (jobs.length === 0) return;
    setBulkTrashQueue(jobs);
    setBulkTrashActiveIdx(0);
    // Deselect all senders that are now in the queue.
    setSelectedIds((prev) => {
      const next = new Set(prev);
      jobs.forEach((j) => next.delete(j.sender_id));
      return next;
    });
  }, []);

  /**
   * Called by a SenderCard when its bulk-trash job finishes (done or error).
   * Advances the queue so the next card can begin its SSE stream.
   */
  const handleBulkTrashJobDone = useCallback((_senderId: string) => {
    setBulkTrashActiveIdx((prev) => prev + 1);
  }, []);

  // Deselect a sender that has been individually actioned (trashed or blocked).
  const handleActioned = useCallback((id: string) => {
    setSelectedIds((prev) => {
      if (!prev.has(id)) return prev;
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }, []);

  // Record that a sender's emails have been permanently deleted.
  const handleTrashed = useCallback((id: string) => {
    setTrashedIds((prev) => new Set(prev).add(id));
  }, []);

  // Only show senders that haven't been dismissed yet.
  const visibleSenders = senders.filter((s) => !dismissedIds.has(s.id));

  const toggle = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () =>
    setSelectedIds(new Set(visibleSenders.map((s) => s.id)));
  const deselectAll = () => setSelectedIds(new Set());

  if (senders.length === 0) return null;

  return (
    <div className="space-y-3">
      <BulkActionBar
        selectedIds={Array.from(selectedIds)}
        totalCount={visibleSenders.length}
        dryRun={dryRun}
        trashedIds={trashedIds}
        onSelectAll={selectAll}
        onDeselectAll={deselectAll}
        onBulkComplete={handleBulkComplete}
        onBulkTrashStarted={handleBulkTrashStarted}
      />

      {visibleSenders.map((sender) => (
        <SenderCard
          key={sender.id}
          sender={sender}
          dryRun={dryRun}
          selected={selectedIds.has(sender.id)}
          onToggleSelect={toggle}
          onDismiss={handleDismiss}
          onActioned={handleActioned}
          onTrashed={handleTrashed}
          bulkTrashJobId={
            activeBulkJob?.sender_id === sender.id ? activeBulkJob.job_id : null
          }
          isBulkTrashQueued={queuedSenderIds.has(sender.id)}
          onBulkTrashJobDone={handleBulkTrashJobDone}
        />
      ))}
    </div>
  );
}
