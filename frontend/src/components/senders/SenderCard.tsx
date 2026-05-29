// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: Sender card component that displays sender information, preview, and action buttons
//              for managing individual senders (move to trash, delete forever, block, skip).

// Import necessary modules and components
import { useState, useEffect, useRef } from "react";
import type { FlaggedSender } from "../../types";
import { useDeletion } from "../../hooks/useDeletion";
import type { DeletionAction } from "../../hooks/useDeletion";
import { SenderPreview } from "./SenderPreview";
import { ActionButtons } from "./ActionButtons";
import { DeletionProgress } from "../deletion/DeletionProgress";

// Represents an active bulk job assigned to this card.
export interface BulkDeleteJob {
  jobId: string;
  action: DeletionAction;
}

// Define the props for the SenderCard component
interface Props {
  sender: FlaggedSender;
  dryRun: boolean;
  selected: boolean;
  onToggleSelect: (id: string) => void;
  /** Called when user skips, or on auto-dismiss after trash/block. */
  onDismiss: (id: string) => void;
  /** Called the first time this sender is trashed or blocked (deselects from bulk). */
  onActioned: (id: string) => void;
  /**
   * Called once when a real (non-dry-run) action job finishes successfully.
   * Used by SenderList to track which senders have been actioned so the bulk
   * buttons can be suppressed for already-actioned senders.
   */
  onActionCompleted?: (id: string) => void;
  /**
   * Set when this card is the *currently active* bulk job.
   * The card attaches to this job's SSE stream and shows live progress.
   */
  bulkDeleteJob?: BulkDeleteJob | null;
  /**
   * Set when this card is *waiting* in the bulk queue (not yet active).
   * Shows a "Queued…" indicator; no SSE is opened yet.
   */
  isBulkQueued?: boolean;
  /**
   * Called immediately when this card's bulk job completes (or errors),
   * so the next queued job can start.
   */
  onBulkJobDone?: (id: string) => void;
}

