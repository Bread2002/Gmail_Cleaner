// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: Sender list component that renders a list of senders with bulk action capabilities,
//              including selection, move-to-trash, and delete-forever.

// Import necessary modules and components
import { useState, useCallback, useMemo } from "react";
import type { FlaggedSender } from "../../types";
import type { DeletionAction } from "../../hooks/useDeletion";
import { SenderCard } from "./SenderCard";
import type { BulkDeleteJob } from "./SenderCard";
import { BulkActionBar } from "./BulkActionBar";

// Define the props for the SenderList component
interface Props {
  senders: FlaggedSender[];
  dryRun: boolean;
}

// Internal shape for queued bulk jobs
interface QueuedBulkJob {
  sender_id: string;
  job_id: string;
  action: DeletionAction;
}

// Define the SenderList component that renders a list of senders with bulk action capabilities
export function SenderList({ senders, dryRun }: Props) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  // Tracks senders removed from the visible list (skipped, blocked, or bulk job done).
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());
  // Tracks senders whose emails have been actioned (real runs only).
  // Used to suppress bulk action buttons for already-actioned senders.
  const [actionedIds, setActionedIds] = useState<Set<string>>(new Set());

  // --- Bulk job queue ---------------------------------------------------
  // Jobs are processed one at a time. `bulkActiveIdx` points to the
  // currently active job; cards at higher indices show "Queued…".
  const [bulkQueue, setBulkQueue] = useState<QueuedBulkJob[]>([]);
  const [bulkActiveIdx, setBulkActiveIdx] = useState(-1);

  // Derived: which job is currently active, and which sender IDs are still waiting.
  const activeBulkJob = bulkQueue[bulkActiveIdx] ?? null;
  const queuedSenderIds = useMemo(
    () =>
      new Set(
        bulkQueue.slice(bulkActiveIdx + 1).map((j) => j.sender_id),
      ),
    [bulkQueue, bulkActiveIdx],
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
   * Called when a real bulk action request returns job IDs.
   * Populates the queue and starts the first job; subsequent jobs show "Queued…".
   */
  const handleBulkActionStarted = useCallback(
    (jobs: { sender_id: string; job_id: string }[], action: DeletionAction) => {
      if (jobs.length === 0) return;
      const queuedJobs: QueuedBulkJob[] = jobs.map((j) => ({ ...j, action }));
      setBulkQueue(queuedJobs);
      setBulkActiveIdx(0);
      setSelectedIds((prev) => {
        const next = new Set(prev);
        jobs.forEach((j) => next.delete(j.sender_id));
        return next;
      });
    },
    [],
  );

  /**
   * Called by a SenderCard when its bulk job finishes (done or error).
   * Advances the queue so the next card can begin its SSE stream.
   */
  const handleBulkJobDone = useCallback((_senderId: string) => {
    setBulkActiveIdx((prev) => prev + 1);
  }, []);

  // Deselect a sender that has been individually actioned.
  const handleActioned = useCallback((id: string) => {
    setSelectedIds((prev) => {
      if (!prev.has(id)) return prev;
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }, []);

  // Record that a sender's emails have been actioned (moved to trash or permanently deleted).
  const handleActionCompleted = useCallback((id: string) => {
    setActionedIds((prev) => new Set(prev).add(id));
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
        actionedIds={actionedIds}
        onSelectAll={selectAll}
        onDeselectAll={deselectAll}
        onBulkComplete={handleBulkComplete}
        onBulkActionStarted={handleBulkActionStarted}
      />

      {visibleSenders.map((sender) => {
        const isActive = activeBulkJob?.sender_id === sender.id;
        const activeBulkDeleteJob: BulkDeleteJob | null = isActive
          ? { jobId: activeBulkJob!.job_id, action: activeBulkJob!.action }
          : null;

        return (
          <SenderCard
            key={sender.id}
            sender={sender}
            dryRun={dryRun}
            selected={selectedIds.has(sender.id)}
            onToggleSelect={toggle}
            onDismiss={handleDismiss}
            onActioned={handleActioned}
            onActionCompleted={handleActionCompleted}
            bulkDeleteJob={activeBulkDeleteJob}
            isBulkQueued={queuedSenderIds.has(sender.id)}
            onBulkJobDone={handleBulkJobDone}
          />
        );
      })}
    </div>
  );
}