// Define the SenderCard component that renders sender information, preview, and action buttons
export function SenderCard({
  sender,
  dryRun,
  selected,
  onToggleSelect,
  onDismiss,
  onActioned,
  onActionCompleted,
  bulkDeleteJob,
  isBulkQueued,
  onBulkJobDone,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const deletion = useDeletion(sender.id);
  const actionedNotifiedRef = useRef(false);
  const completedNotifiedRef = useRef(false);
  const prevBulkJobIdRef = useRef<string | null>(null);

  const bulkDeleteJobRef = useRef<BulkDeleteJob | null | undefined>(null);
  bulkDeleteJobRef.current = bulkDeleteJob;

  const bulkDoneRef = useRef(false);

  const { startFromJobId } = deletion;

  const isActioned = deletion.phase === "done" || blocked;

  // Deselect from bulk once actioned individually.
  useEffect(() => {
    if (isActioned && !actionedNotifiedRef.current) {
      actionedNotifiedRef.current = true;
      onActioned(sender.id);
    }
  }, [isActioned, sender.id, onActioned]);

  // Notify parent that this sender's emails have been actioned (real run only).
  useEffect(() => {
    if (deletion.phase === "done" && !dryRun && !completedNotifiedRef.current) {
      completedNotifiedRef.current = true;
      onActionCompleted?.(sender.id);
    }
  }, [deletion.phase, dryRun, sender.id, onActionCompleted]);

  // When the active bulk job arrives, attach to its SSE stream.
  useEffect(() => {
    if (bulkDeleteJob && bulkDeleteJob.jobId !== prevBulkJobIdRef.current) {
      prevBulkJobIdRef.current = bulkDeleteJob.jobId;
      const endpoint =
        bulkDeleteJob.action === "moveToTrash" ? "move-to-trash" : "trash";
      startFromJobId(bulkDeleteJob.jobId, endpoint, bulkDeleteJob.action);
    }
  }, [bulkDeleteJob, startFromJobId]);

  // When the bulk SSE finishes, notify the queue so the next job can start.
  useEffect(() => {
    const terminal = deletion.phase === "done" || deletion.phase === "error";
    if (!terminal || !bulkDeleteJobRef.current || bulkDoneRef.current) return;
    bulkDoneRef.current = true;
    onBulkJobDone?.(sender.id);
  }, [deletion.phase, sender.id, onBulkJobDone]);

  // For individually actioned senders: auto-dismiss once actioned AND blocked.
  useEffect(() => {
    if (!bulkDeleteJob && deletion.phase === "done" && blocked) {
      const timer = setTimeout(() => onDismiss(sender.id), 1500);
      return () => clearTimeout(timer);
    }
  }, [bulkDeleteJob, deletion.phase, blocked, sender.id, onDismiss]);

  const avatarLetter = (sender.display_name ?? sender.email)
    .charAt(0)
    .toUpperCase();

  const isBulkLocked = !!(bulkDeleteJob || isBulkQueued);

  return (
    <div
      className={`bg-white rounded-xl border transition-all ${
        selected ? "border-blue-400 shadow-md" : "border-gray-200 shadow-sm"
      } ${deletion.phase === "done" ? "opacity-75" : ""} ${
        isBulkQueued ? "opacity-60" : ""
      }`}
    >
      <div className="p-4">
        {/* Top row: checkbox, avatar, sender info, badge */}
        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onToggleSelect(sender.id)}
            disabled={
              deletion.phase === "deleting" ||
              deletion.phase === "starting" ||
              isBulkLocked
            }
            className="mt-1 w-4 h-4 accent-blue-600 cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
          />

          {/* Avatar */}
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-semibold text-sm flex-shrink-0">
            {avatarLetter}
          </div>

          {/* Sender details */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                {sender.display_name && (
                  <p className="font-semibold text-gray-900 text-sm truncate">
                    {sender.display_name}
                  </p>
                )}
                <p
                  className={`text-sm truncate ${sender.display_name ? "text-gray-500" : "font-semibold text-gray-900"}`}
                >
                  {sender.email}
                </p>
              </div>

              {/* Badge: message count */}
              <div className="flex-shrink-0 text-right">
                <span className="bg-red-100 text-red-700 text-xs font-semibold px-2 py-0.5 rounded-full">
                  {sender.consecutive_unread_count}+ consecutive unread
                </span>
              </div>
            </div>

            {/* Preview toggle — hide when queued */}
            {!isBulkQueued && (
              <button
                onClick={() => setExpanded((e) => !e)}
                className="mt-1.5 text-xs text-blue-500 hover:text-blue-700 transition-colors"
              >
                {expanded ? "▲ Hide preview" : "▼ Show preview"}
              </button>
            )}
          </div>
        </div>

        {/* Expanded preview */}
        {expanded && !isBulkQueued && (
          <div className="mt-3 ml-12">
            <SenderPreview
              senderId={sender.id}
              initialSnippet={sender.snippet}
              initialSubject={sender.subject}
            />
          </div>
        )}

        {/* Action area */}
        <div className="mt-3 ml-12">
          {isBulkQueued ? (
            <p className="text-xs text-gray-400 italic">⏳ Queued…</p>
          ) : (
            <>
              {(deletion.phase === "starting" ||
                deletion.phase === "deleting" ||
                deletion.phase === "done" ||
                deletion.phase === "error") && (
                <DeletionProgress
                  phase={deletion.phase}
                  action={deletion.action}
                  progress={deletion.progress}
                  result={deletion.result}
                  dryRun={dryRun}
                />
              )}

              {!bulkDeleteJob &&
                (deletion.phase === "idle" || deletion.phase === "done") && (
                  <ActionButtons
                    senderId={sender.id}
                    phase={deletion.phase}
                    dryRun={dryRun}
                    blocked={blocked}
                    onMoveToTrash={() => deletion.moveToTrash(dryRun)}
                    onDeleteForever={() => deletion.deleteForever(dryRun)}
                    onSkip={() => onDismiss(sender.id)}
                    onBlockComplete={() => setBlocked(true)}
                  />
                )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
